import pytest
from pydantic import ValidationError

from cuaas.models import CommandRequest, CommandResponse
from cuaas.runner import Result


def test_request_defaults():
    request = CommandRequest()
    assert request.args == []
    assert request.stdin_bytes == b""


def test_request_rejects_unknown_fields():
    with pytest.raises(ValidationError) as e:
        CommandRequest.model_validate({"argz": ["-l"]})
    assert e.value.errors()[0]["type"] == "extra_forbidden"


def test_args_with_nul_point_at_the_arg():
    with pytest.raises(ValidationError) as e:
        CommandRequest(args=["-l", "a\0b"])
    error = e.value.errors()[0]
    assert error["type"] == "nul_byte"
    assert error["loc"] == ("args", 1)


def test_args_must_be_strings():
    with pytest.raises(ValidationError):
        CommandRequest.model_validate({"args": [1]})


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
    assert CommandRequest(stdin=stdin).stdin_bytes == expected


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
    request = CommandRequest(stdin=stdin, stdin_encoding="base64")
    assert request.stdin_bytes == expected


# missing padding, junk
@pytest.mark.parametrize("stdin", ["aG k=", "aGk", "!!", "é"])
def test_stdin_invalid_base64(stdin):
    with pytest.raises(ValidationError) as e:
        CommandRequest(stdin=stdin, stdin_encoding="base64")
    error = e.value.errors()[0]
    assert error["type"] == "base64_decode"
    assert error["loc"] == ("stdin",)


def test_stdin_encoding_is_utf8_or_base64():
    with pytest.raises(ValidationError):
        CommandRequest.model_validate({"stdin_encoding": "latin-1"})


def test_response_utf8():
    response = CommandResponse.from_result(Result(b"h\xc3\xa9\n", b"oops\n", 1))
    assert response == CommandResponse(stdout="hé\n", stderr="oops\n", exit_code=1)


def test_response_base64_per_stream():
    response = CommandResponse.from_result(Result(b"\xff\xfe", b"ok", 0))
    assert response == CommandResponse(
        stdout="//4=", stdout_encoding="base64", stderr="ok"
    )
    response = CommandResponse.from_result(Result(b"ok", b"\xff", 0))
    assert response == CommandResponse(
        stdout="ok", stderr="/w==", stderr_encoding="base64"
    )
