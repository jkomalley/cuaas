"""Strict JSON parsing for command routes."""

import json
import math
from typing import TYPE_CHECKING, Any

from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from pydantic import TypeAdapter, ValidationError

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine

    from fastapi import Request, Response

# parses any JSON, only used to check the body
_json = TypeAdapter(Any)


def _is_json(content_type: str) -> bool:
    """Return whether a content-type header is JSON, like application/*+json."""
    mime = content_type.partition(";")[0].strip().lower()
    return mime == "application/json" or (
        mime.startswith("application/") and mime.endswith("+json")
    )


def _non_finite(value: object, loc: tuple = ()) -> tuple[tuple, float] | None:
    """Return the loc and value of the first inf/nan float, or None."""
    if isinstance(value, float):
        return None if math.isfinite(value) else (loc, value)
    if isinstance(value, dict):
        items = value.items()
    elif isinstance(value, list):
        items = enumerate(value)
    else:
        return None
    for key, item in items:
        if (found := _non_finite(item, (*loc, key))) is not None:
            return found
    return None


# every command router must use this
class StrictJSONRoute(APIRoute):
    r"""Route that rejects bodies pydantic's JSON parser won't accept.

    Fastapi parses with the stdlib, which accepts lone surrogates like
    "\ud800" that can't be encoded as UTF-8 later. Pydantic rejects them.
    Both accept NaN, Infinity and 1e999 as floats, which break the 422.
    Non-JSON bodies get a 415 instead of fastapi's 422.
    """

    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        """Wrap the default handler with a strict JSON check."""
        handler = super().get_route_handler()

        async def strict_handler(request: Request) -> Response:
            # starlette caches the body, so the handler can read it again
            body = await request.body()
            if body:
                # fastapi's own 422 for non-JSON bodies echoes the raw bytes,
                # which crashes on invalid UTF-8
                if not _is_json(request.headers.get("content-type", "")):
                    raise HTTPException(
                        status_code=415,
                        detail="Content-type must be application/json",
                    )
                try:
                    value = _json.validate_json(body)
                except ValidationError as e:
                    errors = e.errors(include_url=False, include_input=False)
                    raise RequestValidationError(
                        [{**error, "loc": ("body", *error["loc"])} for error in errors],
                        body=body,
                    ) from e
                # the 422 echoes the input, and json can't send inf/nan back
                if (found := _non_finite(value)) is not None:
                    loc, bad = found
                    raise RequestValidationError(
                        [
                            {
                                "type": "finite_number",
                                "loc": ("body", *loc),
                                "msg": "Input should be a finite number",
                                # as a string, like "NaN" or "Infinity"
                                "input": json.dumps(bad),
                            },
                        ],
                        body=body,
                    )
            return await handler(request)

        return strict_handler
