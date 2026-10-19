"""Deploy tests: the prod image launched like on the vps. Run via `just test-deploy`."""

import base64
import json
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor

import httpx2
import pytest

# set by scripts/test-deploy.sh
URL = os.environ.get("CUAAS_URL", "")
CONTAINER = os.environ.get("CUAAS_CONTAINER", "")

pytestmark = [
    pytest.mark.deploy,
    pytest.mark.skipif(not URL, reason="needs the launched image, see test-deploy"),
]


@pytest.fixture(scope="module")
def api():
    with httpx2.Client(base_url=URL, timeout=30) as client:
        yield client


def inside(*cmd, check=True):
    """Run cmd in the container."""
    argv = ["/usr/bin/sudo", "lxc", "exec", CONTAINER, "--", *cmd]
    # argv is hardcoded in the tests
    return subprocess.run(argv, capture_output=True, text=True, check=check)  # noqa: S603


def test_wc(api):
    r = api.post("/wc", json={"args": ["-l"], "stdin": "a b c\nd e\n"})
    assert r.status_code == 200
    assert r.json()["stdout"] == "2\n"


def test_it_is_gnu(api):
    r = api.post("/wc", json={"args": ["--version"]})
    assert "(GNU coreutils)" in r.json()["stdout"]


def test_bytes_round_trip(api):
    data = bytes(range(256))
    r = api.post(
        "/cat",
        json={"stdin": base64.b64encode(data).decode(), "stdin_encoding": "base64"},
    )
    assert base64.b64decode(r.json()["stdout"]) == data


def test_utf8_locale(api):
    # 2 in C.UTF-8, 3 if the locale silently fell back to C
    r = api.post("/wc", json={"args": ["-m"], "stdin": "é\n"})
    assert r.json()["stdout"] == "2\n"


def test_unknown_command_is_404(api):
    assert api.post("/env", json={}).status_code == 404


def test_host_fs_not_visible(api):
    r = api.post("/cat", json={"args": ["/opt/cuaas/pyproject.toml"]}).json()
    assert r["exit_code"] == 1
    assert "No such file" in r["stderr"]


def test_concurrent_requests(api):
    def wc(i):
        return api.post("/wc", json={"args": ["-l"], "stdin": "x\n" * i})

    with ThreadPoolExecutor(20) as pool:
        responses = list(pool.map(wc, range(20)))
    assert [r.status_code for r in responses] == [200] * 20
    assert [r.json()["stdout"] for r in responses] == [f"{i}\n" for i in range(20)]


# runs the installed BwrapRunner as cuaas, so the sandbox itself is checked
# under lxcfs, the container's apparmor and the service user
SANDBOX_CHECK = """
import asyncio, json
from cuaas.runner import BwrapRunner

async def main():
    out = []
    for argv in (["touch", "/x"], ["touch", "/tmp/x"], ["env"]):
        r = await BwrapRunner().run(argv)
        out.append([r.exit_code, r.stdout.decode(), r.stderr.decode()])
    print(json.dumps(out))

asyncio.run(main())
"""


def test_sandbox_as_cuaas_in_the_container():
    python = "/opt/cuaas/.venv/bin/python"
    out = inside("sudo", "-u", "cuaas", python, "-c", SANDBOX_CHECK).stdout
    root, tmp, env = json.loads(out)
    assert root[0] == 1
    assert "Read-only file system" in root[2]
    assert tmp[0] == 0
    assert sorted(env[1].splitlines()) == ["LC_ALL=C.UTF-8", "PWD=/"]


def test_no_network():
    assert inside("ls", "/sys/class/net").stdout.split() == ["lo"]


def test_service_runs_as_cuaas():
    pid = inside("systemctl", "show", "--property=MainPID", "--value", "cuaas").stdout
    assert inside("ps", "-o", "user=", "-p", pid.strip()).stdout.strip() == "cuaas"


def test_nothing_failed():
    assert inside("systemctl", "--failed", "--no-legend").stdout == ""


def test_no_dev_deps():
    # the image is synced with --no-dev
    result = inside("/opt/cuaas/.venv/bin/python", "-c", "import pytest", check=False)
    assert result.returncode != 0
