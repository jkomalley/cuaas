# cuaas
Coreutils as a service

## Usage

Run:

```sh
uv run fastapi run
```

Then in another shell run:

```sh
# echo -n hello world
curl -X POST localhost:8000/echo \
  -H 'content-type: application/json' \
  -d '{"args": ["hello", "world"], "no_newline": true}'
```

```json
{"stdout": "hello world", "stderr": "", "exit_code": 0}
```

## Development

```sh
uv sync
uv run fastapi dev   # http://127.0.0.1:8000/docs
uv run pytest
uv run ruff check --fix
uv run ruff format
uv run ty check
```
