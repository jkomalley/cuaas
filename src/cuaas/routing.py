"""Strict JSON parsing for command routes."""

from typing import TYPE_CHECKING, Any

from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from pydantic import TypeAdapter, ValidationError

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine

    from fastapi import Request, Response

# parses any JSON, only used to check the body
_json = TypeAdapter(Any)


# every command router must use this
class StrictJSONRoute(APIRoute):
    r"""Route that rejects bodies pydantic's JSON parser won't accept.

    Fastapi parses with the stdlib, which accepts lone surrogates like
    "\ud800" that can't be encoded as UTF-8 later. Pydantic rejects them.
    """

    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        """Wrap the default handler with a strict JSON check."""
        handler = super().get_route_handler()

        async def strict_handler(request: Request) -> Response:
            # starlette caches the body, so the handler can read it again
            body = await request.body()
            if body:
                try:
                    _json.validate_json(body)
                except ValidationError as e:
                    errors = e.errors(include_url=False, include_input=False)
                    raise RequestValidationError(
                        [{**error, "loc": ("body", *error["loc"])} for error in errors],
                    ) from e
            return await handler(request)

        return strict_handler
