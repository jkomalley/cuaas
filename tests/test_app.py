"""The app starts."""


def test_app_starts(client):
    assert client.get("/openapi.json").status_code == 200
