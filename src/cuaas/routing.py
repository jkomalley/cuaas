"""Strict JSON parsing for command routes."""

import json
from typing import TYPE_CHECKING, Any

import pydantic_core
from fastapi import Request, Response
from fastapi.routing import APIRoute

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine


class StrictJSONRequest(Request):
    r"""Request that parses JSON with pydantic instead of the stdlib.

    The stdlib accepts lone surrogates like "\ud800", which can't be encoded
    as UTF-8 later. Pydantic rejects them as invalid JSON.
    """

    async def json(self) -> object:
        """Parse the body, raising JSONDecodeError so fastapi returns a 422."""
        # cache it like starlette does
        if not hasattr(self, "_json"):
            body = await self.body()
            try:
                self._json = pydantic_core.from_json(body)
            except ValueError as e:
                # fastapi only 422s on JSONDecodeError. pydantic has no
                # position, so it's 0
                doc = body.decode(errors="replace")
                raise json.JSONDecodeError(str(e), doc, 0) from e
        return self._json


# every command router must use this
class StrictJSONRoute(APIRoute):
    """Route that hands its endpoint a StrictJSONRequest."""

    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        """Wrap the default handler to swap in StrictJSONRequest."""
        handler = super().get_route_handler()

        async def strict_handler(request: Request) -> Response:
            return await handler(StrictJSONRequest(request.scope, request.receive))

        return strict_handler
