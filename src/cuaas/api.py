"""POST /{cmd} for every allowed command."""

from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Body, Depends, Request

from cuaas.allowlist import ALLOWED
from cuaas.models import CommandRequest, CommandResponse
from cuaas.routing import StrictJSONRoute

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from cuaas.runner import Runner


def runner_dep(request: Request) -> Runner:
    """Return the runner create_app was given."""
    return request.app.state.runner


def _endpoint(cmd: str) -> Callable[..., Awaitable[CommandResponse]]:
    """Return the handler for one command."""

    async def run(
        runner: Annotated[Runner, Depends(runner_dep)],
        # no body at all is the same as {}, so `curl -X POST /true` works
        body: Annotated[CommandRequest | None, Body()] = None,
    ) -> CommandResponse:
        body = body or CommandRequest()
        result = await runner.run([cmd, *body.args], body.stdin_bytes)
        return CommandResponse.from_result(result)

    return run


# strict json: lone surrogates, inf/nan and non-json bodies are a 422 or 415
router = APIRouter(route_class=StrictJSONRoute)
# one route per command instead of /{cmd}: unknown commands get fastapi's 404
# and the docs list every command
for cmd in sorted(ALLOWED):
    router.add_api_route(f"/{cmd}", _endpoint(cmd), methods=["POST"], name=cmd)
