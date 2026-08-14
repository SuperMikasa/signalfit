#!/usr/bin/env python3
"""Local-first command line entry point for SignalFit."""

from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import subprocess
import sys
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MAP = ROOT / "data" / "baseline" / "role-capability-map.json"
PRIVATE_ROOT = ROOT / ".signalfit"
SCORE_SCRIPT = ROOT / "skills" / "score-resume-role-fit" / "scripts" / "score_resume_role_fit.py"
RENDER_SCRIPT = ROOT / "skills" / "render-role-skill-radar" / "scripts" / "render_role_skill_radar.py"
SUPPORTED_RESUME_SUFFIXES = {".md", ".txt", ".pdf", ".docx"}
TIMEZONE = ZoneInfo("America/New_York")


def run_checked(command: list[str]) -> None:
    subprocess.run(command, cwd=ROOT, check=True)


def latest_run_dir() -> Path | None:
    pointer = PRIVATE_ROOT / "latest.json"
    if not pointer.exists():
        return None
    try:
        value = json.loads(pointer.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    run_dir = Path(str(value.get("run_dir") or ""))
    return run_dir if run_dir.is_dir() else None


def doctor(_: argparse.Namespace) -> int:
    checks = {
        "python": sys.version.split()[0],
        "python_supported": sys.version_info >= (3, 10),
        "baseline_map": DEFAULT_MAP.is_file(),
        "score_script": SCORE_SCRIPT.is_file(),
        "render_script": RENDER_SCRIPT.is_file(),
        "pdf_reader": bool(importlib.util.find_spec("pypdf") or shutil.which("pdftotext")),
    }
    print(json.dumps(checks, ensure_ascii=False, indent=2))
    required = checks["python_supported"] and checks["baseline_map"] and checks["score_script"] and checks["render_script"]
    if not checks["pdf_reader"]:
        print("提示：分析 PDF 前运行 `python3 -m pip install -r requirements.txt`，MD/TXT/DOCX 不受影响。")
    return 0 if required else 1


def analyze(args: argparse.Namespace) -> int:
    resume = Path(args.resume).expanduser().resolve()
    capability_map = Path(args.map).expanduser().resolve()
    if not resume.is_file():
        raise SystemExit(f"找不到简历：{resume}")
    if resume.suffix.lower() not in SUPPORTED_RESUME_SUFFIXES:
        supported = ", ".join(sorted(SUPPORTED_RESUME_SUFFIXES))
        raise SystemExit(f"不支持 {resume.suffix or '无扩展名'}；支持：{supported}")
    if not capability_map.is_file():
        raise SystemExit(f"找不到岗位能力地图：{capability_map}")

    timestamp = datetime.now(TIMEZONE).strftime("%Y%m%d-%H%M%S")
    output_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else PRIVATE_ROOT / "runs" / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)

    run_checked([
        sys.executable,
        str(SCORE_SCRIPT),
        "--map",
        str(capability_map),
        "--resume",
        str(resume),
        "--output-dir",
        str(output_dir),
    ])
    run_checked([
        sys.executable,
        str(RENDER_SCRIPT),
        "--fit",
        str(output_dir / "resume-role-fit.json"),
        "--output-dir",
        str(output_dir),
    ])

    PRIVATE_ROOT.mkdir(parents=True, exist_ok=True)
    manifest = {
        "run_dir": str(output_dir),
        "resume_label": resume.name,
        "generated_at": datetime.now(TIMEZONE).isoformat(),
    }
    (PRIVATE_ROOT / "latest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": "complete",
        "privacy": "local_only",
        "resume": resume.name,
        "json": str(output_dir / "resume-role-fit.json"),
        "markdown": str(output_dir / "resume-role-fit.md"),
        "html": str(output_dir / "role-fit-radar.html"),
    }, ensure_ascii=False, indent=2))
    return 0


def serve(args: argparse.Namespace) -> int:
    directory = Path(args.directory).expanduser().resolve() if args.directory else latest_run_dir()
    if not directory or not directory.is_dir():
        raise SystemExit("没有可展示的分析结果。先运行 `./signalfit analyze <resume>`。")

    class OutputHandler(SimpleHTTPRequestHandler):
        def __init__(self, *handler_args, **handler_kwargs):
            super().__init__(*handler_args, directory=str(directory), **handler_kwargs)

        def log_message(self, message: str, *message_args: object) -> None:
            print(f"[signalfit] {message % message_args}")

    server = ThreadingHTTPServer((args.host, args.port), OutputHandler)
    print(f"SignalFit 本地结果：http://{args.host}:{args.port}/role-fit-radar.html")
    print("简历和结果仅从本机目录提供。按 Ctrl+C 停止。")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


def example(args: argparse.Namespace) -> int:
    args.resume = str(ROOT / "examples" / "resume.sample.md")
    return analyze(args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="signalfit", description="Local-first AI role-fit radar")
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor_parser = subparsers.add_parser("doctor", help="检查本地运行环境")
    doctor_parser.set_defaults(func=doctor)

    analyze_parser = subparsers.add_parser("analyze", help="分析本地简历并生成能力雷达")
    analyze_parser.add_argument("resume", help="MD、TXT、PDF 或 DOCX 简历路径")
    analyze_parser.add_argument("--map", default=str(DEFAULT_MAP), help="岗位能力地图 JSON")
    analyze_parser.add_argument("--output-dir", help="输出目录；默认写入被 Git 忽略的 .signalfit/")
    analyze_parser.set_defaults(func=analyze)

    example_parser = subparsers.add_parser("example", help="用匿名示例简历运行完整流程")
    example_parser.add_argument("--map", default=str(DEFAULT_MAP), help="岗位能力地图 JSON")
    example_parser.add_argument("--output-dir", help="输出目录；默认写入被 Git 忽略的 .signalfit/")
    example_parser.set_defaults(func=example)

    serve_parser = subparsers.add_parser("serve", help="仅在本机展示最近一次雷达结果")
    serve_parser.add_argument("--directory", help="包含 role-fit-radar.html 的目录")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8788)
    serve_parser.set_defaults(func=serve)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
