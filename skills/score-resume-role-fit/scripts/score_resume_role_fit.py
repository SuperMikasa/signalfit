#!/usr/bin/env python3
"""Score resume evidence against multiple role capability maps."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any
from xml.etree import ElementTree
from zoneinfo import ZoneInfo


TIMEZONE = ZoneInfo("America/New_York")
PROOF_TERMS = (
    "搭建", "上线", "交付", "开发", "实现", "设计", "打通", "集成", "部署", "验证",
    "推动", "主导", "负责", "完成", "获得", "降低", "提高", "支持", "落库", "分析",
    "built", "shipped", "delivered", "implemented", "designed", "deployed", "integrated",
    "launched", "validated", "led", "owned", "improved", "reduced",
)
NON_PROOF_PREFIXES = (
    "技术：", "- 技术：", "候选人补充", "- 重度使用 Agent", "- 对 LLM/Agent 机制", "- 自己做产品",
)


def load_resume_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".md", ".txt"}:
        return path.read_text(encoding="utf-8")
    if suffix == ".pdf":
        try:
            from pypdf import PdfReader

            reader = PdfReader(str(path))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except ImportError:
            with tempfile.TemporaryDirectory() as temp_dir:
                output = Path(temp_dir) / "resume.txt"
                subprocess.run(["pdftotext", str(path), str(output)], check=True)
                return output.read_text(encoding="utf-8", errors="replace")
    if suffix == ".docx":
        with zipfile.ZipFile(path) as archive:
            document = archive.read("word/document.xml")
        root = ElementTree.fromstring(document)
        namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        paragraphs = []
        for paragraph in root.findall(".//w:p", namespace):
            text = "".join(node.text or "" for node in paragraph.findall(".//w:t", namespace))
            if text:
                paragraphs.append(text)
        return "\n".join(paragraphs)
    raise ValueError(f"Unsupported resume format: {suffix}")


def clean_lines(text: str) -> list[str]:
    return [re.sub(r"\s+", " ", line).strip() for line in text.splitlines() if line.strip()]


def pattern_in_line(pattern: str, line: str) -> bool:
    return pattern.casefold() in line.casefold()


def score_capability(capability: dict[str, Any], lines: list[str]) -> dict[str, Any]:
    groups = capability.get("resume_evidence_groups") or []
    matched_groups: list[str] = []
    demonstrated_groups: list[str] = []
    missing_groups: list[str] = []
    evidence: list[dict[str, Any]] = []
    evidence_line_numbers: set[int] = set()

    for group in groups:
        patterns = [str(value) for value in group.get("patterns") or []]
        group_hits: list[dict[str, Any]] = []
        for index, line in enumerate(lines, start=1):
            matched_patterns = [pattern for pattern in patterns if pattern_in_line(pattern, line)]
            if matched_patterns:
                group_hits.append({
                    "line": index,
                    "text": line,
                    "matched_patterns": matched_patterns,
                    "is_proof": (
                        not line.startswith("#")
                        and not line.startswith(NON_PROOF_PREFIXES)
                        and any(term.casefold() in line.casefold() for term in PROOF_TERMS)
                    ),
                })
        if group_hits:
            group_name = str(group.get("name") or "unnamed")
            matched_groups.append(group_name)
            if any(hit["is_proof"] for hit in group_hits):
                demonstrated_groups.append(group_name)
            for hit in group_hits[:2]:
                if hit["line"] not in evidence_line_numbers:
                    evidence.append(hit)
                    evidence_line_numbers.add(hit["line"])
        else:
            missing_groups.append(str(group.get("name") or "unnamed"))

    coverage = len(matched_groups) / len(groups) if groups else 0.0
    demonstrated = len(demonstrated_groups) / len(groups) if groups else 0.0
    proof = bool(demonstrated_groups)
    breadth = len(evidence_line_numbers) >= 2
    score = round(50 * coverage + 40 * demonstrated + (10 if breadth else 0))
    if not demonstrated_groups:
        score = min(score, 49)
    score = min(100, max(0, score))
    status = "strong" if score >= 80 else "partial" if score >= 55 else "gap"
    return {
        "capability_key": capability["capability_key"],
        "label": capability["label"],
        "rank": capability["rank"],
        "market_score": capability["market_score"],
        "market_weight": capability["priority_weight"],
        "candidate_score": score,
        "status": status,
        "matched_groups": matched_groups,
        "demonstrated_groups": demonstrated_groups,
        "missing_groups": missing_groups,
        "proof_line_present": proof,
        "evidence_breadth": len(evidence_line_numbers),
        "evidence": evidence[:4],
        "learning_actions": capability.get("learning_actions") or [],
    }


def score_resume(capability_map: dict[str, Any], resume_path: Path, text: str) -> dict[str, Any]:
    lines = clean_lines(text)
    roles: dict[str, Any] = {}
    for role_key, role in capability_map["roles"].items():
        axes = [score_capability(capability, lines) for capability in role["top_capabilities"]]
        total_weight = sum(float(axis["market_weight"]) for axis in axes) or 1.0
        overall = round(
            sum(axis["candidate_score"] * float(axis["market_weight"]) for axis in axes) / total_weight
        )
        band = "strong" if overall >= 80 else "plausible" if overall >= 60 else "weak"
        strengths = sorted(
            [axis for axis in axes if axis["status"] == "strong"],
            key=lambda axis: (-axis["candidate_score"], axis["rank"]),
        )
        gaps = []
        for axis in axes:
            if axis["status"] == "strong":
                continue
            gap = dict(axis)
            gap["gap_priority"] = round(float(axis["market_weight"]) * (100 - axis["candidate_score"]), 2)
            gaps.append(gap)
        gaps.sort(key=lambda axis: (-axis["gap_priority"], axis["rank"]))
        roles[role_key] = {
            "role_family": role_key,
            "role_label": role["role_label"],
            "coverage_status": role["coverage_status"],
            "overall_score": overall,
            "fit_band": band,
            "axes": axes,
            "top_strengths": strengths[:3],
            "gaps": gaps,
            "constraints_to_review": role.get("constraints") or {},
        }

    return {
        "schema_version": 1,
        "generated_at": datetime.now(TIMEZONE).isoformat(),
        "resume_path": resume_path.name,
        "resume_line_count": len(lines),
        "map_generated_at": capability_map.get("generated_at"),
        "baseline": capability_map.get("baseline"),
        "score_type": "resume_evidence_coverage",
        "roles": roles,
    }


def render_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# 简历 × 多岗位能力匹配",
        "",
        f"生成时间：{result['generated_at']}",
        f"简历：{result['resume_path']}",
        f"评分口径：{result['score_type']}（只衡量简历可见证据，不推断未写经历）",
        f"完整基线：{(result.get('baseline') or {}).get('status', 'unknown')}",
    ]
    for role in result["roles"].values():
        lines.extend([
            "",
            f"## {role['role_label']}：{role['overall_score']}/100（{role['fit_band']}）",
            "",
            "| 能力 | 市场 Top | 简历分 | 状态 | 证据 |",
            "|---|---:|---:|---|---|",
        ])
        for axis in role["axes"]:
            evidence = "；".join(f"L{item['line']} {item['text']}" for item in axis["evidence"][:2]) or "无"
            lines.append(
                f"| {axis['label']} | {axis['rank']} | {axis['candidate_score']} | {axis['status']} | {evidence} |"
            )
        lines.extend(["", "### 优先缺口", ""])
        if not role["gaps"]:
            lines.append("- 当前 Top 能力均有 strong 级简历证据。")
        for gap in role["gaps"][:4]:
            missing = "、".join(gap["missing_groups"]) or "证据深度/广度"
            action = "；".join(gap["learning_actions"][:2])
            lines.append(
                f"- {gap['label']}（{gap['candidate_score']} 分，优先级 {gap['gap_priority']}）："
                f"缺 {missing}。建议：{action}"
            )
        constraint_count = (role.get("constraints_to_review") or {}).get("signal_count", 0)
        lines.extend(["", f"> 另有 {constraint_count} 条地点、经验或用工约束需单独核对，不计入能力总分。"])
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--map", type=Path, required=True)
    parser.add_argument("--resume", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    map_path = args.map.resolve()
    resume_path = args.resume.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    capability_map = json.loads(map_path.read_text(encoding="utf-8"))
    resume_text = load_resume_text(resume_path)
    result = score_resume(capability_map, resume_path, resume_text)
    json_path = output_dir / "resume-role-fit.json"
    md_path = output_dir / "resume-role-fit.md"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(result), encoding="utf-8")
    print(json.dumps({"json": str(json_path), "markdown": str(md_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
