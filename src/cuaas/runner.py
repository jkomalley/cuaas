"""Run commands in a bwrap sandbox."""

import asyncio
import json
import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Sequence

BWRAP = "/usr/bin/bwrap"
# chiselled gnu coreutils, built by image/provision.sh
JAIL = "/jail"


@dataclass(frozen=True)
class Result:
    """What a command did."""

    stdout: bytes
    stderr: bytes
    # the command's exit code, 128 + signal if it was killed
    exit_code: int


class SandboxError(Exception):
    """Bwrap failed to run the command. A server problem, not a bad request."""


class Runner(Protocol):
    """Runs a command with stdin."""

    async def run(self, argv: Sequence[str], stdin: bytes = b"") -> Result:
        """Run argv[0] with the rest of argv as its args."""
        ...


def check_argv(argv: Sequence[str]) -> None:
    """Raise ValueError for argv no runner can run."""
    cmd = argv[0] if argv else ""
    # bare name under the jail's /usr/bin, never a path. allowlist is checked elsewhere
    if not cmd or "/" in cmd or cmd in {".", ".."}:
        msg = f"not a command name: {cmd!r}"
        raise ValueError(msg)
    # clearer than subprocess's "embedded null byte"
    for i, arg in enumerate(argv):
        if "\0" in arg:
            msg = f"NUL byte in argv[{i}]"
            raise ValueError(msg)


def bwrap_argv(argv: Sequence[str], status_fd: int) -> list[str]:
    """Return the bwrap command line that runs argv in the jail."""
    check_argv(argv)
    cmd = argv[0]
    # fmt: off
    return [
        BWRAP,
        # jail as read-only /, minimal /dev, fresh /tmp. no /proc, lxcfs in the
        # container blocks bwrap from mounting it
        "--ro-bind", JAIL, "/",
        "--dev", "/dev",
        "--tmpfs", "/tmp",  # noqa: S108, private to the sandbox
        # new user/pid/net/ipc/uts/cgroup namespaces, so no network
        "--unshare-all",
        # die with the server. new session blocks TIOCSTI terminal injection
        "--die-with-parent",
        "--new-session",
        "--cap-drop", "ALL",
        # empty env. C.UTF-8 so wc -m etc count utf-8 chars
        "--clearenv",
        "--setenv", "LC_ALL", "C.UTF-8",
        # otherwise bwrap keeps the server's cwd if that path exists in the jail
        "--chdir", "/",
        # bwrap writes the exit code here, only if the command started
        "--json-status-fd", str(status_fd),
        # gnu uses argv[0] in errors and --help: "wc: ..." not "/usr/bin/wc: ..."
        "--argv0", cmd,
        # everything after -- is the command, never bwrap options
        "--", f"/usr/bin/{cmd}", *argv[1:],
    ]
    # fmt: on


def parse_status(status: str) -> int | None:
    """Return the exit code from bwrap's json status, None if the command never ran."""
    # one json object per line, exit-code is the last. scan from the end and skip
    # anything that doesn't parse
    exit_code = None
    for line in reversed(status.splitlines()):
        try:
            obj = json.loads(line)
        except ValueError:
            # empty, or truncated if bwrap died mid-write
            continue
        if isinstance(obj, dict) and "exit-code" in obj:
            exit_code = obj["exit-code"]
            break
    return exit_code


class BwrapRunner:
    """Runs each command in a fresh bwrap sandbox."""

    async def run(self, argv: Sequence[str], stdin: bytes = b"") -> Result:
        """Run argv in the jail, raising SandboxError if bwrap couldn't."""
        read_fd, write_fd = os.pipe()
        # closes the read end on any exit
        with open(read_fd, "rb") as status:  # noqa: ASYNC230, PTH123
            try:
                proc = await asyncio.create_subprocess_exec(
                    *bwrap_argv(argv, write_fd),
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    pass_fds=(write_fd,),
                    # don't pass the server's env to bwrap
                    env={},
                )
            except OSError as e:
                # bwrap isn't installed
                msg = f"can't start {BWRAP}: {e}"
                raise SandboxError(msg) from e
            finally:
                # bwrap has its own copy. if ours stays open the read never sees EOF
                os.close(write_fd)
            # also handles EPIPE if the command exits before reading all of stdin
            stdout, stderr = await proc.communicate(stdin)
            # bwrap has exited, write end is closed, won't block
            exit_code = parse_status(status.read().decode())
        if exit_code is None:
            # bwrap itself failed, e.g. "execvp /usr/bin/sh: No such file or directory"
            raise SandboxError(stderr.decode(errors="replace").strip())
        return Result(stdout=stdout, stderr=stderr, exit_code=exit_code)


@dataclass
class FakeRunner:
    """Test double. Records calls, returns `result` if set, else echoes stdin."""

    # returned for every call when set
    result: Result | None = None
    calls: list[tuple[list[str], bytes]] = field(default_factory=list)

    async def run(self, argv: Sequence[str], stdin: bytes = b"") -> Result:
        """Record the call, return result, a gnu --version, or stdin echoed."""
        # validate like BwrapRunner, rejected calls aren't recorded
        check_argv(argv)
        self.calls.append((list(argv), stdin))
        if self.result is not None:
            return self.result
        # for check_gnu at startup
        if list(argv[1:]) == ["--version"]:
            return Result(f"{argv[0]} (GNU coreutils) fake\n".encode(), b"", 0)
        return Result(stdout=stdin, stderr=b"", exit_code=0)


async def check_gnu(runner: Runner) -> str:
    """Return the coreutils version line, or raise if it isn't GNU."""
    result = await runner.run(["wc", "--version"])
    first = result.stdout.decode(errors="replace").partition("\n")[0]
    if result.exit_code != 0 or "(GNU coreutils)" not in first:
        found = first or result.stderr.decode(errors="replace").strip()
        msg = f"not GNU coreutils: {found!r}"
        raise RuntimeError(msg)
    return first
