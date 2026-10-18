#!/bin/bash
# builds the cuaas lxd image: ubuntu 26.04, bwrap, gnu coreutils jail, the api.
# run in the dev vm with `just build-image`
set -euo pipefail

BUILD=cuaas-build
repo=$(cd "$(dirname "$0")/.." && pwd)

run() { lxc exec "$BUILD" -- "$@"; }

lxc delete --force "$BUILD" 2>/dev/null || true
trap 'lxc delete --force "$BUILD" >/dev/null 2>&1 || true' EXIT
lxc launch ubuntu:26.04 "$BUILD"
run cloud-init status --wait >/dev/null

run env DEBIAN_FRONTEND=noninteractive apt-get update -qq
run env DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends bubblewrap python3-venv

# jail: gnu coreutils and their libs, plus the C.utf8 locale so LC_ALL=C.UTF-8
# works (without it glibc quietly falls back to C). the chisel snap can only write
# in $HOME, so cut there and move it. bwrap can't mkdir mount points in a read-only
# root, so they have to exist already
run bash -euo pipefail -c '
  snap wait system seed.loaded
  snap install chisel
  mkdir /root/jail
  chisel cut --release ubuntu-26.04 --root /root/jail coreutils-from-gnu_bins libc-bin_locale
  mv /root/jail /jail
  mkdir /jail/dev /jail/proc /jail/tmp
  snap remove --purge chisel
'

# app: only what uv needs to build it, no .venv or caches from the mac
tar -C "$repo" --exclude=__pycache__ -cf - .python-version pyproject.toml uv.lock README.md src \
  | run bash -c 'mkdir -p /opt/cuaas && tar -C /opt/cuaas --no-same-owner -xf -'

# uv from pypi, in a throwaway venv since 26.04's python won't pip install system-wide.
# uv is only needed for the sync. python goes under /opt so the service user can read it
run bash -euo pipefail -c '
  python3 -m venv /tmp/uv-venv
  /tmp/uv-venv/bin/pip install -q --disable-pip-version-check uv
  cd /opt/cuaas
  UV_PYTHON_INSTALL_DIR=/opt/cuaas/python UV_CACHE_DIR=/tmp/uv-cache UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy /tmp/uv-venv/bin/uv sync --locked --no-dev
  rm -rf /tmp/uv-venv /tmp/uv-cache
'

run useradd --system --no-create-home --shell /usr/sbin/nologin cuaas
lxc file push "$repo/image/cuaas.service" "$BUILD/etc/systemd/system/cuaas.service"
run systemctl enable cuaas

lxc stop "$BUILD"
# publish under a temp alias first, so a failed publish keeps the old image
lxc image delete cuaas-new 2>/dev/null || true
lxc publish "$BUILD" --alias cuaas-new
lxc image delete cuaas 2>/dev/null || true
lxc image alias rename cuaas-new cuaas
