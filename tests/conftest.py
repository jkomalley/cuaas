"""Shared fixtures for cuaas tests."""

import pytest
from fastapi.testclient import TestClient

from cuaas.main import app


@pytest.fixture
def client():
    """Test client fixture for the cuaas app."""
    with TestClient(app) as c:
        yield c
