"""echo command."""

from fastapi import APIRouter

from cuaas.models import CommandResponse, EchoRequest

router = APIRouter()


@router.post("/echo")
async def echo(request: EchoRequest) -> CommandResponse:
    """Return the arguments to stdout."""
    return CommandResponse(
        stdout=" ".join(request.args) + ("" if request.no_newline else "\n"),
    )
