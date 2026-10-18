import base64

import pytest

from cuaas.allowlist import ALLOWED
from cuaas.api import runner_dep
from cuaas.main import app
from cuaas.runner import FakeRunner, Result


@pytest.fixture
def fake():
    """A fresh fake runner for one test, so its calls can be checked."""
    runner = FakeRunner()
    app.dependency_overrides[runner_dep] = lambda: runner
    yield runner
    app.dependency_overrides.clear()


def test_args_and_stdin_reach_the_runner(client, fake):
    r = client.post("/wc", json={"args": ["-l", "--", "-x"], "stdin": "a\nb\n"})
    assert r.status_code == 200
    assert fake.calls == [(["wc", "-l", "--", "-x"], b"a\nb\n")]
    # the fake echoes stdin
    assert r.json() == {
        "stdout": "a\nb\n",
        "stdout_encoding": "utf-8",
        "stderr": "",
        "stderr_encoding": "utf-8",
        "exit_code": 0,
    }


def test_failing_command_is_still_200(client, fake):
    fake.result = Result(b"", b"wc: nope\n", 1)
    r = client.post("/wc", json={"args": ["nope"]})
    assert r.status_code == 200
    assert r.json()["exit_code"] == 1
    assert r.json()["stderr"] == "wc: nope\n"


@pytest.mark.parametrize("kwargs", [{}, {"json": {}}])
def test_no_body_is_empty_request(client, fake, kwargs):
    r = client.post("/true", **kwargs)
    assert r.status_code == 200
    assert fake.calls == [(["true"], b"")]


def test_binary_both_ways(client, fake):
    data = b"\x00\xff\xfe"
    r = client.post(
        "/cat",
        json={"stdin": base64.b64encode(data).decode(), "stdin_encoding": "base64"},
    )
    assert fake.calls == [(["cat"], data)]
    assert r.json()["stdout_encoding"] == "base64"
    assert base64.b64decode(r.json()["stdout"]) == data


def test_unknown_command_is_404(client, fake):
    assert client.post("/bash", json={}).status_code == 404
    assert client.post("/env", json={"args": ["sh"]}).status_code == 404
    assert fake.calls == []


def test_get_is_405(client):
    assert client.get("/wc").status_code == 405


def test_nul_in_args_is_422(client, fake):
    r = client.post("/wc", json={"args": ["-l", "a\0b"]})
    assert r.status_code == 422
    assert r.json()["detail"][0]["loc"] == ["body", "args", 1]
    assert fake.calls == []


@pytest.mark.parametrize(
    "body", [[], "wc", {"args": "-l"}, {"argz": []}, {"stdin_encoding": "hex"}]
)
def test_bad_body_is_422(client, fake, body):
    assert client.post("/wc", json=body).status_code == 422
    assert fake.calls == []


def test_a_route_per_allowed_command(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert set(paths) == {f"/{cmd}" for cmd in ALLOWED}
    assert all(set(ops) == {"post"} for ops in paths.values())
