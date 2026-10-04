"""Tests for the echo endpoint."""

import pytest
from fastapi.testclient import TestClient

from cuaas.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_echo_no_args(client):
    response = client.post("/echo")
    assert response.status_code == 200
    assert response.text == "\n"


@pytest.mark.parametrize(
    ("params", "expected"),
    [
        ({"args": ["hello"]}, "hello\n"),
        ({"args": ["hello", "world"]}, "hello world\n"),
        ({"args": ["a", "", "b"]}, "a  b\n"),
        ({"args": ["a,b"]}, "a,b\n"),
        ({"args": ["b", "a"]}, "b a\n"),
        ({"args": ["héllo", "日本"]}, "héllo 日本\n"),
        ({"args": ["a b"]}, "a b\n"),
        ({"args": ["hi"], "no_newline": True}, "hi"),
        ({"args": ["hi"], "no_newline": False}, "hi\n"),
    ],
)
def test_echo(client, params, expected):
    response = client.post("/echo", params=params)
    assert response.status_code == 200
    assert response.text == expected


def test_echo_content_type(client):
    response = client.post("/echo", params={"args": ["hi"]})
    assert response.headers["content-type"].startswith("text/plain")


def test_echo_invalid(client):
    response = client.post("/echo", params={"no_newline": "banana"})
    assert response.status_code == 422
