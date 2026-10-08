"""Main entrypoint for cuaas."""

from fastapi import FastAPI

from cuaas.commands import echo, wc

app = FastAPI()

app.include_router(echo.router)
app.include_router(wc.router)
