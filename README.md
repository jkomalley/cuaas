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

## Errors

Bad JSON or a bad value gets a 422 from pydantic:

```sh
# wc with a number instead of text
curl -X POST localhost:8000/wc \
  -H 'content-type: application/json' \
  -d '{"stdin": 5}' \
  -w '\n%{http_code}\n'
```

```
{"detail":[{"type":"string_type","loc":["body","stdin"],"msg":"Input should be a valid string","input":5}]}
422
```

If the command ran it's a 200, even if it failed. Check `exit_code` and `stderr`.

Lone surrogates like `"\ud800"` count as bad JSON, and so do `NaN`, `Infinity` and huge numbers like `1e999`. Raw bytes will go through base64 (#51).

## Development

Needs [uv](https://docs.astral.sh/uv/) and [just](https://just.systems).

```sh
uv sync
just dev     # http://127.0.0.1:8000/docs
just test
just fix     # fix lint and format
just check   # lint + types + tests, same as ci
```
