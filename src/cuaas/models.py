"""Models for cuaas."""

from typing import Self

from pydantic import BaseModel, ConfigDict


class CommandRequest(BaseModel):
    """Base class for command requests."""

    model_config = ConfigDict(extra="forbid")


class StdinRequest(CommandRequest):
    """Command request with stdin."""

    stdin: str = ""

    @property
    def stdin_bytes(self) -> bytes:
        """Return stdin encoded as UTF-8."""
        return self.stdin.encode()


class CommandResponse(BaseModel):
    """Base class for command responses."""

    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0

    @classmethod
    def from_bytes(cls, stdout: bytes, exit_code: int = 0) -> Self:
        """Build a response from stdout bytes, decoded as UTF-8."""
        return cls(stdout=stdout.decode(), exit_code=exit_code)
