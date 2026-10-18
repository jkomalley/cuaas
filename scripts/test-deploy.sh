#!/bin/bash
# builds the image, launches it like on the vps (cuaas profile, no network, a
# proxy device for the port) and runs the deploy tests over http. args go to pytest.
# run on linux after host/setup.sh, `just test-deploy`
set -euo pipefail
# lxc reads yaml from stdin when it isn't a terminal and waits for eof, which
# never comes under just or limactl shell. nothing here needs stdin
exec </dev/null

NAME=cuaas-deploy-test
PORT=18000
repo=$(cd "$(dirname "$0")/.." && pwd)
# shellcheck source=scripts/lxc.sh
source "$repo/scripts/lxc.sh"

"$repo/image/build.sh"

lxc_t 60 delete --force "$NAME" 2>/dev/null || true
trap 'lxc_t 60 delete --force "$NAME" >/dev/null 2>&1 || true' EXIT
# the cuaas profile alone, so no nic. lxc warns about that, it's the point
launch cuaas "$NAME" --profile cuaas
lxc_t 60 config device add "$NAME" api proxy \
  listen=tcp:127.0.0.1:$PORT connect=tcp:127.0.0.1:8000 >/dev/null

booted "$NAME"

# the api checks gnu at startup before it listens
for _ in $(seq 60); do
  curl -sf "http://127.0.0.1:$PORT/openapi.json" >/dev/null && break
  sleep 0.5
done

CUAAS_URL=http://127.0.0.1:$PORT CUAAS_CONTAINER=$NAME uv run pytest -m deploy "$@"
