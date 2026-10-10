"""echo command."""

from fastapi import APIRouter
from pydantic import Field

from cuaas.models import CommandRequest, CommandResponse
from cuaas.routing import StrictJSONRoute


class EchoRequest(CommandRequest):
    """Arguments and flags for echo."""

    args: list[str] = Field(default_factory=list)
    no_newline: bool = False  # -n


router = APIRouter(route_class=StrictJSONRoute)


@router.post("/echo")
async def echo(request: EchoRequest) -> CommandResponse:
    """Return the arguments to stdout."""
    return CommandResponse(
        stdout=" ".join(request.args) + ("" if request.no_newline else "\n"),
    )
