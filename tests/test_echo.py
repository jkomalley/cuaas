"""Tests for the echo endpoint."""

import pytest
from fastapi.testclient import TestClient

from cuaas.main import app

client = TestClient(app)


def test_echo_no_args():
    response = client.post("/echo")
    assert response.status_code == 200
    assert response.text == "\n"


@pytest.mark.parametrize(
    ("params", "expected"),
    [
        ({"args": ["hello"]}, "hello\n"),
        ({"args": ["hello", "world"]}, "hello world\n"),
        ({"args": ["a", "", "b"]}, "a  b\n"),
        ({"args": ["hi"], "no_newline": True}, "hi"),
        ({"args": ["hi"], "no_newline": False}, "hi\n"),
    ],
)
def test_echo(params, expected):
    response = client.post("/echo", params=params)
    assert response.status_code == 200
    assert response.text == expected


def test_echo_content_type():
    response = client.post("/echo", params={"args": ["hi"]})
    assert response.headers["content-type"].startswith("text/plain")


def test_echo_invalid():
    response = client.post("/echo", params={"no_newline": "banana"})
    assert response.status_code == 422
