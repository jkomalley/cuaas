"""Tests for the cuaas wc endpoint.

Expected output follows GNU coreutils wc reading from stdin.
"""

import base64

import pytest


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        # no flags: lines, words, bytes, each padded to width 7
        ({"stdin": "a b\nc\n"}, "      2       3       6\n"),
        ({"stdin": ""}, "      0       0       0\n"),
        ({}, "      0       0       0\n"),
        # one count: no padding
        ({"stdin": "a\nb\n", "lines": True}, "2\n"),
        ({"stdin": "", "lines": True}, "0\n"),
        ({"stdin": "hello world", "words": True}, "2\n"),
        # lines counts newlines, so a last line without one doesn't count
        ({"stdin": "a\nb", "lines": True}, "1\n"),
        # words are runs of non-whitespace
        ({"stdin": "  a\t\tb \n", "words": True}, "2\n"),
        # unicode whitespace splits words too, not just ascii
        ({"stdin": "a\u00a0b", "words": True}, "2\n"),
        ({"stdin": "a\u2028b", "words": True}, "2\n"),
        # chars vs bytes
        ({"stdin": "héllo", "chars": True}, "5\n"),
        ({"stdin": "héllo", "bytes": True}, "6\n"),
        # output order is always lines, words, chars, bytes
        ({"stdin": "héllo\n", "bytes": True, "lines": True}, "      1       7\n"),
        (
            {
                "stdin": "héllo wörld\n",
                "bytes": True,
                "chars": True,
                "words": True,
                "lines": True,
            },
            "      1       2      12      14\n",
        ),
    ],
)
def test_wc(client, body, expected):
    response = client.post("/wc", json=body)
    assert response.status_code == 200
    assert response.json() == {
        "stdout": expected,
        "stderr": "",
        "stdout_encoding": "utf-8",
        "exit_code": 0,
    }


@pytest.mark.parametrize(
    ("stdin", "flag", "expected"),
    [
        # gwc counts invalid UTF-8 as word chars
        (b"\xff", "words", "1\n"),
        (b"a \xff b", "words", "3\n"),
        (b"\xff\xfe \xc3", "words", "2\n"),
        # but not as chars
        (b"\xff", "chars", "0\n"),
        (b"\xff", "bytes", "1\n"),
    ],
)
def test_wc_binary(client, stdin, flag, expected):
    body = {
        "stdin": base64.b64encode(stdin).decode(),
        "stdin_encoding": "base64",
        flag: True,
    }
    response = client.post("/wc", json=body)
    assert response.status_code == 200
    assert response.json()["stdout"] == expected


def test_wc_invalid_base64(client):
    response = client.post("/wc", json={"stdin": "!!", "stdin_encoding": "base64"})
    assert response.status_code == 422
    error = response.json()["detail"][0]
    assert error["type"] == "base64_decode"
    assert error["loc"] == ["body", "stdin"]


@pytest.mark.parametrize(
    "body",
    [
        {"args": ["file.txt"]},
        {"lines": "banana"},
        {"stdin": 5},
        {"stdin_encoding": "latin-1"},
    ],
)
def test_wc_invalid(client, body):
    response = client.post("/wc", json=body)
    assert response.status_code == 422
