# cuaas
Coreutils as a service

GNU coreutils behind an API.

## Usage

`POST /<cmd>` with args and stdin, get stdout, stderr and the exit code back.

```sh
curl -X POST localhost:8000/wc \
  -H 'content-type: application/json' \
  -d '{"args": ["-l"], "stdin": "a\nb\n"}'
```

```json
{"stdout": "2\n", "stdout_encoding": "utf-8", "stderr": "", "stderr_encoding": "utf-8", "exit_code": 0}
```

- no body is fine, `curl -X POST localhost:8000/true`
- the content-type header is needed, plain `curl -d` gets a 415
- bytes go in with `"stdin_encoding": "base64"`, stdout/stderr come back base64 if they aren't utf-8
- a failing command is still a 200, check `exit_code`. 422 is a bad request, 404 a command that isn't allowed
- `/docs` lists the commands. no timeouts yet, so nothing like `yes` or `sleep`

## Development

Needs [uv](https://docs.astral.sh/uv/) and [just](https://just.systems).

```sh
uv sync
just serve-fake  # http://127.0.0.1:8000/docs
just test
just fix         # fix lint and format
just check       # lint + types + tests, same as ci
```

`serve-fake` and `test` use a fake runner, no sandbox needed.

### Real sandbox

Needs [lima](https://lima-vm.io). The vm runs lxd, the image has the api, bwrap and a
GNU coreutils jail.

```sh
just vm-up          # create or start the vm
just build-image    # build the lxd image
just test-sandbox   # sandbox tests in a container from the image
just vm-shell       # shell in the vm
```
