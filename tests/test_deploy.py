"""The prod image launched like on the vps, over http. `just test-deploy` runs them."""

import base64
import os
import subprocess

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
    # our own argv, run on the test host
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
