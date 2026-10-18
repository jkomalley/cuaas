#!/bin/bash
# checks the dev box can run the sandbox, prints a fix for anything that's off.
# run in the vm by `just vm-doctor`
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
  # as the service user, the way the api runs it
  sudo -u cuaas bwrap --ro-bind /jail / --dev /dev --unshare-all --clearenv \
    -- /usr/bin/wc --version | grep -q "(GNU coreutils)"
}

venv_outside_repo() {
  [[ -n "${UV_PROJECT_ENVIRONMENT:-}" && "$UV_PROJECT_ENVIRONMENT" != "$repo"/* ]]
}

check "bwrap installed" "just vm-up" command -v bwrap
check "jail at /jail" "just vm-up" test -x /jail/usr/bin/wc
check "gnu coreutils run in bwrap as cuaas" "just vm-up" gnu_in_bwrap
check "uv installed" "just vm-up" command -v uv
check "just installed" "just vm-up" command -v just
check "venv outside the repo" "just vm-up, then a new vm-shell" venv_outside_repo
check "repo is writable" "just vm-rm && just vm-up, the mount needs :w" test -w "$repo"

exit "$failed"
