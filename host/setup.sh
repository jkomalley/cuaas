#!/bin/bash
# lxd host setup for building and running the cuaas image. used on the dev vm,
# ci and the vps. run as root, idempotent.
# usage: host/setup.sh [STORAGE]
#   STORAGE: block device or btrfs mount for the pool. default: loop file
set -euo pipefail
# lxc launch/create read yaml from stdin when it's not a tty. under just and
# limactl shell it never gets EOF and hangs
exec </dev/null

here=$(cd "$(dirname "$0")" && pwd)
storage=${1:-}

snap wait system seed.loaded
# 5.21 lts, held so it can't refresh mid-build
snap list lxd >/dev/null 2>&1 || snap install lxd --channel=5.21/stable
snap refresh --hold lxd >/dev/null
lxd waitready --timeout=120

# fixed subnet: lima's network answers ping for every ip, so lxd's auto-pick
# thinks every subnet is in use
lxc network show lxdbr0 >/dev/null 2>&1 \
  || lxc network create lxdbr0 ipv4.address=10.64.64.1/24 ipv4.nat=true ipv6.address=none

# btrfs for snapshots. the dir driver copies the full rootfs per container
if ! lxc storage show default >/dev/null 2>&1; then
  if [[ -n "$storage" ]]; then
    lxc storage create default btrfs source="$storage"
  else
    # the default 5GiB fills up after a couple of images
    lxc storage create default btrfs size=20GiB
  fi
fi

# default profile: used by the build, has a nic
lxc profile device show default | grep -q '^root:' \
  || lxc profile device add default root disk path=/ pool=default
lxc profile device show default | grep -q '^eth0:' \
  || lxc profile device add default eth0 nic network=lxdbr0 name=eth0

# cuaas profile: used by deploys, no nic
lxc profile show cuaas >/dev/null 2>&1 || lxc profile create cuaas
lxc profile edit cuaas <"$here/cuaas-profile.yaml"

# pprof on localhost. scripts/lxc.sh dumps goroutines from it on a timeout
lxc config set core.debug_address 127.0.0.1:8444

# the ci runner has docker, whose FORWARD DROP policy blocks lxdbr0 traffic
if iptables -L DOCKER-USER -n >/dev/null 2>&1; then
  iptables -C DOCKER-USER -i lxdbr0 -j ACCEPT 2>/dev/null || iptables -I DOCKER-USER -i lxdbr0 -j ACCEPT
  iptables -C DOCKER-USER -o lxdbr0 -j ACCEPT 2>/dev/null || iptables -I DOCKER-USER -o lxdbr0 -j ACCEPT
fi
