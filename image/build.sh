#!/bin/bash
# builds the cuaas lxd image: ubuntu 26.04, image/provision.sh, the api.
# needs host/setup.sh first. run on linux, `just build-image`
set -euo pipefail
# lxc reads yaml from stdin when it isn't a terminal and waits for eof, which
# never comes under just or limactl shell. nothing here needs stdin
exec </dev/null

BUILD=cuaas-build
repo=$(cd "$(dirname "$0")/.." && pwd)
# shellcheck source=scripts/lxc.sh
source "$repo/scripts/lxc.sh"

run() { lxc_t 600 exec "$BUILD" -- "$@"; }

# fetch the base on its own, so a slow download isn't mistaken for a stalled launch
lxc_t 30 image show ubuntu-26.04 >/dev/null 2>&1 \
  || lxc_t 900 image copy ubuntu:26.04 local: --alias ubuntu-26.04

lxc_t 60 delete --force "$BUILD" 2>/dev/null || true
trap 'lxc_t 60 delete --force "$BUILD" >/dev/null 2>&1 || true' EXIT
# the default profile, the build needs network
launch ubuntu-26.04 "$BUILD"
run cloud-init status --wait >/dev/null

# the app and provision.sh. only what uv needs to build it, no .venv or caches
tar -C "$repo" --exclude=__pycache__ -cf - \
  .python-version pyproject.toml uv.lock README.md src image/provision.sh \
  | run bash -c 'mkdir -p /opt/cuaas && tar -C /opt/cuaas --no-same-owner -xf -'

# same setup as the dev vm and ci, then the cutter isn't needed anymore
run /opt/cuaas/image/provision.sh
run bash -c 'snap remove --purge chisel && rm -rf /opt/cuaas/image'

# python under /opt so the service user can read it, no cache left behind
run bash -euo pipefail -c '
  cd /opt/cuaas
  UV_PYTHON_INSTALL_DIR=/opt/cuaas/python UV_CACHE_DIR=/tmp/uv-cache UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy uv sync --locked --no-dev --quiet
  rm -rf /tmp/uv-cache
'

lxc_t 60 file push "$repo/image/cuaas.service" "$BUILD/etc/systemd/system/cuaas.service"
run systemctl enable --quiet cuaas
# containers from the image have no network, nothing for cloud-init to do
run touch /etc/cloud/cloud-init.disabled
# no console logins, and lxd 5.21 with 26.04 fails it at boot anyway
run systemctl mask --quiet console-getty.service

lxc_t 120 stop "$BUILD"
# publish under a temp alias first, so a failed publish keeps the old image
lxc_t 60 image delete cuaas-new 2>/dev/null || true
lxc_t 900 publish -q "$BUILD" --alias cuaas-new
lxc_t 60 image delete cuaas 2>/dev/null || true
lxc_t 60 image alias rename cuaas-new cuaas
