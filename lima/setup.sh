#!/bin/bash
# dev vm extras on top of provision.sh: just, venv outside the repo.
# run as root by `just vm-up`, idempotent
set -euo pipefail

if ! command -v just >/dev/null; then
  apt-get update -qq
  DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends just >/dev/null
fi

# keep the vm's venv out of the shared repo so it doesn't fight the host's .venv.
# limactl shell starts a login shell, which sources profile.d
# shellcheck disable=SC2016
echo 'export UV_PROJECT_ENVIRONMENT="$HOME/.venvs/cuaas"' >/etc/profile.d/cuaas.sh
