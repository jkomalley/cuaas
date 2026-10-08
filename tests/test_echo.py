"""Tests for the cuaas echo endpoint."""

import pytest


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ({}, "\n"),
        ({"args": ["hello"]}, "hello\n"),
        ({"args": ["hello", "world"]}, "hello world\n"),
        ({"args": ["a", "", "b"]}, "a  b\n"),
        ({"args": ["b", "a"]}, "b a\n"),
        ({"args": ["héllo", "日本"]}, "héllo 日本\n"),
        ({"args": ["a b"]}, "a b\n"),
        ({"args": ["hi"], "no_newline": True}, "hi"),
        ({"args": ["hi"], "no_newline": False}, "hi\n"),
    ],
)
def test_echo(client, body, expected):
    response = client.post("/echo", json=body)
    assert response.status_code == 200
    assert response.json() == {"stdout": expected, "stderr": "", "exit_code": 0}


def test_echo_content_type(client):
    response = client.post("/echo", json={"args": ["hi"]})
    assert response.headers["content-type"] == "application/json"


@pytest.mark.parametrize(
    "body",
    [
        {"no_newline": "banana"},
        {"args": "hi"},
        {"n": True},
    ],
)
def test_echo_invalid(client, body):
    response = client.post("/echo", json=body)
    assert response.status_code == 422


def test_echo_missing_body(client):
    response = client.post("/echo")
    assert response.status_code == 422
