"""wc command."""

from fastapi import APIRouter

from cuaas.models import CommandResponse, StdinRequest
from cuaas.routing import StrictJSONRoute


class WcRequest(StdinRequest):
    """Arguments and flags for wc."""

    lines: bool = False  # -l
    words: bool = False  # -w
    chars: bool = False  # -m
    bytes: bool = False  # -c


router = APIRouter(route_class=StrictJSONRoute)


@router.post("/wc")
async def wc(request: WcRequest) -> CommandResponse:
    """Return line, word, char, and byte counts."""
    # no flags means the GNU default: lines, words, bytes
    flag_set = any((request.lines, request.words, request.chars, request.bytes))

    data = request.stdin_bytes
    # like gwc -m, invalid UTF-8 isn't counted as chars
    text = data.decode(errors="ignore")
    # but gwc -w counts it as part of a word, and U+FFFD isn't whitespace
    words = data.decode(errors="replace").split()

    # always lines, words, chars, bytes, whatever the flag order
    counts: list[int] = []

    if request.lines or not flag_set:
        counts.append(data.count(b"\n"))

    if request.words or not flag_set:
        # close to GNU but not exact, see #61
        counts.append(len(words))

    if request.chars:
        counts.append(len(text))

    if request.bytes or not flag_set:
        counts.append(len(data))

    # like gwc on stdin: one count un-padded, more padded to 7
    if len(counts) == 1:
        stdout = str(counts[0])
    else:
        stdout = " ".join(f"{count:>7}" for count in counts)

    stdout += "\n"

    return CommandResponse(stdout=stdout)
