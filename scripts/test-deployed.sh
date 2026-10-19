#!/bin/bash
# builds the image, launches it with the cuaas profile (no nic,
# proxy device for the port), runs the deployed checks against it, then the
# isolation tests inside it as cuaas. extra args go to the deployed checks.
# needs host/setup.sh. run via `just test-deployed`
set -euo pipefail
# lxc launch/create read yaml from stdin when it's not a tty. under just and
# limactl shell it never gets EOF and hangs
exec </dev/null

NAME=cuaas-deployed-test
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
up=false
for _ in $(seq 60); do
  curl -sf --max-time 5 "http://127.0.0.1:$PORT/openapi.json" >/dev/null && up=true && break
  sleep 0.5
done
if ! $up; then
  echo "api didn't come up, cuaas.service log:" >&2
  lxc_t 30 exec "$NAME" -- journalctl -u cuaas --no-pager -n 50 >&2 || true
  exit 1
fi

rc=0
CUAAS_URL=http://127.0.0.1:$PORT CUAAS_CONTAINER=$NAME uv run pytest -m deployed "$@" || rc=1

# the isolation tests again, in the container as cuaas. the image has no pytest
# and no network, so push the locked test group in. pure python, no build needed
stage=$(mktemp -d)
trap 'rm -rf "$stage"; lxc_t 60 delete --force "$NAME" >/dev/null 2>&1 || true' EXIT
mkdir -p "$stage/cuaas-test/tests"
uv export --quiet --frozen --only-group test --no-hashes --no-emit-project >"$stage/req.txt"
uv pip install --quiet --target "$stage/cuaas-test/site" --python-version "$(cat "$repo/.python-version")" \
  --no-deps -r "$stage/req.txt"
cp "$repo"/tests/{__init__,helpers,test_isolation}.py "$stage/cuaas-test/tests/"
lxc_t 120 file push -q -r "$stage/cuaas-test" "$NAME/tmp/"
echo "isolation tests in $NAME, as cuaas:"
lxc_t 300 exec -T "$NAME" --env TERM=dumb --cwd /tmp/cuaas-test -- sudo -u cuaas \
  env PYTHONPATH=/tmp/cuaas-test/site PYTHONDONTWRITEBYTECODE=1 \
  /opt/cuaas/.venv/bin/python -m pytest -p no:cacheprovider -o markers=bwrap tests/test_isolation.py \
  || rc=1

exit "$rc"
