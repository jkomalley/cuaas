"""wc command."""

from fastapi import APIRouter

from cuaas.models import CommandResponse, StdinRequest
from cuaas.routing import StrictJSONRoute


class WcRequest(StdinRequest):
    """Arguments and flags for wc."""

    lines: bool = False
    words: bool = False
    chars: bool = False
    bytes: bool = False


router = APIRouter(route_class=StrictJSONRoute)


@router.post("/wc")
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
