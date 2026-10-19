"""A command in bwrap can't get out. `just test-bwrap`, and in the container."""

import sys
from pathlib import Path

import pytest

from cuaas import runner
from tests.helpers import run

pytestmark = pytest.mark.bwrap


def test_env_is_only_ours():
    assert sorted(run(["env"]).stdout.splitlines()) == [b"LC_ALL=C.UTF-8", b"PWD=/"]


def test_cwd_is_root(monkeypatch):
    # /usr/bin is in the jail too, so without --chdir bwrap would stay there
    monkeypatch.chdir("/usr/bin")
    assert run(["pwd"]).stdout == b"/\n"


def test_root_is_read_only():
    result = run(["touch", "/x"])
    assert result.exit_code == 1
    assert b"Read-only file system" in result.stderr


def test_tmp_is_writable_and_gone_next_run():
    assert run(["touch", "/tmp/x"]).exit_code == 0  # noqa: S108, the sandbox's tmpfs
    assert run(["test", "-e", "/tmp/x"]).exit_code == 1  # noqa: S108


# both exist wherever the tests run, so a pass means the jail hid them
@pytest.mark.parametrize(
    "path",
    [Path(__file__).resolve(), Path(sys.prefix).resolve()],
    ids=["test file", "venv"],
)
def test_host_files_not_visible(path):
    assert path.exists()
    assert run(["test", "-e", str(path)]).exit_code == 1


def test_no_processes_visible():
    # /proc in the jail is an empty mount point, nothing gets mounted on it
    result = run(["ls", "-A", "/proc"])
    assert (result.exit_code, result.stdout) == (0, b"")


# coreutils can't open sockets or make syscalls like chroot, so these run python
# from the host's root under the same bwrap flags


@pytest.fixture
def probe(monkeypatch):
    assert Path("/usr/bin/python3").exists(), "the probes need /usr/bin/python3"
    monkeypatch.setattr(runner, "JAIL", "/")

    def probe(code):
        result = run(["python3", "-c", code])
        assert result.exit_code == 0, result.stderr
        return result.stdout.decode().strip()

    return probe


def test_no_network(probe):
    assert probe("import socket; print(socket.if_nameindex())") == "[(1, 'lo')]"


def test_own_pid_namespace(probe):
    # bwrap is pid 1, the command 2
    assert int(probe("import os; print(os.getpid())")) <= 2


def test_no_capabilities(probe):
    code = """
import os
try:
    os.chroot("/")
    print("chroot worked")
except PermissionError:
    print("denied")
"""
    assert probe(code) == "denied"
