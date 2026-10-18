"""Run commands in a bwrap sandbox, or pretend to on the mac."""

import asyncio
import json
import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Sequence

BWRAP = "/usr/bin/bwrap"
# chiselled gnu coreutils, see image/build.sh
JAIL = "/jail"


@dataclass(frozen=True)
class Result:
    """What a command did."""

    stdout: bytes
    stderr: bytes
    # the command's exit code, 128 + signal if it was killed
    exit_code: int


class SandboxError(Exception):
    """The sandbox couldn't run the command. Our fault, not the request's."""


class Runner(Protocol):
    """Runs a command with stdin."""

    async def run(self, argv: Sequence[str], stdin: bytes = b"") -> Result:
        """Run argv[0] with the rest of argv as its args."""
        ...


def bwrap_argv(argv: Sequence[str], status_fd: int) -> list[str]:
    """Return the bwrap command line that runs argv in the jail."""
    cmd = argv[0] if argv else ""
    # a bare name in the jail's /usr/bin, never a path. the allowlist is the real check
    if not cmd or "/" in cmd or cmd in {".", ".."}:
        msg = f"not a command name: {cmd!r}"
        raise ValueError(msg)
    # fmt: off
    return [
        BWRAP,
        # the jail as a read-only /, a minimal /dev, an empty /tmp. no /proc,
        # lxcfs in the container won't let bwrap mount one
        "--ro-bind", JAIL, "/",
        "--dev", "/dev",
        "--tmpfs", "/tmp",  # noqa: S108, a fresh tmpfs inside the sandbox
        # new user/pid/net/ipc/uts/cgroup namespaces, so no network
        "--unshare-all",
        # the command dies if we do, and can't inject into a terminal (TIOCSTI)
        "--die-with-parent",
        "--new-session",
        "--cap-drop", "ALL",
        # nothing from our env. C.UTF-8 so wc -m and friends see utf-8 chars
        "--clearenv",
        "--setenv", "LC_ALL", "C.UTF-8",
        # bwrap writes the exit code here, only if the command actually ran
        "--json-status-fd", str(status_fd),
        # everything after -- is the command, never bwrap options
        "--", f"/usr/bin/{cmd}", *argv[1:],
    ]
    # fmt: on


def parse_status(status: str) -> int | None:
    """Return the exit code from bwrap's json status, None if the command never ran."""
    # one json object per line. the exit code comes last, after the command exits,
    # so take the last one in case anything before it isn't bwrap's
    exit_code = None
    for line in status.splitlines():
        if line.strip():
            exit_code = json.loads(line).get("exit-code", exit_code)
    return exit_code


class BwrapRunner:
    """Runs each command in a fresh bwrap sandbox."""

    async def run(self, argv: Sequence[str], stdin: bytes = b"") -> Result:
        """Run argv in the jail, raising SandboxError if bwrap couldn't."""
        read_fd, write_fd = os.pipe()
        # closes our read end however we leave
        with open(read_fd, "rb") as status:  # noqa: ASYNC230, PTH123
            try:
                proc = await asyncio.create_subprocess_exec(
                    *bwrap_argv(argv, write_fd),
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    pass_fds=(write_fd,),
                    # bwrap needs nothing from our env
                    env={},
                )
            except OSError as e:
                # no bwrap at all, like on the mac
                msg = f"can't start {BWRAP}: {e}"
                raise SandboxError(msg) from e
            finally:
                # bwrap has its own copy. ours would keep the pipe open forever
                os.close(write_fd)
            # also swallows EPIPE when the command exits before reading all of stdin
            stdout, stderr = await proc.communicate(stdin)
            # bwrap has exited and closed its end, so this doesn't block
            exit_code = parse_status(status.read().decode())
        if exit_code is None:
            # bwrap's own error, like "execvp /usr/bin/sh: No such file or directory"
            raise SandboxError(stderr.decode(errors="replace").strip())
        return Result(stdout=stdout, stderr=stderr, exit_code=exit_code)


@dataclass
class FakeRunner:
    """Pretends to run commands, for the mac and the fast tests."""

    # returned for every call when set
    result: Result | None = None
    calls: list[tuple[list[str], bytes]] = field(default_factory=list)

    async def run(self, argv: Sequence[str], stdin: bytes = b"") -> Result:
        """Record the call, return result, a gnu --version, or stdin echoed."""
        self.calls.append((list(argv), stdin))
        if self.result is not None:
            return self.result
        # enough for check_gnu
        if list(argv[1:]) == ["--version"]:
            return Result(f"{argv[0]} (GNU coreutils) fake\n".encode(), b"", 0)
        return Result(stdout=stdin, stderr=b"", exit_code=0)


def get_runner() -> Runner:
    """Return the runner CUAAS_RUNNER names, bwrap by default."""
    # bwrap by default, so a server missing the setting fails check_gnu loudly
    # instead of quietly faking
    name = os.environ.get("CUAAS_RUNNER", "bwrap")
    if name == "bwrap":
        return BwrapRunner()
    if name == "fake":
        return FakeRunner()
    msg = f"CUAAS_RUNNER must be bwrap or fake, not {name!r}"
    raise ValueError(msg)


async def check_gnu(runner: Runner) -> str:
    """Return the coreutils version line, or raise if it isn't GNU."""
    result = await runner.run(["wc", "--version"])
    first = result.stdout.decode(errors="replace").partition("\n")[0]
    if result.exit_code != 0 or "(GNU coreutils)" not in first:
        found = first or result.stderr.decode(errors="replace").strip()
        msg = f"not GNU coreutils: {found!r}"
        raise RuntimeError(msg)
    return first
