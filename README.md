# cuaas
Coreutils as a service

Real GNU coreutils behind an API. For anyone who lost theirs (Ubuntu switched to the Rust ones)
or never had them (Windows).

Starting over. The old python reimplementation is tagged `python-reimpl`.

## Development

Needs [uv](https://docs.astral.sh/uv/) and [just](https://just.systems).

```sh
uv sync
just dev     # http://127.0.0.1:8000/docs
just test
just fix     # fix lint and format
just check   # lint + types + tests, same as ci
```
