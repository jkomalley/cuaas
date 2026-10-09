"""Models for cuaas."""

from pydantic import BaseModel, ConfigDict


class CommandRequest(BaseModel):
    """Base class for command requests."""

    model_config = ConfigDict(extra="forbid")


class StdinRequest(CommandRequest):
    """Command request with stdin."""

    stdin: str = ""


class CommandResponse(BaseModel):
    """Base class for command responses."""

    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
