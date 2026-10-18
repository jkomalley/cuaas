"""Strict json on the api routes, and the 500."""

import json

import pytest
from fastapi.testclient import TestClient

from cuaas.api import router
from cuaas.main import create_app
from cuaas.routing import StrictJSONRoute
from cuaas.runner import SandboxError

HIGH = "\ud800"
LOW = "\udc00"


def post(client, path, body):
    # json= on the test client chokes on lone surrogates before sending,
    # so send the escaped json text ourselves
    return client.post(
        path,
        content=json.dumps(body),
        headers={"content-type": "application/json"},
    )


@pytest.mark.parametrize(
    "body",
    [
        {"stdin": f"a{HIGH}"},
        {"stdin": f"a{LOW}"},
        # reversed pair is still two lone surrogates
        {"stdin": LOW + HIGH},
        {"args": ["ok", HIGH]},
    ],
)
def test_lone_surrogate_rejected(client, fake, body):
    response = post(client, "/wc", body)
    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "json_invalid"
    assert fake.calls == []


@pytest.mark.usefixtures("fake")
def test_surrogate_pair_ok(client):
    # json.dumps sends this as the escaped pair "😀"
    response = post(client, "/cat", {"stdin": "\U0001f600"})
    assert response.status_code == 200
    assert response.json()["stdout"] == "\U0001f600"


@pytest.mark.parametrize(
    ("body", "loc", "value"),
    [
        ('{"stdin": NaN}', ["body", "stdin"], "NaN"),
        ('{"lines": -Infinity}', ["body", "lines"], "-Infinity"),
        # valid json, but too big for a float so it parses as inf
        ('{"stdin": 1e999}', ["body", "stdin"], "Infinity"),
        ('{"args": ["ok", [Infinity]]}', ["body", "args", 1, 0], "Infinity"),
    ],
)
def test_non_finite_rejected(client, fake, body, loc, value):
    # a 422 echoes the input, and inf/nan can't be sent back as json
    response = client.post(
        "/wc", content=body, headers={"content-type": "application/json"}
    )
    assert response.status_code == 422
    error = response.json()["detail"][0]
    assert error["type"] == "finite_number"
    assert error["loc"] == loc
    assert error["input"] == value
    assert fake.calls == []


@pytest.mark.parametrize(
    ("content_type", "body"),
    [
        ("text/plain", b'{"stdin": "a"}'),
        # what curl -d sends without -H
        ("application/x-www-form-urlencoded", b"stdin=a"),
        # fastapi's own 422 would echo this and crash on the invalid utf-8
        ("text/plain", b"caf\xe9"),
        (None, b'{"stdin": "a"}'),
        # malformed, fastapi treats it as text/plain
        ("application/foo/bar+json", b'{"stdin": "a"}'),
    ],
)
def test_non_json_rejected(client, fake, content_type, body):
    headers = {"content-type": content_type} if content_type else {}
    response = client.post("/wc", content=body, headers=headers)
    assert response.status_code == 415
    assert fake.calls == []


@pytest.mark.parametrize(
    "content_type", ["application/json; charset=utf-8", "application/vnd.api+json"]
)
@pytest.mark.usefixtures("fake")
def test_json_content_types_ok(client, content_type):
    response = client.post(
        "/wc", content=b'{"stdin": "a"}', headers={"content-type": content_type}
    )
    assert response.status_code == 200


def test_routes_parse_strict_json():
    # a route without StrictJSONRoute would let surrogates in
    assert router.routes
    for route in router.routes:
        assert isinstance(route, StrictJSONRoute), route


class BrokenRunner:
    async def run(self, *_args, **_kwargs):
        msg = "execvp /usr/bin/wc: No such file or directory"
        raise SandboxError(msg)


def test_sandbox_error_is_500_without_details(caplog):
    # no `with`, so startup's gnu check doesn't hit the broken runner
    client = TestClient(create_app(BrokenRunner()))
    response = client.post("/wc", json={})
    assert response.status_code == 500
    assert response.json() == {"detail": "Sandbox error"}
    # the real error is only in the log
    assert "execvp" in caplog.text
