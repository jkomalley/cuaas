#!/bin/bash
# everything the service needs: bwrap, the gnu coreutils jail, the cuaas user,
# uv. used by the dev vm, ci and the image build. run as root, idempotent.
set -euo pipefail

# libc-bin_locale has C.utf8. without it LC_ALL=C.UTF-8 silently falls back to C
RELEASE=ubuntu-26.04
SLICES="coreutils-from-gnu_bins libc-bin_locale"
UV_VERSION=0.13.1

export DEBIAN_FRONTEND=noninteractive

if ! command -v bwrap >/dev/null || ! command -v python3 >/dev/null; then
  apt-get update -qq
  apt-get install -y -qq --no-install-recommends bubblewrap python3-venv >/dev/null
fi

# re-cut only when the release or slices change
stamp="$RELEASE $SLICES"
if [[ "$(cat /jail/.chisel 2>/dev/null)" != "$stamp" ]]; then
  snap wait system seed.loaded
  snap list chisel >/dev/null 2>&1 || snap install chisel
  # snap confinement, chisel can only write under $HOME
  rm -rf /root/jail /jail
  mkdir /root/jail
  # shellcheck disable=SC2086
  chisel cut --release "$RELEASE" --root /root/jail $SLICES
  mv /root/jail /jail
  # mount points, bwrap can't create them in a read-only root
  mkdir /jail/dev /jail/proc /jail/tmp
  echo "$stamp" >/jail/.chisel
fi

# with apparmor_restrict_unprivileged_userns=1, only programs with an apparmor
# profile allowing it can create user namespaces. bwrap-userns-restrict is that
# profile. 26.04 loads it by default, older releases only ship it in
# extra-profiles. in a container the host's policy applies
profile=bwrap-userns-restrict
if aa-enabled -q 2>/dev/null && ! systemd-detect-virt --container -q \
  && [[ ! -e /etc/apparmor.d/$profile && -e /usr/share/apparmor/extra-profiles/$profile ]]; then
  cp "/usr/share/apparmor/extra-profiles/$profile" /etc/apparmor.d/
  apparmor_parser -r "/etc/apparmor.d/$profile"
fi

# service user. bwrap runs unprivileged as this, hence the userns bit above
id cuaas >/dev/null 2>&1 || useradd --system --no-create-home --shell /usr/sbin/nologin cuaas

# ubuntu's python is externally managed, so uv gets its own venv
if [[ "$(/usr/local/bin/uv --version 2>/dev/null)" != "uv $UV_VERSION"* ]]; then
  rm -rf /opt/uv
  python3 -m venv /opt/uv
  /opt/uv/bin/pip install -q --disable-pip-version-check "uv==$UV_VERSION"
  ln -sf /opt/uv/bin/uv /usr/local/bin/uv
fi
