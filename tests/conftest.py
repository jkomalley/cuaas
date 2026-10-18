"""Shared fixtures for cuaas tests."""

import pytest
from fastapi.testclient import TestClient

from cuaas.api import runner_dep
from cuaas.main import app
from cuaas.runner import FakeRunner


@pytest.fixture(scope="session")
def client():
    """Test client fixture for the cuaas app, with the fake runner."""
    # the lifespan reads CUAAS_RUNNER when the client starts
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("CUAAS_RUNNER", "fake")
        with TestClient(app) as c:
            yield c


@pytest.fixture
def fake():
    """A fresh fake runner for one test, so its calls can be checked."""
    runner = FakeRunner()
    app.dependency_overrides[runner_dep] = lambda: runner
    yield runner
    app.dependency_overrides.clear()
