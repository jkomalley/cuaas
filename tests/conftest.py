"""Shared fixtures for cuaas tests."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from cuaas.main import create_app
from cuaas.runner import BWRAP, JAIL, FakeRunner


@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(items):
    """Stop once, not per test, when bwrap tests are selected but can't run."""
    # trylast, so -m has already deselected what isn't asked for
    wants_bwrap = any(item.get_closest_marker("bwrap") for item in items)
    if wants_bwrap and not (Path(BWRAP).exists() and Path(JAIL, "usr/bin").is_dir()):
        msg = f"bwrap tests need {BWRAP} and {JAIL}, run via `just test-bwrap`"
        raise pytest.UsageError(msg)


@pytest.fixture
def fake():
    """The FakeRunner behind `client`, for setting results and checking calls."""
    return FakeRunner()


@pytest.fixture
def client(fake):
    """Test client for the api with the fake runner."""
    with TestClient(create_app(fake)) as c:
        # drop the check_gnu call from startup
        fake.calls.clear()
        yield c
