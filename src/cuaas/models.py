"""Models for cuaas."""

import base64
import binascii
from typing import Literal

from pydantic import BaseModel, ConfigDict, ValidationInfo, field_validator
from pydantic_core import PydanticCustomError


def _b64decode(data: str) -> bytes:
    """Decode base64, allowing the line breaks `base64` wraps with."""
    # validate=True so junk is an error, not silently dropped
    return base64.b64decode(data.replace("\r", "").replace("\n", ""), validate=True)


class CommandRequest(BaseModel):
    """Base class for command requests."""

    # typo'd fields are a 422, not silently ignored
    model_config = ConfigDict(extra="forbid")


class StdinRequest(CommandRequest):
    """Command request with stdin."""

    # before stdin, so the validator can see it
    stdin_encoding: Literal["utf-8", "base64"] = "utf-8"
    stdin: str = ""

    @field_validator("stdin")
    @classmethod
    def _check_base64(cls, stdin: str, info: ValidationInfo) -> str:
        """Reject stdin that says it's base64 but isn't."""
        if info.data.get("stdin_encoding") == "base64":
            try:
                _b64decode(stdin)
            except (binascii.Error, ValueError) as e:
                # same type and message pydantic uses for its own base64
                error_type = "base64_decode"
                msg = "Base64 decoding error: '{error}'"
                raise PydanticCustomError(error_type, msg, {"error": str(e)}) from e
        return stdin

    @property
    def stdin_bytes(self) -> bytes:
        """Return stdin as bytes, decoding base64 if stdin_encoding says so."""
        # never raises, the validator already checked the base64 and routing
        # already rejects lone surrogates
        if self.stdin_encoding == "base64":
            return _b64decode(self.stdin)
        return self.stdin.encode()


class CommandResponse(BaseModel):
    """Base class for command responses."""

    stdout: str = ""
    stderr: str = ""
    # the command's exit code, not the HTTP status
    exit_code: int = 0

    @classmethod
    def from_bytes(cls, stdout: bytes, exit_code: int = 0) -> CommandResponse:
        """Build a response from stdout bytes, decoded as UTF-8."""
        # raises on invalid UTF-8, nothing produces it until #52
        return cls(stdout=stdout.decode(), exit_code=exit_code)
