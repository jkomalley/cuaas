#!/bin/bash
# dev vm only, on top of image/provision.sh: just, and the venv out of the repo.
# run as root by `just vm-up`, safe to rerun
set -euo pipefail

if ! command -v just >/dev/null; then
  apt-get update -qq
  DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends just >/dev/null
fi

# the repo is shared with the mac, so the linux venv lives outside it and the
# two never clash. limactl shell runs a login shell, which reads this
# shellcheck disable=SC2016
echo 'export UV_PROJECT_ENVIRONMENT="$HOME/.venvs/cuaas"' >/etc/profile.d/cuaas.sh
