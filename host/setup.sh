#!/bin/bash
# lxd for building and running the cuaas image. same script for the dev vm, the
# ci runner and the vps. run as root, safe to rerun.
# usage: host/setup.sh [STORAGE]
#   STORAGE is a block device or a btrfs mount for the pool, a loop file if left out
set -euo pipefail
# lxc reads yaml from stdin when it isn't a terminal and waits for eof, which
# never comes under just or limactl shell. nothing here needs stdin
exec </dev/null

here=$(cd "$(dirname "$0")" && pwd)
storage=${1:-}

snap wait system seed.loaded
# the lts, same as the vps gets
snap list lxd >/dev/null 2>&1 || snap install lxd --channel=5.21/stable
# no refresh in the middle of a build or a deploy
snap refresh --hold lxd >/dev/null
lxd waitready --timeout=120

# a fixed subnet, not auto: lima's network answers ping for every ip, so lxd
# thinks every subnet is taken
lxc network show lxdbr0 >/dev/null 2>&1 \
  || lxc network create lxdbr0 ipv4.address=10.64.64.1/24 ipv4.nat=true ipv6.address=none

# btrfs, the dir driver copies the whole rootfs per container
if ! lxc storage show default >/dev/null 2>&1; then
  if [[ -n "$storage" ]]; then
    lxc storage create default btrfs source="$storage"
  else
    # lxd's default loop file is 5GiB, full after a couple of images
    lxc storage create default btrfs size=20GiB
  fi
fi

# default profile: what the image build uses, with network
lxc profile device show default | grep -q '^root:' \
  || lxc profile device add default root disk path=/ pool=default
lxc profile device show default | grep -q '^eth0:' \
  || lxc profile device add default eth0 nic network=lxdbr0 name=eth0

# cuaas profile: how the image runs, no network
lxc profile show cuaas >/dev/null 2>&1 || lxc profile create cuaas
lxc profile edit cuaas <"$here/cuaas-profile.yaml"

# goroutine dumps when lxd stalls, see scripts/lxc.sh. localhost only
lxc config set core.debug_address 127.0.0.1:8444

# docker's FORWARD DROP (on the ci runner) cuts lxdbr0 off from the internet
if iptables -L DOCKER-USER -n >/dev/null 2>&1; then
  iptables -C DOCKER-USER -i lxdbr0 -j ACCEPT 2>/dev/null || iptables -I DOCKER-USER -i lxdbr0 -j ACCEPT
  iptables -C DOCKER-USER -o lxdbr0 -j ACCEPT 2>/dev/null || iptables -I DOCKER-USER -o lxdbr0 -j ACCEPT
fi
