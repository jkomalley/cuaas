"""Models for cuaas."""

from pydantic import BaseModel, ConfigDict


class CommandRequest(BaseModel):
    """Base class for command requests."""

    # typo'd fields are a 422, not silently ignored
    model_config = ConfigDict(extra="forbid")


class StdinRequest(CommandRequest):
    """Command request with stdin."""

    # text for now, base64 comes with #51
    stdin: str = ""

    @property
    def stdin_bytes(self) -> bytes:
        """Return stdin encoded as UTF-8."""
        # never raises, routing already rejects lone surrogates
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
