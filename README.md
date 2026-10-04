# cuaas
Coreutils as a service

## Development

```sh
uv sync
uv run fastapi dev src/cuaas/main.py   # http://127.0.0.1:8000/docs
uv run pytest
uv run ruff check --fix && uv run ruff format
```
