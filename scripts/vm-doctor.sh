#!/bin/bash
# checks the dev vm is set up, prints the fix for each failure. run via
# `just vm-doctor`
set -uo pipefail

repo=$(cd "$(dirname "$0")/.." && pwd)
failed=0

check() {
  local what=$1 fix=$2
  shift 2
  if "$@" >/dev/null 2>&1; then
    echo "ok   $what"
  else
    echo "FAIL $what -> $fix"
    failed=1
  fi
}

gnu_in_bwrap() {
  # as cuaas, like the service
  sudo -u cuaas bwrap --ro-bind /jail / --dev /dev --unshare-all --clearenv \
    -- /usr/bin/wc --version | grep -q "(GNU coreutils)"
}

venv_outside_repo() {
  [[ -n "${UV_PROJECT_ENVIRONMENT:-}" && "$UV_PROJECT_ENVIRONMENT" != "$repo"/* ]]
}

lxd_answers() { timeout 10 sudo lxc info; }
pool_on_disk() { [[ "$(timeout 10 sudo lxc storage get default source)" == /mnt/lima-cuaas-lxd ]]; }

check "bwrap installed" "just vm-up" command -v bwrap
check "jail at /jail" "just vm-up" test -x /jail/usr/bin/wc
check "gnu coreutils run in bwrap as cuaas" "just vm-up" gnu_in_bwrap
check "uv installed" "just vm-up" command -v uv
check "just installed" "just vm-up" command -v just
check "venv outside the repo" "just vm-up, then a new vm-shell" venv_outside_repo
check "repo is writable" "just vm-rm && just vm-up, the mount needs :w" test -w "$repo"
check "lxd answers" "just vm-up" lxd_answers
check "lxd pool on its own disk" "just vm-rm && just vm-up" pool_on_disk
check "cuaas profile" "just vm-up" timeout 10 sudo lxc profile show cuaas

exit "$failed"
