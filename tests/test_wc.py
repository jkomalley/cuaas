"""Tests for the cuaas wc endpoint."""

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
    assert response.json() == {"stdout": expected, "stderr": "", "exit_code": 0}


@pytest.mark.parametrize(
    "body",
    [
        {"args": ["file.txt"]},
        {"lines": "banana"},
        {"stdin": 5},
    ],
)
def test_wc_invalid(client, body):
    response = client.post("/wc", json=body)
    assert response.status_code == 422
