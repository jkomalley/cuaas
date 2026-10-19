"""Shared fixtures for cuaas tests."""

import pytest
from fastapi.testclient import TestClient

from cuaas.main import create_app
from cuaas.runner import FakeRunner


@pytest.fixture
def fake():
    """The fake runner behind client, so a test can set its result or check calls."""
    return FakeRunner()


@pytest.fixture
def client(fake):
    """Test client for the api with the fake runner."""
    with TestClient(create_app(fake)) as c:
        # forget startup's check_gnu call, tests only check their own
        fake.calls.clear()
        yield c
