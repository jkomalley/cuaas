# cuaas
Coreutils as a service

## Usage

Each command is a POST endpoint. Args go in the query string, stdin is
the request body, and stdout comes back in the response.

```sh
# echo -n hello world
curl -X POST 'localhost:8000/echo?args=hello&args=world&n=true'
```

Notes:
- flags use the same letter as the real command (`-n` -> `n=true`)
- args have to be UTF-8, otherwise you get a 400. Use the body for binary stuff
- args live in the URL, so keep them short. Big input goes in the body
- `+` in a URL is a space, so use `%2B` if you're typing URLs by hand

## Development

```sh
uv sync
uv run fastapi dev   # http://127.0.0.1:8000/docs
uv run pytest
uv run ruff check --fix && uv run ruff format
```
