"""Request and response, the same for every command."""

import base64
from typing import TYPE_CHECKING, Annotated, Literal

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    ValidationInfo,
    field_validator,
)
from pydantic_core import PydanticCustomError

if TYPE_CHECKING:
    from cuaas.runner import Result

type Encoding = Literal["utf-8", "base64"]


def _b64decode(data: str) -> bytes:
    """Decode base64, allowing the line breaks `base64` wraps with."""
    # validate=True so junk is an error, not silently dropped
    return base64.b64decode(data.replace("\r", "").replace("\n", ""), validate=True)


def _utf8(value: str) -> str:
    """Reject lone surrogates, they can't be encoded as utf-8 later."""
    # routing already rejects them in json, this covers anything built another way
    try:
        value.encode()
    except UnicodeEncodeError as e:
        error_type = "string_unicode"
        msg = "String should be valid unicode"
        raise PydanticCustomError(error_type, msg) from e
    return value


def _no_nul(arg: str) -> str:
    """Reject NUL bytes, exec can't pass them."""
    if "\0" in arg:
        error_type = "nul_byte"
        msg = "String should not contain NUL bytes"
        raise PydanticCustomError(error_type, msg)
    return arg


def _encode(data: bytes) -> tuple[str, Encoding]:
    """Return data as utf-8 text if it is, else base64."""
    try:
        return data.decode(), "utf-8"
    except UnicodeDecodeError:
        return base64.b64encode(data).decode(), "base64"


class CommandRequest(BaseModel):
    """Args and stdin for a command."""

    # typo'd fields are a 422, not silently ignored
    model_config = ConfigDict(extra="forbid")

    # everything after the command name, never parsed by a shell
    args: list[Annotated[str, AfterValidator(_utf8), AfterValidator(_no_nul)]] = []
    # declared before stdin, so stdin's validator can read it
    stdin_encoding: Encoding = "utf-8"
    stdin: Annotated[str, AfterValidator(_utf8)] = ""

    @field_validator("stdin")
    @classmethod
    def _check_base64(cls, stdin: str, info: ValidationInfo) -> str:
        """Reject stdin that says it's base64 but isn't."""
        if info.data.get("stdin_encoding") == "base64":
            try:
                _b64decode(stdin)
            except ValueError as e:
                # same type and message pydantic uses for its own base64
                error_type = "base64_decode"
                msg = "Base64 decoding error: '{error}'"
                raise PydanticCustomError(error_type, msg, {"error": str(e)}) from e
        return stdin

    @property
    def stdin_bytes(self) -> bytes:
        """Return stdin as bytes, decoding base64 if stdin_encoding says so."""
        # never raises, the validators already checked the base64 and the utf-8
        if self.stdin_encoding == "base64":
            return _b64decode(self.stdin)
        return self.stdin.encode()


class CommandResponse(BaseModel):
    """What the command did. Any exit code is still a 200."""

    stdout: str = ""
    # base64 when stdout isn't valid utf-8
    stdout_encoding: Encoding = "utf-8"
    stderr: str = ""
    stderr_encoding: Encoding = "utf-8"
    # the command's, 128 + signal if it was killed. not the http status
    exit_code: int = 0

    @classmethod
    def from_result(cls, result: Result) -> CommandResponse:
        """Build a response from a run, each stream as utf-8 or else base64."""
        stdout, stdout_encoding = _encode(result.stdout)
        stderr, stderr_encoding = _encode(result.stderr)
        return cls(
            stdout=stdout,
            stdout_encoding=stdout_encoding,
            stderr=stderr,
            stderr_encoding=stderr_encoding,
            exit_code=result.exit_code,
        )
