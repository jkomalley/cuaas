"""A command in bwrap can't get out. `just test-bwrap`, and in the container."""

from pathlib import Path

import pytest

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


def test_tmp_is_writable():
    assert run(["touch", "/tmp/x"]).exit_code == 0  # noqa: S108, the sandbox's tmpfs


@pytest.mark.parametrize(
    "path",
    [
        str(Path(__file__).resolve().parents[1] / "pyproject.toml"),
        "/opt/cuaas/pyproject.toml",
    ],
    ids=["repo", "service"],
)
def test_host_files_not_visible(path):
    assert run(["test", "-e", path]).exit_code == 1
