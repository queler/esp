#!/usr/bin/env bash
set -euo pipefail
# Path as it was invoked (may be relative)
script_ref="${BASH_SOURCE[0]}"

# Absolute, dereferenced path to the script file
script_path="$(readlink -f -- "$script_ref")"

# Directory containing the script
script_dir="$(dirname -- "$script_path")"
cd "$script_dir"
# ---------- config (override via env) ----------
REAL_DEV="${REAL_DEV:-/dev/ttyUSB0}"
SIM_DEV="${SIM_DEV:-/dev/ttyRFC2217}"

SOCAT_LINK="${SOCAT_LINK:-/dev/ttyRFC2217}"
SOCAT_PORT="${SOCAT_PORT:-4000}"
SOCAT_USER="${SOCAT_USER:-amq102}"

# A hook for your already-working wokwi deploy script (optional)
WOKWI_DEPLOY_SCRIPT="${WOKWI_DEPLOY_SCRIPT:-./deploy_wokwi.sh}"

# ---------- helpers ----------
die() { echo "ERROR: $*" >&2; exit 1; }
info(){ echo "==> $*" >&2; }

have() { command -v "$1" >/dev/null 2>&1; }

ready() {
  local dev="$1"
  mpremote connect "$dev" eval "True" &>/dev/null
}

kill_socat_holding_link() {
  # Only kill processes that:
  #   1) have SOCAT_LINK open, and
  #   2) are actually "socat"
  local pids pid comm
  pids="$(sudo lsof -t -- "$SOCAT_LINK" 2>/dev/null || true)"
  [[ -z "$pids" ]] && return 0

  for pid in $pids; do
    comm="$(ps -p "$pid" -o comm= 2>/dev/null || true)"
    if [[ "$comm" == "socat" ]]; then
      info "Killing socat pid $pid holding $SOCAT_LINK"
      sudo kill "$pid" 2>/dev/null || true
    else
      info "Not killing pid $pid ($comm) holding $SOCAT_LINK"
    fi
  done
}

start_socat_bridge() {
  have socat || die "socat not found"
  have sudo  || die "sudo not found"

  kill_socat_holding_link

  if [[ -L "$SOCAT_LINK" || -e "$SOCAT_LINK" ]]; then
    info "Removing stale $SOCAT_LINK"
    sudo rm -f -- "$SOCAT_LINK" || true
  fi

  info "Starting socat bridge: $SOCAT_LINK -> localhost:$SOCAT_PORT (user=$SOCAT_USER)"
  sudo socat \
    "PTY,link=$SOCAT_LINK,raw,echo=0,user=$SOCAT_USER" \
    "TCP:localhost:$SOCAT_PORT" \
    >/tmp/mprw-socat.log 2>&1 &

  disown || true
}

ensure_sim_ready() {
  if ready "$SIM_DEV"; then
    return 0
  fi

  info "Sim not ready on $SIM_DEV; restarting socat bridge..."
  start_socat_bridge

  local i
  for i in {1..25}; do
    sleep 0.2
    if ready "$SIM_DEV"; then
      return 0
    fi
  done

  return 1
}

select_dev_explicit() {
  local target="$1"
  case "$target" in
    real) echo "$REAL_DEV" ;;
    sim)  echo "$SIM_DEV"  ;;
    *)    die "Unknown target '$target' (use: real|sim)" ;;
  esac
}

autodetect_target() {
  # prioritize real
  if ready "$REAL_DEV"; then
    echo "real"
    return 0
  fi

  # then sim without touching anything
  if ready "$SIM_DEV"; then
    echo "sim"
    return 0
  fi

  # try to revive sim (restart socat)
  if ensure_sim_ready; then
    echo "sim"
    return 0
  fi

  return 1
}

list_deploy_files() {
  {
    find "src" -maxdepth 1 -type f -name '*.py' -print
    [[ -f "wifi.json" ]] && echo "wifi.json"
    find "lib" -type f -print
  } | sed 's|^\./||' | LC_ALL=C sort
}

sha_local() {
  sha256sum "$1" | grep -Eo '[0-9a-fA-F]{64}'

}

sha_remote() {
  local dev="$1" rpath="$2"
  # mpremote prints: "<hash>  <filename>"
  mpremote connect "$dev" sha256sum "$rpath" 2>/dev/null | grep -Eo '[0-9a-fA-F]{64}'

}

