#!/bin/sh
set -eu

PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SCAN_DAY=${SIGNALFIT_SCAN_DAY:-$(date +%F)}
WINDOW_DAYS=${SIGNALFIT_WINDOW_DAYS:-14}
RUN_ROOT=${SIGNALFIT_RUN_ROOT:-${PROJECT_DIR}/.signalfit-cache/runs}
RAW_ROOT=${SIGNALFIT_RAW_ROOT:-${PROJECT_DIR}/.signalfit-cache/raw}
RUN_DIR=${RUN_ROOT}/${SCAN_DAY}

mkdir -p "$RUN_DIR"

echo "SignalFit 每日侦查开始：${SCAN_DAY}，最近 ${WINDOW_DAYS} 天"
echo "公开来源目录：${PROJECT_DIR}/data/evidence/source-catalog.json"
echo "本次运行产物：${RUN_DIR}"
echo "Raw 私有快照：${RAW_ROOT}/${SCAN_DAY}"

python3 "${PROJECT_DIR}/tools/scan_recent_jds.py" \
  --as-of "$SCAN_DAY" \
  --days "$WINDOW_DAYS" \
  --catalog "${PROJECT_DIR}/data/evidence/source-catalog.json" \
  --output-dir "$RUN_DIR" \
  --raw-dir "$RAW_ROOT"

echo "SignalFit 每日侦查完成。中文日志：${RUN_DIR}/source-run.log"
echo "逐来源审计：${RUN_DIR}/source-runs.jsonl"
echo "本次结果只进入侦查缓存，未自动改写公开能力地图。"
