"""Shared by the bwrap tests. No fastapi or httpx, it also runs in the container."""

import asyncio

from cuaas.runner import BwrapRunner


def run(argv, stdin=b""):
    return asyncio.run(BwrapRunner().run(argv, stdin))
