"""Main entrypoint for cuaas."""

import logging
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from cuaas.api import router
from cuaas.runner import SandboxError, check_gnu, get_runner

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

# uvicorn's logger, so this shows up next to its startup lines
logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Pick the runner and refuse to start unless it runs GNU coreutils."""
    runner = get_runner()
    logger.info("coreutils: %s", await check_gnu(runner))
    app.state.runner = runner
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(router)


@app.exception_handler(SandboxError)
async def sandbox_error(request: Request, exc: SandboxError) -> JSONResponse:
    """Our fault, so a 500. bwrap's error goes in the log, not to the client."""
    logger.error("sandbox error on %s: %s", request.url.path, exc)
    return JSONResponse({"detail": "Sandbox error"}, status_code=500)
