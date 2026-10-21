# Roadmap

GNU coreutils behind an API. FastAPI runs in a rock under docker, each request runs in a
throwaway bwrap sandbox over chiselled GNU coreutils from Ubuntu 26.04. No shell.

## M1 Runner

- lima vm with lxd for local dev
- script to build the image (fastapi, sandbox, coreutils)
- pick bwrap or nsjail
- run a command with args and stdin, get stdout, stderr and exit code
- refuse to start if it isn't GNU coreutils
- dev vm set up like ci and the image, app tests run anywhere

## M2 API

- `POST /{cmd}`, same request and response for every command
- allowlist of commands
- utf-8 or base64 for stdin, stdout and stderr
- 422 for a bad request, 200 if it ran, any exit code

## M3 Rock

- `rockcraft.yaml` replaces `image/`: bare base + slices, no setuid binaries
- parts: coreutils cut into `/jail`, the jail's seccomp filter, the app via uv
- pebble runs uvicorn as a non-root user
- bwrap from the bubblewrap slice (see below)

## M4 Docker

- `compose.yaml` runs the rock: read-only, `--cap-drop ALL`, userns-remap
- seccomp profile: docker's default + `clone unshare mount umount2 pivot_root`
- apparmor: the container profile denies userns and mount, `/usr/bin/bwrap` moves to
  a `cuaas-bwrap` profile that allows them, its children get `unpriv_bwrap`
- bwrap gets `--unshare-user` and `--seccomp` (no namespaces, mounts, keyrings, bpf,
  io_uring, ptrace or non-unix sockets in the jail)
- refuse to start unless `apparmor_restrict_unprivileged_userns` and
  `apparmor_restrict_unprivileged_unconfined` are 1
- deployed tests run against compose instead of lxd

## M5 Ansible

- one playbook for the dev vm, ci and the vps, replaces `host/`, `lima/setup.sh` and most
  of `scripts/`. justfile stays the entry point
- docker.io from apt, daemon.json, subuid range big enough for the rock's user
- apparmor and seccomp profiles, sysctls
- lxd + rockcraft only where rocks get built
- dev vm: move lima's containerd and runc aside, docker silently uses them

## M6 Limits

- timeout, output cap, stdin cap
- max concurrent runs, 503 when full
- sized `/tmp`, container memory/cpu/pids limits
- tests for the nasty stuff (`yes`, `seq 1 1e18`, `sort --compress-program=sh`, `split`)

## M7 CLI

- `cuaas wc -l < file`, typer + httpx
- readable errors on stderr, coreutils-style exit codes. the api keeps fastapi's 422 shape,
  the cli turns it into `unknown field "stdn"` etc
- snap

## M8 VPS

- ubuntu 26.04 vps set up by the playbook
- caddy for tls, logs
- unattended-upgrades on the host, rebuild the rock for coreutils and bubblewrap updates

## M9 Files

- send files with the request, name and size limits
- maybe get files back (`split`, `tee`, `sort -o`)

## Bubblewrap slice

no bubblewrap slice in chisel-releases yet, for any release

- slice + spread test on a fork, the rock cuts from the fork pinned to a commit
- PR to canonical/chisel-releases for 26.04, forward ported to 26.10. needs the CLA
- once merged the rock uses the official release
