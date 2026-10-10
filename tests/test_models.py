"""Tests for the shared request and response models."""

import pytest
from pydantic import ValidationError

from cuaas.models import CommandResponse, StdinRequest


@pytest.mark.parametrize(
    ("stdin", "expected"),
    [
        ("hello\n", b"hello\n"),
        ("héllo", b"h\xc3\xa9llo"),
        ("\U0001f600", b"\xf0\x9f\x98\x80"),
        # not base64, but it's utf-8 so it doesn't matter
        ("!!", b"!!"),
    ],
)
def test_stdin_bytes(stdin, expected):
    assert StdinRequest(stdin=stdin).stdin_bytes == expected


def test_stdin_bytes_default():
    assert StdinRequest().stdin_bytes == b""


@pytest.mark.parametrize(
    ("stdin", "expected"),
    [
        ("aGk=", b"hi"),
        ("/+8=", b"\xff\xef"),
        ("", b""),
        # what `base64 file` gives you, wrapped and with a trailing newline
        ("aGk=\n", b"hi"),
        ("aGVs\nbG8=\n", b"hello"),
        ("aGVs\r\nbG8=\r\n", b"hello"),
    ],
)
def test_stdin_bytes_base64(stdin, expected):
    request = StdinRequest(stdin=stdin, stdin_encoding="base64")
    assert request.stdin_bytes == expected


@pytest.mark.parametrize(
    "stdin",
    [
        "aG k=",
        # missing padding
        "aGk",
        "!!",
        "é",
    ],
)
def test_stdin_invalid_base64(stdin):
    with pytest.raises(ValidationError) as e:
        StdinRequest(stdin=stdin, stdin_encoding="base64")
    error = e.value.errors()[0]
    assert error["type"] == "base64_decode"
    assert error["loc"] == ("stdin",)


@pytest.mark.parametrize(
    ("stdout", "expected"),
    [
        (b"hello\n", "hello\n"),
        (b"h\xc3\xa9llo", "héllo"),
    ],
)
def test_from_bytes(stdout, expected):
    response = CommandResponse.from_bytes(stdout)
    assert response == CommandResponse(stdout=expected, stdout_encoding="utf-8")


def test_from_bytes_invalid_utf8():
    response = CommandResponse.from_bytes(b"\xff\xfe")
    assert response == CommandResponse(stdout="//4=", stdout_encoding="base64")


def test_from_bytes_exit_code():
    response = CommandResponse.from_bytes(b"", exit_code=1)
    assert response == CommandResponse(exit_code=1)
