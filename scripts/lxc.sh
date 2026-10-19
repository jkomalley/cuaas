# sourced by the image scripts. lxc via sudo (no lxd group needed) with a timeout
# on every call

# lxc_t SECS ARGS...: sudo lxc ARGS with a timeout. on timeout, dumps lxd's
# goroutines from the debug address host/setup.sh turns on
lxc_t() {
  local secs=$1 rc=0
  shift
  timeout "$secs" sudo lxc "$@" || rc=$?
  if [[ $rc == 124 ]]; then
    local dump
    dump=/tmp/lxd-stall-$(date +%s).txt
    curl -s --max-time 10 "http://127.0.0.1:8444/debug/pprof/goroutine?debug=2" >"$dump" || true
    echo "lxc $1 stalled after ${secs}s, lxd's goroutines are in $dump" >&2
  fi
  return "$rc"
}

# launch IMAGE NAME [ARGS...]: stdin from /dev/null or lxc launch waits for yaml
launch() {
  local image=$1 name=$2
  shift 2
  lxc_t 60 launch -q "$image" "$name" "$@" </dev/null
}

# booted NAME: wait for systemd in NAME to finish booting, fail if any unit
# failed. is-system-running errors until dbus is up, hence the retry
booted() {
  local name=$1 state=""
  for _ in $(seq 60); do
    state=$(lxc_t 150 exec "$name" -- systemctl is-system-running --wait 2>/dev/null) && return 0
    case $state in "" | offline) sleep 1 ;; *) break ;; esac
  done
  echo "$name is ${state:-not answering}, failed units:" >&2
  lxc_t 30 exec "$name" -- systemctl --failed --no-legend >&2 || true
  return 1
}