remote_path_for() {
  local f="$1"
  if [[ "$f" == src/* ]]; then
    # src/foo.py -> :/foo.py (device root)
    echo ":/${f#src/}"
  elif [[ "$f" == lib/* ]]; then
    # lib/a/b.py -> :/lib/a/b.py
    echo ":/$f"
  else
    # wifi.json -> :/wifi.json
    echo ":/$f"
  fi
}

deploy() {
  local dev="$1"
  info "Deploying (changed-only) to $dev"

  local files
  files="$(list_deploy_files)"
  [[ -z "$files" ]] && die "No deploy files found (src/*.py, wifi.json, lib/**)"

  # cache dirs we've mkdir'd so we don't spam the device
  declare -A made_dirs=()

  local f rpath lsha rsha rdir
  while IFS= read -r f; do
    [[ -z "$f" ]] && continue
    [[ -f "$f" ]] || continue

    rpath="$(remote_path_for "$f")"

    lsha="$(sha_local "$f")"
    rsha="$(sha_remote "$dev" "$rpath" || true)"

    if [[ -n "$rsha" && "$rsha" == "$lsha" ]]; then
      info "  skip (same): $f"
      continue
    fi

    # ensure remote directory exists for nested lib paths
    if [[ "$rpath" == :/lib/* ]]; then
      rdir="${rpath%/*}"   # ":/lib/a" etc
      if [[ -z "${made_dirs[$rdir]+x}" ]]; then
        mpremote connect "$dev" fs mkdir "$rdir" 2>/dev/null || true
        made_dirs[$rdir]=1
      fi
    fi

    info "  push: $f -> $rpath"
    mpremote connect "$dev" cp "$f" "$rpath"
  done <<< "$files"
}

usage() {
  cat >&2 <<'EOF'
Usage:
  mprw [--target real|sim] <cmd> [args...]

Target selection:
  - If --target is omitted: autodetect active device (prioritizes real).
  - real  -> /dev/ttyUSB0 (override REAL_DEV)
  - sim   -> /dev/ttyRFC2217 (override SIM_DEV) + will auto-restart socat if needed

Commands:
  status            Probe device readiness (mpremote eval True)
  deploy            Copy *.py and wifi.json (if present) to device
  reset             Soft-reset the device
  repl              Open mpremote repl
  run               Soft-reset (default) then open repl
  wokwi-deploy      Run your existing Wokwi deploy script (WOKWI_DEPLOY_SCRIPT)

Examples:
  ./mprw status                 # autodetect (real preferred)
  ./mprw deploy                  # autodetect then deploy
  ./mprw --target sim deploy      # force sim
EOF
}

# ---------- main ----------
have mpremote || die "mpremote not found (pipx install mpremote or pip install mpremote)"

target=""
if [[ "${1:-}" == "--target" ]]; then
  target="${2:-}"; shift 2
fi

cmd="${1:-}"; shift || true
#[[ -z "${cmd:-}" ]] && { usage; exit 2; }

if [[ -z "$target" ]]; then
  if ! target="$(autodetect_target)"; then
    die "No active target found. Real ($REAL_DEV) not responding; sim ($SIM_DEV) not responding (even after socat restart)."
  fi
  info "Autodetected target: $target"
fi

dev="$(select_dev_explicit "$target")"

case "$cmd" in
  status)
    if ready "$dev"; then
      echo "READY: $target ($dev)"
    else
      echo "NOT READY: $target ($dev)" >&2
      exit 1
    fi
    ;;
  deploy)
    deploy "$dev"
    ;;
  help)
    die usage
    ;;
#  reset)
#    info "Soft reset: $target ($dev)"
#    mpremote connect "$dev" reset
#    ;;
#  repl)
#    exec mpremote connect "$dev" repl
#    ;;
#  run)
#    info "Soft reset then repl: $target ($dev)"
#    mpremote connect "$dev" reset
#    exec mpremote connect "$dev" repl
#    ;;
#  wokwi-deploy)
#    [[ -x "$WOKWI_DEPLOY_SCRIPT" ]] || die "WOKWI_DEPLOY_SCRIPT not executable: $WOKWI_DEPLOY_SCRIPT"
#    exec "$WOKWI_DEPLOY_SCRIPT" "$@"
#    ;;
  *)
    exec mpremote connect "$dev" "$cmd" "$@"
    ;;
esac
