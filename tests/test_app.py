"""Smoke test so there's something for pytest to run."""


def test_app_starts(client):
    assert client.get("/openapi.json").status_code == 200
