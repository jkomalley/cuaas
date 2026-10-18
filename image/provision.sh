#!/bin/bash
# what the service needs to run commands: bwrap, the gnu coreutils jail, the
# cuaas user, uv. same script for the dev vm, the ci runner and the image build,
# so all three run the same thing. run as root, safe to rerun
set -euo pipefail

# chisel slices for the jail: gnu coreutils and their libs, plus the C.utf8
# locale so LC_ALL=C.UTF-8 works (without it glibc quietly falls back to C)
RELEASE=ubuntu-26.04
SLICES="coreutils-from-gnu_bins libc-bin_locale"
UV_VERSION=0.13.1

export DEBIAN_FRONTEND=noninteractive

if ! command -v bwrap >/dev/null || ! command -v python3 >/dev/null; then
  apt-get update -qq
  apt-get install -y -qq --no-install-recommends bubblewrap python3-venv >/dev/null
fi

# the jail. skipped when it was cut from the same release and slices, so reruns are quick
stamp="$RELEASE $SLICES"
if [[ "$(cat /jail/.chisel 2>/dev/null)" != "$stamp" ]]; then
  snap wait system seed.loaded
  snap list chisel >/dev/null 2>&1 || snap install chisel
  # the chisel snap can only write in $HOME, so cut there and move it
  rm -rf /root/jail /jail
  mkdir /root/jail
  # shellcheck disable=SC2086
  chisel cut --release "$RELEASE" --root /root/jail $SLICES
  mv /root/jail /jail
  # bwrap can't mkdir mount points in a read-only root, so they have to exist already
  mkdir /jail/dev /jail/proc /jail/tmp
  echo "$stamp" >/jail/.chisel
fi

# with kernel.apparmor_restrict_unprivileged_userns on, only programs apparmor
# allows can make user namespaces. ubuntu's bwrap-userns-restrict profile allows
# bwrap and strips caps from what it runs. 26.04 loads it already, older releases
# only ship it in extra-profiles. not in a container, lxd's host profile covers that
profile=bwrap-userns-restrict
if aa-enabled -q 2>/dev/null && ! systemd-detect-virt --container -q \
  && [[ ! -e /etc/apparmor.d/$profile && -e /usr/share/apparmor/extra-profiles/$profile ]]; then
  cp "/usr/share/apparmor/extra-profiles/$profile" /etc/apparmor.d/
  apparmor_parser -r "/etc/apparmor.d/$profile"
fi

# the service user, bwrap runs as this so it uses user namespaces like in prod
id cuaas >/dev/null 2>&1 || useradd --system --no-create-home --shell /usr/sbin/nologin cuaas

# uv from pypi, in its own venv since ubuntu's python won't pip install system-wide
if [[ "$(/usr/local/bin/uv --version 2>/dev/null)" != "uv $UV_VERSION"* ]]; then
  rm -rf /opt/uv
  python3 -m venv /opt/uv
  /opt/uv/bin/pip install -q --disable-pip-version-check "uv==$UV_VERSION"
  ln -sf /opt/uv/bin/uv /usr/local/bin/uv
fi
