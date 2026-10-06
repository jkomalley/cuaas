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

Needs [uv](https://docs.astral.sh/uv/) and [just](https://just.systems).

```sh
uv sync
just dev     # http://127.0.0.1:8000/docs
just test
just fix     # fix lint and format
just check   # lint + types + tests, same as ci
```
