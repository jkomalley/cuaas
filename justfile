set positional-arguments

# runs a command in the dev vm, in the repo
vm := "limactl shell --workdir " + quote(justfile_directory()) + " cuaas"

# list recipes
default:
    @just --list

# unit tests, no vm. extra args go to pytest
test *args:
    uv run pytest -m "not sandbox" "$@"

# sandbox tests with real bwrap, in the vm. extra args go to pytest
[linux]
test-sandbox *args:
    CUAAS_SANDBOX=1 uv run pytest -m sandbox "$@"

# sandbox tests with real bwrap, in the vm. extra args go to pytest
[macos]
test-sandbox *args:
    {{ vm }} just test-sandbox "$@"

# the api with real bwrap in the vm, on localhost:8000, reloads
[linux]
dev:
    uv run fastapi dev

# the api with real bwrap in the vm, on localhost:8000, reloads
[macos]
dev:
    {{ vm }} just dev

# check lint, formatting, and types
lint:
    uv run ruff check
    uv run ruff format --check
    uv run ty check

# fix lint and format
fix:
    uv run ruff check --fix
    uv run ruff format

# lint and unit tests, quick before a push
check: lint test

# create or start the dev vm, set it up, then vm-doctor
vm-up:
    #!/bin/bash
    set -euo pipefail
    # repo mounted writable at the same path, so fix and format work from the vm
    if limactl list -q | grep -qx cuaas; then
      limactl start cuaas
    else
      limactl start --yes --name=cuaas --mount-only "{{ justfile_directory() }}:w" lima/cuaas.yaml
    fi
    {{ vm }} sudo image/provision.sh
    {{ vm }} sudo lima/setup.sh
    just vm-doctor

# check the dev vm can run the sandbox, print fixes
vm-doctor:
    #!/bin/bash
    set -euo pipefail
    if [[ "$(limactl list --format '{{{{.Status}}' cuaas 2>/dev/null)" != Running ]]; then
      echo "FAIL dev vm running -> just vm-up"
      exit 1
    fi
    {{ vm }} scripts/vm-doctor.sh

# shell in the dev vm, in the repo
vm-shell:
    {{ vm }}

# stop the dev vm
vm-stop:
    limactl stop cuaas

# build the lxd image in the dev vm
build-image:
    limactl shell --workdir "{{ justfile_directory() }}" cuaas image/build.sh

# delete the dev vm
vm-rm:
    limactl delete --force cuaas
