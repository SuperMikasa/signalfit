#!/usr/bin/env python3
"""Validate accepted interview evidence and print a detailed Chinese audit log."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse


ROLES = {
    "ai_pm": "AI 产品",
    "ai_fullstack": "AI 全栈 / Agent 工程",
    "fde": "FDE / 前线部署工程",
}
REQUIRED = {
    "record_id", "report_id", "role_family", "evidence_type", "topic",
    "question", "company", "role_title", "source_platform", "source_url",
    "published_at", "retrieved_at", "source_class", "confidence",
}


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{number} JSON 无效：{exc}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"{path}:{number} 必须是 JSON object")
        rows.append(row)
    return rows


def audit(evidence_dir: Path) -> tuple[list[str], list[str]]:
    questions = read_jsonl(evidence_dir / "question-bank.jsonl")
    status_rows = read_jsonl(evidence_dir / "record-status.jsonl")
    leads = read_jsonl(evidence_dir / "interview-source-leads.jsonl")
    errors: list[str] = []
    record_ids: set[str] = set()
    statuses: dict[str, str] = {}
    reports: dict[str, dict] = {}

    for row in status_rows:
        record_id = str(row.get("record_id") or "")
        if not record_id:
            errors.append("状态行缺少 record_id")
            continue
        statuses[record_id] = str(row.get("status") or "")

    accepted: list[dict] = []
    for row in questions:
        missing = sorted(REQUIRED - row.keys())
        record_id = str(row.get("record_id") or "")
        report_id = str(row.get("report_id") or "")
        if missing:
            errors.append(f"{record_id or '<unknown>'} 缺少字段：{', '.join(missing)}")
        if record_id in record_ids:
            errors.append(f"重复 record_id：{record_id}")
        record_ids.add(record_id)
        if row.get("role_family") not in ROLES:
            errors.append(f"{record_id} role_family 无效")
        if row.get("evidence_type") != "real_interview_report":
            errors.append(f"{record_id} evidence_type 不是 real_interview_report")
        parsed = urlparse(str(row.get("source_url") or ""))
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            errors.append(f"{record_id} source_url 无效")
        if statuses.get(record_id) == "accepted":
            accepted.append(row)
        previous = reports.get(report_id)
        signature = {
            "role_family": row.get("role_family"),
            "company": row.get("company"),
            "source_url": row.get("source_url"),
        }
        if previous and previous != signature:
            errors.append(f"{report_id} 的岗位、公司或来源不一致")
        reports[report_id] = signature

    missing_status = sorted(record_ids - statuses.keys())
    extra_status = sorted(statuses.keys() - record_ids)
    if missing_status:
        errors.append(f"{len(missing_status)} 道问题没有审核状态")
    if extra_status:
        errors.append(f"{len(extra_status)} 条审核状态找不到对应问题")

    lines = [
        "SignalFit 真实面经证据审计",
        "口径：独立 report 与提取 question 分开计数；只有 accepted + real_interview_report 进入能力地图。",
        "",
    ]
    by_role: dict[str, list[dict]] = defaultdict(list)
    by_source: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for row in accepted:
        by_role[str(row["role_family"])].append(row)
        by_source[(str(row["source_platform"]), str(row["company"]), str(row["source_url"]))].append(row)

    for role, label in ROLES.items():
        rows = by_role[role]
        report_count = len({row["report_id"] for row in rows})
        source_count = len({row["source_url"] for row in rows})
        lines.append(f"岗位：{label}｜独立面经 {report_count}｜已验收问题 {len(rows)}｜来源 URL {source_count}")
    lines.extend(["", "逐来源获取结果："])
    for (platform, company, source_url), rows in sorted(by_source.items()):
        report_count = len({row["report_id"] for row in rows})
        topics = "、".join(sorted({str(row["topic"]) for row in rows}))
        lines.append(
            f"- 网站={platform}｜公司={company}｜获取=独立面经 {report_count} / 问题 {len(rows)}｜主题={topics}"
        )
        lines.append(f"  URL={source_url}")
    lines.extend(["", "未计入真实面经的线索："])
    for lead in leads:
        lines.append(
            f"- 网站={lead.get('source_platform')}｜状态={lead.get('status')}｜原因={lead.get('reason')}"
        )
        lines.append(f"  URL={lead.get('source_url')}")
    lines.extend([
        "",
        f"审计结论：{'通过' if not errors else '失败'}｜独立面经 {len({row['report_id'] for row in accepted})}｜已验收问题 {len(accepted)}｜错误 {len(errors)}",
    ])
    return lines, errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-dir", type=Path, default=Path("data/evidence"))
    parser.add_argument("--log", type=Path)
    args = parser.parse_args()
    lines, errors = audit(args.evidence_dir.resolve())
    output = "\n".join(lines) + "\n"
    print(output, end="")
    if args.log:
        args.log.parent.mkdir(parents=True, exist_ok=True)
        args.log.write_text(output, encoding="utf-8")
    for error in errors:
        print(f"错误：{error}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
