#!/bin/bash
# builds the image, launches it the way the vps will (cuaas profile, no nic,
# proxy device for the port) and runs the deploy tests. extra args go to pytest.
# needs host/setup.sh. run via `just test-deploy`
set -euo pipefail
# lxc launch/create read yaml from stdin when it's not a tty. under just and
# limactl shell it never gets EOF and hangs
exec </dev/null

NAME=cuaas-deploy-test
PORT=18000
repo=$(cd "$(dirname "$0")/.." && pwd)
# shellcheck source=scripts/lxc.sh
source "$repo/scripts/lxc.sh"

"$repo/image/build.sh"

lxc_t 60 delete --force "$NAME" 2>/dev/null || true
trap 'lxc_t 60 delete --force "$NAME" >/dev/null 2>&1 || true' EXIT
# no nic on purpose, ignore lxc's warning
launch cuaas "$NAME" --profile cuaas
lxc_t 60 config device add "$NAME" api proxy \
  listen=tcp:127.0.0.1:$PORT connect=tcp:127.0.0.1:8000 >/dev/null

booted "$NAME"

# wait for the api to listen, it runs check_gnu first
for _ in $(seq 60); do
  curl -sf "http://127.0.0.1:$PORT/openapi.json" >/dev/null && break
  sleep 0.5
done

CUAAS_URL=http://127.0.0.1:$PORT CUAAS_CONTAINER=$NAME uv run pytest -m deploy "$@"
