"""Strict JSON parsing for command routes."""

import email.message
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

# validator for any json value, just to check the body parses
_json = TypeAdapter(Any)


def _is_json(content_type: str) -> bool:
    """Return whether a content-type header is JSON, like application/*+json."""
    # same parsing as fastapi, except a missing header isn't json (415)
    message = email.message.Message()
    message["content-type"] = content_type
    subtype = message.get_content_subtype()
    return message.get_content_maintype() == "application" and (
        subtype == "json" or subtype.endswith("+json")
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
            # starlette caches this, the wrapped handler reads it again
            body = await request.body()
            if body:
                # fastapi's 422 for non-json echoes the raw body and crashes on
                # invalid utf-8
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
                # the 422 echoes input back, and inf/nan aren't valid json
                if (found := _non_finite(value)) is not None:
                    loc, bad = found
                    raise RequestValidationError(
                        [
                            {
                                "type": "finite_number",
                                "loc": ("body", *loc),
                                "msg": "Input should be a finite number",
                                # e.g. "NaN", "Infinity"
                                "input": json.dumps(bad),
                            },
                        ],
                        body=body,
                    )
            return await handler(request)

        return strict_handler
