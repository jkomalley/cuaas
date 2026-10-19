"""Main entrypoint for cuaas."""

import logging
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from cuaas.api import router
from cuaas.runner import BwrapRunner, SandboxError, check_gnu

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from cuaas.runner import Runner

# uvicorn's logger, so this shows up next to its startup lines
logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Refuse to start unless the runner runs GNU coreutils."""
    logger.info("coreutils: %s", await check_gnu(app.state.runner))
    yield


async def sandbox_error(request: Request, exc: Exception) -> JSONResponse:
    """Our fault, so a 500. bwrap's error goes in the log, not to the client."""
    logger.error("sandbox error on %s: %s", request.url.path, exc)
    return JSONResponse({"detail": "Sandbox error"}, status_code=500)


def create_app(runner: Runner | None = None) -> FastAPI:
    """Return the api, running commands with runner, bwrap by default."""
    app = FastAPI(lifespan=lifespan)
    app.state.runner = runner or BwrapRunner()
    app.include_router(router)
    app.add_exception_handler(SandboxError, sandbox_error)
    return app


app = create_app()
