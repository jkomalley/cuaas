set positional-arguments

# runs a command in the dev vm, in the repo
vm := "limactl shell --workdir " + quote(justfile_directory()) + " cuaas"

# list recipes
default:
    @just --list

# unit tests, no vm. extra args go to pytest
test *args:
    uv run pytest -m "not sandbox and not deploy" "$@"

# sandbox tests with bwrap, in the vm. extra args go to pytest
[linux]
test-sandbox *args:
    CUAAS_SANDBOX=1 uv run pytest -m sandbox "$@"

# sandbox tests with bwrap, in the vm. extra args go to pytest
[macos]
test-sandbox *args:
    {{ vm }} just test-sandbox "$@"

# build the image, launch it like on the vps, http tests. extra args go to pytest
[linux]
test-deploy *args:
    scripts/test-deploy.sh "$@"

# build the image, launch it like on the vps, http tests. extra args go to pytest
[macos]
test-deploy *args:
    {{ vm }} just test-deploy "$@"

# unit, sandbox and deploy tests, what ci runs
test-all: test test-sandbox test-deploy

# the api in the vm, on localhost:8000, reloads
[linux]
dev:
    uv run fastapi dev

# the api in the vm, on localhost:8000, reloads
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
      limactl disk ls 2>/dev/null | grep -q '^cuaas-lxd ' || limactl disk create cuaas-lxd --size 20GiB
      limactl start --yes --name=cuaas --mount-only "{{ justfile_directory() }}:w" lima/cuaas.yaml
    fi
    {{ vm }} sudo image/provision.sh
    {{ vm }} sudo lima/setup.sh
    {{ vm }} sudo host/setup.sh /mnt/lima-cuaas-lxd
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

# build the lxd image
[linux]
build-image:
    image/build.sh

# build the lxd image, in the vm
[macos]
build-image:
    {{ vm }} just build-image

# delete the dev vm and its lxd disk, vm-up builds a fresh one
vm-rm:
    limactl delete --force cuaas
    limactl disk delete cuaas-lxd 2>/dev/null || true
