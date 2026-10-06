"""Models for cuaas."""

from pydantic import BaseModel, ConfigDict, Field


class CommandRequest(BaseModel):
    """Base class for command requests."""

    model_config = ConfigDict(extra="forbid")


class CommandResponse(BaseModel):
    """Base class for command responses."""

    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0


class EchoRequest(CommandRequest):
    """Arguments and flags for echo."""

    args: list[str] = Field(default_factory=list)
    no_newline: bool = False


class WcRequest(CommandRequest):
    """Arguments and flags for wc."""

    stdin: str = ""
    lines: bool = False
    words: bool = False
    chars: bool = False
    bytes: bool = False
