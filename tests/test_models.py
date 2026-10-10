"""Tests for the shared request and response models."""

import pytest

from cuaas.models import CommandResponse, StdinRequest


@pytest.mark.parametrize(
    ("stdin", "expected"),
    [
        ("", b""),
        ("hello\n", b"hello\n"),
        ("héllo", b"h\xc3\xa9llo"),
        ("😀", b"\xf0\x9f\x98\x80"),
    ],
)
def test_stdin_bytes(stdin, expected):
    assert StdinRequest(stdin=stdin).stdin_bytes == expected


def test_stdin_bytes_default():
    assert StdinRequest().stdin_bytes == b""


@pytest.mark.parametrize(
    ("stdout", "expected"),
    [
        (b"", ""),
        (b"hello\n", "hello\n"),
        (b"h\xc3\xa9llo", "héllo"),
    ],
)
def test_from_bytes(stdout, expected):
    response = CommandResponse.from_bytes(stdout)
    assert response == CommandResponse(stdout=expected)


def test_from_bytes_exit_code():
    response = CommandResponse.from_bytes(b"", exit_code=1)
    assert response == CommandResponse(exit_code=1)
