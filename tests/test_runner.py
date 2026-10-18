"""Fast tests for the runner, no sandbox needed."""

import asyncio

import pytest

from cuaas.runner import (
    BwrapRunner,
    FakeRunner,
    Result,
    bwrap_argv,
    check_argv,
    check_gnu,
    get_runner,
    parse_status,
)


def test_bwrap_argv_runs_the_jails_binary_after_dashdash():
    argv = bwrap_argv(["wc", "-l"], 5)
    assert argv[0] == "/usr/bin/bwrap"
    assert argv[-3:] == ["--", "/usr/bin/wc", "-l"]


def test_bwrap_argv_sandbox_flags():
    argv = bwrap_argv(["wc"], 5)
    joined = " ".join(argv)
    assert "--ro-bind /jail /" in joined
    assert "--json-status-fd 5" in joined
    assert "--setenv LC_ALL C.UTF-8" in joined
    assert "--argv0 wc --" in joined
    assert "--chdir /" in joined
    for flag in ["--unshare-all", "--die-with-parent", "--new-session", "--clearenv"]:
        assert flag in argv


def test_bwrap_argv_passes_user_args_untouched():
    args = ["--foo", "-l", "; rm -rf /", "$(id)", "--", "--ro-bind"]
    argv = bwrap_argv(["wc", *args], 5)
    # everything after the -- is the command's, nothing gets parsed as bwrap options
    assert argv[argv.index("--") + 2 :] == args


@pytest.mark.parametrize("cmd", ["", "/bin/sh", "../wc", "usr/bin/wc", ".", ".."])
def test_bwrap_argv_rejects_non_names(cmd):
    with pytest.raises(ValueError, match="not a command name"):
        bwrap_argv([cmd], 5)


def test_bwrap_argv_rejects_empty_argv():
    with pytest.raises(ValueError, match="not a command name"):
        bwrap_argv([], 5)


@pytest.mark.parametrize("argv", [["wc", "a\0b"], ["wc\0"], ["wc", "-l", "\0"]])
def test_check_argv_rejects_nul(argv):
    with pytest.raises(ValueError, match="NUL byte"):
        check_argv(argv)


def test_check_argv_allows_empty_args():
    check_argv(["wc", "-l", ""])


def test_bwrap_argv_rejects_nul():
    with pytest.raises(ValueError, match="NUL byte"):
        bwrap_argv(["wc", "a\0b"], 5)


CHILD = '{ "child-pid": 7, "mnt-namespace": 4026532458 }\n'


@pytest.mark.parametrize("code", [0, 1, 137])
def test_parse_status_exit_code(code):
    assert parse_status(f'{CHILD}{{ "exit-code": {code} }}\n') == code


def test_parse_status_never_ran():
    # what bwrap writes when execvp fails
    assert parse_status(CHILD) is None


def test_parse_status_empty():
    assert parse_status("") is None


def test_parse_status_takes_the_last_exit_code():
    assert parse_status(f'{CHILD}{{ "exit-code": 0 }}\n{{ "exit-code": 3 }}\n') == 3


def test_parse_status_torn_line():
    # bwrap killed halfway through writing
    assert parse_status('{ "child-pid": 7, "cgr') is None


def test_parse_status_not_an_object():
    assert parse_status("5\n") is None


def test_parse_status_skips_junk():
    assert parse_status(f'junk\n{CHILD}{{ "exit-code": 2 }}\n[1]\nmore junk') == 2


def test_fake_echoes_stdin_and_records_calls():
    fake = FakeRunner()
    result = asyncio.run(fake.run(["cat"], b"hi\n"))
    assert result == Result(b"hi\n", b"", 0)
    assert fake.calls == [(["cat"], b"hi\n")]


@pytest.mark.parametrize("argv", [["sh/x"], [], ["wc", "a\0b"]])
def test_fake_rejects_like_bwrap_and_records_nothing(argv):
    fake = FakeRunner()
    with pytest.raises(ValueError, match=r"not a command name|NUL byte"):
        asyncio.run(fake.run(argv))
    assert fake.calls == []


def test_fake_returns_the_set_result():
    fake = FakeRunner(Result(b"", b"nope\n", 2))
    assert asyncio.run(fake.run(["wc", "--version"])).exit_code == 2


def test_check_gnu_passes_on_the_fake():
    assert asyncio.run(check_gnu(FakeRunner())) == "wc (GNU coreutils) fake"


def test_check_gnu_refuses_uutils():
    # what 26.04's own /usr/bin/wc says
    fake = FakeRunner(Result(b"wc (uutils coreutils) 0.10.0\n", b"", 0))
    with pytest.raises(RuntimeError, match="uutils"):
        asyncio.run(check_gnu(fake))


def test_check_gnu_refuses_a_failed_run():
    fake = FakeRunner(Result(b"", b"wc: broken\n", 1))
    with pytest.raises(RuntimeError, match="wc: broken"):
        asyncio.run(check_gnu(fake))


def test_get_runner_defaults_to_bwrap(monkeypatch):
    monkeypatch.delenv("CUAAS_RUNNER", raising=False)
    assert isinstance(get_runner(), BwrapRunner)


def test_get_runner_fake(monkeypatch):
    monkeypatch.setenv("CUAAS_RUNNER", "fake")
    assert isinstance(get_runner(), FakeRunner)


def test_get_runner_rejects_junk(monkeypatch):
    monkeypatch.setenv("CUAAS_RUNNER", "docker")
    with pytest.raises(ValueError, match="docker"):
        get_runner()
