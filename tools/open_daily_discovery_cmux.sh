#!/bin/sh
set -eu

PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
CMUX_BIN=${CMUX_BIN:-/Applications/cmux.app/Contents/Resources/bin/cmux}

if [ ! -x "$CMUX_BIN" ]; then
  echo "SignalFit：未找到 cmux CLI：$CMUX_BIN" >&2
  exit 1
fi

exec "$CMUX_BIN" new-workspace \
  --name "SignalFit JD+面经每日侦查" \
  --description "逐站中文日志、14 天 JD 与面经增量、待验收链接和 Raw 证据快照" \
  --cwd "$PROJECT_DIR" \
  --command "tools/run_daily_discovery.sh" \
  --focus true
