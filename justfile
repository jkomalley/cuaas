# list recipes
default:
    @just --list

# api on the mac with the fake runner, reloads
serve-fake:
    CUAAS_RUNNER=fake uv run fastapi dev

# run tests, extra args go to pytest
test *args:
    uv run pytest {{ args }}

# run the sandbox tests in a container from the image, extra args go to pytest
test-sandbox *args:
    limactl shell --workdir "{{ justfile_directory() }}" cuaas image/test.sh {{ args }}

# check lint, formatting, and types
lint:
    uv run ruff check
    uv run ruff format --check
    uv run ty check

# fix lint and format
fix:
    uv run ruff check --fix
    uv run ruff format

# lint and test, same as ci
check: lint test

# create or start the dev vm, repo mounted read-only at the same path
vm-up:
    if limactl list -q | grep -qx cuaas; then limactl start cuaas; else limactl start --yes --name=cuaas --mount-only "{{ justfile_directory() }}" lima/cuaas.yaml; fi

# shell in the dev vm, in the repo
vm-shell:
    limactl shell --workdir "{{ justfile_directory() }}" cuaas

# stop the dev vm
vm-stop:
    limactl stop cuaas

# build the lxd image in the dev vm
build-image:
    limactl shell --workdir "{{ justfile_directory() }}" cuaas image/build.sh

# delete the dev vm
vm-rm:
    limactl delete --force cuaas
