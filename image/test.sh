#!/bin/bash
# runs the sandbox tests in a throwaway container from the cuaas image.
# run in the dev vm with `just test-sandbox`, after `just build-image`. args go to pytest
set -euo pipefail

TEST=cuaas-test
repo=$(cd "$(dirname "$0")/.." && pwd)

run() { lxc exec "$TEST" -- "$@"; }

lxc delete --force "$TEST" 2>/dev/null || true
trap 'lxc delete --force "$TEST" >/dev/null 2>&1 || true' EXIT
lxc launch -q cuaas "$TEST"
run cloud-init status --wait >/dev/null

# the code and tests from the repo, the jail and python from the image
tar -C "$repo" --exclude=__pycache__ -cf - .python-version pyproject.toml uv.lock README.md src tests \
  | run bash -c 'mkdir /opt/cuaas-test && tar -C /opt/cuaas-test --no-same-owner -xf - && chown -R cuaas: /opt/cuaas-test'

# same uv bootstrap as the build
run bash -euo pipefail -c '
  python3 -m venv /tmp/uv-venv
  /tmp/uv-venv/bin/pip install -q --disable-pip-version-check uv
'

# as the unprivileged service user, so bwrap uses user namespaces like the service does
run runuser -u cuaas -- env -C /opt/cuaas-test \
  HOME=/tmp CUAAS_SANDBOX=1 UV_PYTHON_INSTALL_DIR=/opt/cuaas/python UV_CACHE_DIR=/tmp/uv-cache UV_LINK_MODE=copy \
  /tmp/uv-venv/bin/uv run --locked pytest -m sandbox "$@"
