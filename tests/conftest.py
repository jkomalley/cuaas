"""Shared fixtures for cuaas tests."""

import pytest
from fastapi.testclient import TestClient

from cuaas.main import app


@pytest.fixture(scope="session")
def client():
    """Test client fixture for the cuaas app, with the fake runner."""
    # the lifespan reads CUAAS_RUNNER when the client starts
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("CUAAS_RUNNER", "fake")
        with TestClient(app) as c:
            yield c
