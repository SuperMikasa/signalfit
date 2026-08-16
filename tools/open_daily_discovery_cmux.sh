#!/bin/sh
set -eu

PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
CMUX_BIN=${CMUX_BIN:-/Applications/cmux.app/Contents/Resources/bin/cmux}

if [ ! -x "$CMUX_BIN" ]; then
  echo "SignalFit：未找到 cmux CLI：$CMUX_BIN" >&2
  exit 1
fi

exec "$CMUX_BIN" new-workspace \
  --name "SignalFit 每日岗位侦查" \
  --description "逐站中文日志、14 天 AI 岗位发现与 Raw 证据快照" \
  --cwd "$PROJECT_DIR" \
  --command "tools/run_daily_discovery.sh" \
  --focus true
