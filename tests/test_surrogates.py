"""Tests for lone surrogates in requests.

JSON allows "\\ud800" on its own, and pydantic accepts it as a str, but it
can't be encoded as UTF-8. Every endpoint should reject it with a 422.
"""

import json

import pytest

HIGH = "\ud800"
LOW = "\udc00"
# a valid pair, decodes to one emoji
PAIR = "😀"


def post(client, path, body):
    # json= on the test client chokes on lone surrogates before sending,
    # so send the escaped JSON text ourselves
    return client.post(
        path,
        content=json.dumps(body),
        headers={"content-type": "application/json"},
    )


@pytest.mark.parametrize(
    ("path", "body", "field"),
    [
        ("/echo", {"args": [HIGH]}, "args"),
        ("/echo", {"args": [LOW]}, "args"),
        ("/echo", {"args": ["ok", f"a{HIGH}b"]}, "args"),
        ("/echo", {"args": [f"a{HIGH}"], "no_newline": True}, "args"),
        # wc used to 500 or 200 depending on the flags, all should be 422
        ("/wc", {"stdin": f"a{HIGH}"}, "stdin"),
        ("/wc", {"stdin": f"a{LOW}"}, "stdin"),
        ("/wc", {"stdin": f"a{HIGH}", "lines": True}, "stdin"),
        ("/wc", {"stdin": f"a{HIGH}", "words": True}, "stdin"),
        ("/wc", {"stdin": f"a{HIGH}", "chars": True}, "stdin"),
        ("/wc", {"stdin": f"a{HIGH}", "bytes": True}, "stdin"),
        # reversed pair is still two lone surrogates
        ("/wc", {"stdin": LOW + HIGH}, "stdin"),
    ],
)
def test_lone_surrogate_rejected(client, path, body, field):
    response = post(client, path, body)
    assert response.status_code == 422
    # the error should point at the field, not just the body
    locs = [error["loc"][:2] for error in response.json()["detail"]]
    assert ["body", field] in locs


@pytest.mark.parametrize(
    ("path", "body", "expected"),
    [
        ("/echo", {"args": [PAIR]}, "😀\n"),
        ("/wc", {"stdin": PAIR, "chars": True}, "1\n"),
        ("/wc", {"stdin": PAIR, "bytes": True}, "4\n"),
    ],
)
def test_surrogate_pair_ok(client, path, body, expected):
    response = post(client, path, body)
    assert response.status_code == 200
    assert response.json() == {"stdout": expected, "stderr": "", "exit_code": 0}
