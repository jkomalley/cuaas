# Roadmap

GNU coreutils behind an API. FastAPI runs in an LXD container, each request runs in a
throwaway bwrap sandbox over chiselled GNU coreutils from Ubuntu 26.04. No shell.

## M1 Runner

- lima vm with lxd for local dev
- script to build the image (fastapi, sandbox, coreutils)
- pick bwrap or nsjail
- run a command with args and stdin, get stdout, stderr and exit code
- refuse to start if it isn't GNU coreutils
- dev vm set up like ci and the image, unit tests on the mac

## M2 API

- `POST /{cmd}`, same request and response for every command
- allowlist of commands
- utf-8 or base64 for stdin, stdout and stderr
- 422 for a bad request, 200 if it ran, any exit code

## M3 Limits

- timeouts, output cap, memory/cpu/process limits, small /tmp, no network, read-only fs
- tests for the nasty stuff (`yes`, `seq 1 1e18`, `sort --compress-program=sh`, `split`)

## M4 CLI

- `cuaas wc -l < file`

## M5 Files

- send files with the request, name and size limits
- maybe get files back (`split`, `tee`, `sort -o`)

## M6 VPS

- vps with lxd, no network in the container
- lxd security updates: `host/setup.sh` holds the snap forever, fine for dev and ci, not
  for the vps (refresh window, or hold only during builds)
- tls, rate limiting, logs
