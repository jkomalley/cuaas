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

Needs [uv](https://docs.astral.sh/uv/), [just](https://just.systems) and
[lima](https://lima-vm.io). App tests run on the mac, everything else in an ubuntu
26.04 vm that's set up the same way as ci and the image.

```sh
just vm-up          # create or start the vm, set it up, check it
just test           # app + bwrap tests, seconds
just test-app       # our code without bwrap, on the mac
just test-bwrap     # runs commands in bwrap, in the vm
just test-deployed  # build the image, launch it like on the vps, check it
just test-all       # all of the above
just dev            # the api in the vm, http://127.0.0.1:8000/docs
just fix            # fix lint and format
just check          # lint + test
just vm-doctor      # what's wrong with the vm and how to fix it
```

`just vm-rm && just vm-up` gets you a fresh vm, nothing to do by hand. `uv sync` on
the mac is just for the editor, the vm keeps its venv in `~/.venvs/cuaas`.

- `image/provision.sh` sets up bwrap, the gnu coreutils jail, the cuaas user and uv.
  same script in the vm, in ci and in the image
- `host/setup.sh` sets up lxd, same for the vm, ci and the vps
- `image/build.sh` builds the image, `scripts/test-deployed.sh` launches it with no
  network and a proxy device for the port
- lxc runs through sudo with timeouts and never gets stdin, see `scripts/lxc.sh`
