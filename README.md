# cuaas
Coreutils as a service

GNU coreutils behind an API.

## Development

Needs [uv](https://docs.astral.sh/uv/) and [just](https://just.systems).

```sh
uv sync
just dev     # http://127.0.0.1:8000/docs
just test
just fix     # fix lint and format
just check   # lint + types + tests, same as ci
```
