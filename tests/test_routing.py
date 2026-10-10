"""Tests for strict JSON parsing in command routes."""

import importlib
import json
import pkgutil

import pytest

from cuaas import commands
from cuaas.routing import StrictJSONRoute

HIGH = "\ud800"
LOW = "\udc00"


def post(client, path, body):
    # json= on the test client chokes on lone surrogates before sending,
    # so send the escaped JSON text ourselves
    return client.post(
        path,
        content=json.dumps(body),
        headers={"content-type": "application/json"},
    )


@pytest.mark.parametrize(
    ("path", "body"),
    [
        ("/wc", {"stdin": f"a{HIGH}"}),
        ("/wc", {"stdin": f"a{LOW}"}),
        # reversed pair is still two lone surrogates
        ("/wc", {"stdin": LOW + HIGH}),
        ("/echo", {"args": ["ok", HIGH]}),
    ],
)
def test_lone_surrogate_rejected(client, path, body):
    response = post(client, path, body)
    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "json_invalid"


def test_surrogate_pair_ok(client):
    # json.dumps sends this as the escaped pair "\ud83d\ude00"
    response = post(client, "/echo", {"args": ["\U0001f600"]})
    assert response.status_code == 200
    assert response.json()["stdout"] == "\U0001f600\n"


@pytest.mark.parametrize(
    ("path", "body", "loc", "value"),
    [
        ("/wc", '{"stdin": NaN}', ["body", "stdin"], "NaN"),
        ("/wc", '{"lines": -Infinity}', ["body", "lines"], "-Infinity"),
        # valid JSON, but too big for a float so it parses as inf
        ("/wc", '{"stdin": 1e999}', ["body", "stdin"], "Infinity"),
        ("/echo", '{"args": ["ok", [Infinity]]}', ["body", "args", 1, 0], "Infinity"),
    ],
)
def test_non_finite_rejected(client, path, body, loc, value):
    # a 422 echoes the input, and inf/nan can't be sent back as JSON
    response = client.post(
        path, content=body, headers={"content-type": "application/json"}
    )
    assert response.status_code == 422
    error = response.json()["detail"][0]
    assert error["type"] == "finite_number"
    assert error["loc"] == loc
    assert error["input"] == value


@pytest.mark.parametrize(
    ("content_type", "body"),
    [
        ("text/plain", b'{"stdin": "a"}'),
        ("application/x-www-form-urlencoded", b"stdin=a"),
        # fastapi's own 422 would echo this and crash on the invalid UTF-8
        ("text/plain", b"caf\xe9"),
        (None, b'{"stdin": "a"}'),
        # malformed, fastapi treats it as text/plain
        ("application/foo/bar+json", b'{"stdin": "a"}'),
    ],
)
def test_non_json_rejected(client, content_type, body):
    headers = {"content-type": content_type} if content_type else {}
    response = client.post("/wc", content=body, headers=headers)
    assert response.status_code == 415


@pytest.mark.parametrize(
    "content_type", ["application/json; charset=utf-8", "application/vnd.api+json"]
)
def test_json_content_types_ok(client, content_type):
    response = client.post(
        "/wc", content=b'{"stdin": "a"}', headers={"content-type": content_type}
    )
    assert response.status_code == 200


@pytest.mark.parametrize(
    "name", [m.name for m in pkgutil.iter_modules(commands.__path__)]
)
def test_routes_parse_strict_json(name):
    # a router without route_class=StrictJSONRoute would let surrogates in
    router = importlib.import_module(f"cuaas.commands.{name}").router
    assert router.routes
    for route in router.routes:
        assert isinstance(route, StrictJSONRoute), route.path
