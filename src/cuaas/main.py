"""Main entrypoint for cuaas."""

from fastapi import FastAPI

from cuaas.models import CommandResponse, EchoRequest, WcRequest

app = FastAPI()


@app.post("/echo")
async def echo(request: EchoRequest) -> CommandResponse:
    """Return the arguments to stdout."""
    return CommandResponse(
        stdout=" ".join(request.args) + ("" if request.no_newline else "\n"),
    )


@app.post("/wc")
async def wc(request: WcRequest) -> CommandResponse:
    """Return line, word, char, and byte counts."""
    flag_set = any((request.lines, request.words, request.chars, request.bytes))

    counts: list[int] = []

    if request.lines or not flag_set:
        counts.append(request.stdin.count("\n"))

    if request.words or not flag_set:
        counts.append(len(request.stdin.split()))

    if request.chars:
        counts.append(len(request.stdin))

    if request.bytes or not flag_set:
        counts.append(len(request.stdin.encode()))

    if len(counts) == 1:
        stdout = str(counts[0])
    else:
        stdout = " ".join(f"{count:>7}" for count in counts)

    stdout += "\n"

    return CommandResponse(stdout=stdout)
