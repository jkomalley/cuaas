# sourced by the image scripts. every lxc call has a timeout, so a stuck lxd
# fails with a message instead of hanging. lxc runs through sudo, so there's no
# lxd group to get stale in an old ssh session

# lxc_t SECS ARGS... runs lxc ARGS, giving up after SECS. a stall saves lxd's
# goroutines, set up by host/setup.sh, so there's something to look at
lxc_t() {
  local secs=$1 rc=0
  shift
  timeout "$secs" sudo lxc "$@" || rc=$?
  if [[ $rc == 124 ]]; then
    local dump
    dump=/tmp/lxd-stall-$(date +%s).txt
    curl -s "http://127.0.0.1:8444/debug/pprof/goroutine?debug=2" >"$dump" || true
    echo "lxc $1 stalled after ${secs}s, lxd's goroutines are in $dump" >&2
  fi
  return "$rc"
}

# launch IMAGE NAME [ARGS...]. lxc launch reads instance config from stdin when
# it isn't a terminal, and under just or limactl shell that's a pipe that never
# closes, so it waited forever. that was the lxd "stall"
launch() {
  local image=$1 name=$2
  shift 2
  lxc_t 60 launch -q "$image" "$name" "$@" </dev/null
}

