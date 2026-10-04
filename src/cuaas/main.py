"""Main entrypoint for cuaas."""

from typing import Annotated

from fastapi import FastAPI, Query
from fastapi.responses import PlainTextResponse

app = FastAPI()


@app.post("/echo", response_class=PlainTextResponse)
async def echo(
    args: Annotated[list[str], Query(default_factory=list)], no_newline: bool = False
) -> str:
    return " ".join(args) + ("" if no_newline else "\n")
