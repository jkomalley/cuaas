"""Strict JSON parsing for command routes."""

import math
from typing import TYPE_CHECKING, Any

from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from pydantic import TypeAdapter, ValidationError

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine

    from fastapi import Request, Response

# parses any JSON, only used to check the body
_json = TypeAdapter(Any)


def _finite(value: object) -> bool:
    """Return whether every float in a parsed JSON value is finite."""
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, dict):
        return all(_finite(v) for v in value.values())
    if isinstance(value, list):
        return all(_finite(v) for v in value)
    return True


# every command router must use this
class StrictJSONRoute(APIRoute):
    r"""Route that rejects bodies pydantic's JSON parser won't accept.

    Fastapi parses with the stdlib, which accepts lone surrogates like
    "\ud800" that can't be encoded as UTF-8 later. Pydantic rejects them.
    Both accept NaN, Infinity and 1e999 as floats, which break the 422.
    """

    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        """Wrap the default handler with a strict JSON check."""
        handler = super().get_route_handler()

        async def strict_handler(request: Request) -> Response:
            # starlette caches the body, so the handler can read it again
            body = await request.body()
            if body:
                try:
                    value = _json.validate_json(body)
                except ValidationError as e:
                    errors = e.errors(include_url=False, include_input=False)
                    raise RequestValidationError(
                        [{**error, "loc": ("body", *error["loc"])} for error in errors],
                    ) from e
                # the 422 echoes the input, and json can't send inf/nan back
                if not _finite(value):
                    raise RequestValidationError(
                        [
                            {
                                "type": "finite_number",
                                "loc": ("body",),
                                "msg": "Input should be a finite number",
                            },
                        ],
                    )
            return await handler(request)

        return strict_handler
