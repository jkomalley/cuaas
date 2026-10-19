"""What goes in comes out unchanged, and the binaries are GNU. `just test-bwrap`."""

import asyncio
import base64
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from cuaas.allowlist import ALLOWED
from cuaas.main import create_app
from cuaas.runner import JAIL, BwrapRunner, SandboxError, check_gnu
from tests.helpers import run

pytestmark = pytest.mark.bwrap


def test_wc_with_stdin():
    result = run(["wc", "-l"], b"a b c\nd e\n")
    assert (result.stdout, result.stderr, result.exit_code) == (b"2\n", b"", 0)


def test_it_is_gnu():
    assert run(["wc", "--version"]).stdout.startswith(b"wc (GNU coreutils) 9.")
    assert asyncio.run(check_gnu(BwrapRunner())).startswith("wc (GNU coreutils)")


def test_exit_code_passes_through():
    assert run(["false"]).exit_code == 1


def test_stderr_passes_through():
    result = run(["wc", "--bogus"])
    assert result.exit_code == 1
    # wc, not /usr/bin/wc, like in a shell
    want = b"wc: unrecognized option '--bogus'\nTry 'wc --help'"
    assert result.stderr.startswith(want)


def test_no_shell_is_a_sandbox_error():
    with pytest.raises(SandboxError, match="execvp"):
        run(["sh", "-c", "id"])


def test_bytes_pass_through_unchanged():
    data = bytes(range(256)) * 4
    assert run(["cat"], data).stdout == data


def test_utf8_locale():
    # 2 in C.UTF-8, 3 if the locale silently fell back to C
    assert run(["wc", "-m"], "é\n".encode()).stdout == b"2\n"


def test_killed_shows_as_128_plus_signal():
    # timeout kills sleep with SIGKILL and exits 128 + 9 itself
    assert run(["timeout", "-s", "KILL", "0.1", "sleep", "5"]).exit_code == 137


def test_command_that_stops_reading_stdin_early():
    # head exits after one byte, writing the rest of stdin hits EPIPE
    assert run(["head", "-c1"], b"\0" * 10_000_000).stdout == b"\0"


def test_concurrent_runs():
    async def many():
        runner = BwrapRunner()
        inputs = [b"x" * n for n in range(20)]
        results = await asyncio.gather(*(runner.run(["wc", "-c"], i) for i in inputs))
        return [r.stdout for r in results]

    assert asyncio.run(many()) == [f"{n}\n".encode() for n in range(20)]


@pytest.mark.parametrize("cmd", sorted(ALLOWED))
def test_allowed_is_in_the_jail_and_gnu(cmd):
    assert (Path(JAIL) / "usr/bin" / cmd).is_file()
    # gnu test only answers --version as [
    if cmd != "test":
        assert b"(GNU coreutils)" in run([cmd, "--version"]).stdout


# the api end to end with bwrap


@pytest.fixture
def api():
    """TestClient with BwrapRunner, lifespan and check_gnu included."""
    with TestClient(create_app(BwrapRunner())) as c:
        yield c


def test_api_wc(api):
    r = api.post("/wc", json={"args": ["-l"], "stdin": "a b c\nd e\n"})
    assert r.status_code == 200
    assert r.json() == {
        "stdout": "2\n",
        "stdout_encoding": "utf-8",
        "stderr": "",
        "stderr_encoding": "utf-8",
        "exit_code": 0,
    }


def test_api_unicode_args(api):
    r = api.post("/echo", json={"args": ["héllo", "\U0001f600"]})
    assert r.json()["stdout"] == "héllo \U0001f600\n"


def test_api_binary_through_cat(api):
    data = bytes(range(256))
    r = api.post(
        "/cat",
        json={"stdin": base64.b64encode(data).decode(), "stdin_encoding": "base64"},
    )
    assert r.json()["stdout_encoding"] == "base64"
    assert base64.b64decode(r.json()["stdout"]) == data


def test_api_invalid_utf8_out_is_base64(api):
    r = api.post("/printf", json={"args": ["a\\xffb"]})
    assert r.json()["stdout_encoding"] == "base64"
    assert base64.b64decode(r.json()["stdout"]) == b"a\xffb"


def test_api_false_is_200_exit_1(api):
    r = api.post("/false")
    assert r.status_code == 200
    assert r.json()["exit_code"] == 1


def test_api_bad_flag(api):
    r = api.post("/wc", json={"args": ["--bogus"]})
    assert r.status_code == 200
    assert r.json()["exit_code"] == 1
    assert r.json()["stderr"].startswith("wc: unrecognized option '--bogus'")


def test_api_args_are_not_a_shell(api):
    r = api.post("/echo", json={"args": ["$(id)", ";", "|", "*"]})
    assert r.json()["stdout"] == "$(id) ; | *\n"
