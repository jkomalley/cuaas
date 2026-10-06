"""Main entrypoint for cuaas."""

from fastapi import FastAPI

from cuaas.models import CommandResponse, EchoRequest

app = FastAPI()


@app.post("/echo")
async def echo(request: EchoRequest) -> CommandResponse:
    """Print the arguments, separated by spaces."""
    return CommandResponse(
        stdout=" ".join(request.args) + ("" if request.no_newline else "\n"),
    )
