"""Shared fixtures for cuaas tests."""

import pytest
from fastapi.testclient import TestClient

from cuaas.main import create_app
from cuaas.runner import FakeRunner


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
