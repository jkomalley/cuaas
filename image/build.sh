#!/bin/bash
# builds the cuaas lxd image (ubuntu 26.04 + provision.sh + the app).
# needs host/setup.sh. run via `just build-image`
set -euo pipefail
# lxc launch/create read yaml from stdin when it's not a tty. under just and
# limactl shell it never gets EOF and hangs
exec </dev/null

BUILD=cuaas-build
repo=$(cd "$(dirname "$0")/.." && pwd)
# shellcheck source=scripts/lxc.sh
source "$repo/scripts/lxc.sh"

run() { lxc_t 600 exec "$BUILD" -- "$@"; }

# pull the base image up front so launch's 60s timeout doesn't include the download
lxc_t 30 image show ubuntu-26.04 >/dev/null 2>&1 \
  || lxc_t 900 image copy ubuntu:26.04 local: --alias ubuntu-26.04
# copied once, so pull the latest 26.04 base on every build
lxc_t 900 image refresh ubuntu-26.04 >/dev/null

lxc_t 60 delete --force "$BUILD" 2>/dev/null || true
trap 'lxc_t 60 delete --force "$BUILD" >/dev/null 2>&1 || true' EXIT
# default profile, needs network for apt/snap/uv
launch ubuntu-26.04 "$BUILD"
run cloud-init status --wait >/dev/null
# updates published since the base image
run bash -c 'apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get upgrade -y -qq >/dev/null'

# source + provision.sh only, no .venv or caches
tar -C "$repo" --exclude=__pycache__ -cf - \
  .python-version pyproject.toml uv.lock README.md src image/provision.sh \
  | run bash -c 'mkdir -p /opt/cuaas && tar -C /opt/cuaas --no-same-owner -xf -'

# chisel is only needed to cut the jail
run /opt/cuaas/image/provision.sh
run bash -c 'snap remove --purge chisel && rm -rf /opt/cuaas/image'

# uv's python goes under /opt/cuaas so the cuaas user can read it (default is
# /root/.local). uv itself is only needed to build
run bash -euo pipefail -c '
  cd /opt/cuaas
  UV_PYTHON_INSTALL_DIR=/opt/cuaas/python UV_CACHE_DIR=/tmp/uv-cache UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy uv sync --locked --no-dev --quiet
  rm -rf /tmp/uv-cache /opt/uv /usr/local/bin/uv
'

lxc_t 60 file push "$repo/image/cuaas.service" "$BUILD/etc/systemd/system/cuaas.service"
run systemctl enable --quiet cuaas
# no network at runtime, cloud-init has nothing to do
run touch /etc/cloud/cloud-init.disabled
# fails at boot under lxd 5.21 + 26.04, and nobody needs a console login
run systemctl mask --quiet console-getty.service

lxc_t 120 stop "$BUILD"
# publish to a temp alias then swap, a failed publish leaves the old image
lxc_t 60 image delete cuaas-new 2>/dev/null || true
lxc_t 900 publish -q "$BUILD" --alias cuaas-new
lxc_t 60 image delete cuaas 2>/dev/null || true
lxc_t 60 image alias rename cuaas-new cuaas
