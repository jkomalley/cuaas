# cuaas
Coreutils as a service

GNU coreutils behind an API.

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
