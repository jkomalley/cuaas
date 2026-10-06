# cuaas
Coreutils as a service

## Usage

Each command is a POST endpoint that takes JSON and gives back JSON.

```sh
# echo -n hello world
curl -X POST localhost:8000/echo \
  -H 'content-type: application/json' \
  -d '{"args": ["hello", "world"], "no_newline": true}'
```

```json
{"stdout": "hello world", "stderr": "", "exit_code": 0}
```

Notes:
- flags are spelled out, so `-n` is `no_newline`
- a command failing still gives you a 200, check `exit_code`
- text only for now, no binary

## Development

```sh
uv sync
uv run fastapi dev   # http://127.0.0.1:8000/docs
uv run pytest
uv run ruff check --fix
uv run ruff format
uv run ty check
```
