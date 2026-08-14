#!/usr/bin/env python3
"""Render resume-to-role fit data as accessible radar charts."""

from __future__ import annotations

import argparse
import html
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


TIMEZONE = ZoneInfo("America/New_York")


def polygon_points(values: list[float], radius: float, cx: float, cy: float) -> str:
    count = len(values)
    points = []
    for index, value in enumerate(values):
        angle = -math.pi / 2 + 2 * math.pi * index / count
        distance = radius * value / 100
        points.append(f"{cx + math.cos(angle) * distance:.1f},{cy + math.sin(angle) * distance:.1f}")
    return " ".join(points)


def wrap_label(value: str, width: int = 10) -> list[str]:
    """Wrap compact radar labels without splitting them into many tiny lines."""
    value = value.strip()
    if len(value) <= width:
        return [value]
    separators = [index for index, char in enumerate(value) if char.isspace()]
    preferred = [index for index in separators if 6 <= index <= width + 4]
    if preferred:
        split_at = min(preferred, key=lambda index: abs(index - width))
        return [value[:split_at].rstrip(), value[split_at:].lstrip()[:width]]
    return [value[:width], value[width : width * 2]]


def radar_svg(role: dict[str, Any], standalone: bool = False) -> str:
    axes = role["axes"]
    size = 480
    cx = cy = size / 2
    radius = 150
    count = len(axes)
    title_id = f"radar-title-{role.get('role_family', role.get('role_label', 'role'))}"
    parts = []
    if standalone:
        parts.append(
            '<svg xmlns="http://www.w3.org/2000/svg" width="480" height="480" '
            'viewBox="0 0 480 480" role="img">'
        )
        parts.append(
            "<style>text{font-family:-apple-system,BlinkMacSystemFont,'PingFang SC',sans-serif;"
            "fill:#18202a;font-size:12px}.grid{fill:none;stroke:#c8d0da}.axis{stroke:#d7dde5}"
            ".target{fill:none;stroke:#6b7280;stroke-dasharray:6 5}.candidate{fill:#3377ff;fill-opacity:.22;"
            "stroke:#3377ff;stroke-width:3}.score{font-weight:600}</style>"
        )
        parts.append('<rect width="480" height="480" fill="#ffffff"/>')
    else:
        parts.append(f'<svg viewBox="0 0 480 480" role="img" aria-labelledby="{html.escape(title_id)}">')

    parts.append(
        f'<title id="{html.escape(title_id)}">{html.escape(role["role_label"])} 能力匹配雷达图</title>'
    )
    for level in range(20, 101, 20):
        points = polygon_points([level] * count, radius, cx, cy)
        parts.append(f'<polygon class="grid" points="{points}"/>')
        parts.append(f'<text class="ring-label" x="{cx + 4}" y="{cy - radius * level / 100 + 13:.1f}">{level}</text>')

    for index, axis in enumerate(axes):
        angle = -math.pi / 2 + 2 * math.pi * index / count
        end_x = cx + math.cos(angle) * radius
        end_y = cy + math.sin(angle) * radius
        label_x = cx + math.cos(angle) * (radius + 42)
        label_y = cy + math.sin(angle) * (radius + 42)
        anchor = "middle"
        if label_x < cx - 15:
            anchor = "start"
            label_x = 12
        elif label_x > cx + 15:
            anchor = "end"
            label_x = size - 12
        label_lines = wrap_label(str(axis["label"]))
        parts.append(f'<line class="axis" x1="{cx}" y1="{cy}" x2="{end_x:.1f}" y2="{end_y:.1f}"/>')
        parts.append(f'<text class="axis-label" text-anchor="{anchor}" x="{label_x:.1f}" y="{label_y:.1f}">')
        for line_index, label_line in enumerate(label_lines):
            dy = "0" if line_index == 0 else "14"
            parts.append(
                f'<tspan x="{label_x:.1f}" dy="{dy}">{html.escape(label_line)}</tspan>'
            )
        parts.append(
            f'<tspan class="score" x="{label_x:.1f}" dy="16">{axis["candidate_score"]}</tspan></text>'
        )

    target = polygon_points([100] * count, radius, cx, cy)
    candidate = polygon_points([float(axis["candidate_score"]) for axis in axes], radius, cx, cy)
    parts.append(f'<polygon class="target" points="{target}"/>')
    parts.append(f'<polygon class="candidate" points="{candidate}"/>')
    parts.append("</svg>")
    return "".join(parts)


def render_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# 多岗位能力雷达摘要",
        "",
        f"生成时间：{datetime.now(TIMEZONE).isoformat()}",
        f"简历：{result['resume_path']}",
        f"完整基线：{(result.get('baseline') or {}).get('status', 'unknown')}",
    ]
    for role in result["roles"].values():
        lines.extend(["", f"## {role['role_label']}：{role['overall_score']}/100", ""])
        for gap in role["gaps"][:4]:
            actions = "；".join(gap.get("learning_actions") or [])
            lines.append(f"- {gap['label']}：{gap['candidate_score']} 分。{actions}")
    lines.append("")
    return "\n".join(lines)


def render_html(result: dict[str, Any], svg_by_role: dict[str, str]) -> str:
    baseline_status = (result.get("baseline") or {}).get("status", "unknown")
    cards = []
    for role_key, role in result["roles"].items():
        gaps = "".join(
            "<li><strong>{}</strong><span>{} 分</span><p>{}</p></li>".format(
                html.escape(str(gap["label"])),
                gap["candidate_score"],
                html.escape("；".join((gap.get("learning_actions") or [])[:2])),
            )
            for gap in role["gaps"][:4]
        )
        cards.append(
            f'<section class="role-card" data-role="{html.escape(role_key)}">'
            f'<header><div><h2>{html.escape(role["role_label"])}</h2>'
            f'<p>简历证据匹配</p></div><strong class="overall">{role["overall_score"]}<small>/100</small></strong></header>'
            f'{svg_by_role[role_key]}'
            f'<h3>优先补强</h3><ol class="gaps">{gaps or "<li>当前 Top 能力均有强证据。</li>"}</ol>'
            f'<p class="constraint">另有 {(role.get("constraints_to_review") or {}).get("signal_count", 0)} 条硬约束需单独核对。</p>'
            "</section>"
        )
    notice = (
        '<p class="notice">当前完整市场基线尚未完成，排名和分数为 provisional；'
        "会随每日新增 JD 与面经自动更新。</p>"
        if baseline_status != "complete"
        else '<p class="notice complete">完整市场基线已通过。</p>'
    )
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>多岗位能力雷达图</title>
<style>
:root{{--bg:#f5f7fb;--surface:#fff;--text:#172033;--muted:#677287;--border:#dde3ec;--grid:#d7deea;--axis:#e5e9f0;--accent:#386bf6;--accent-fill:rgba(56,107,246,.20);--target:#8a94a6;--warn-bg:#fff6db;--warn:#745300}}
@media(prefers-color-scheme:dark){{:root{{--bg:#111620;--surface:#19212e;--text:#eef3fa;--muted:#a9b4c5;--border:#303b4c;--grid:#354154;--axis:#2b3545;--accent:#79a0ff;--accent-fill:rgba(121,160,255,.22);--target:#9da8b8;--warn-bg:#3a3116;--warn:#ffdc72}}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif}}main{{max-width:1440px;margin:0 auto;padding:32px}}h1{{margin:0 0 8px;font-size:28px}}.subtitle{{color:var(--muted);margin:0 0 16px}}.notice{{padding:12px 14px;background:var(--warn-bg);color:var(--warn);border-radius:10px;margin:0 0 24px}}.grid{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px}}.role-card{{background:var(--surface);border:1px solid var(--border);border-radius:16px;padding:20px}}header{{display:flex;justify-content:space-between;align-items:flex-start}}h2{{margin:0;font-size:20px}}header p{{margin:5px 0;color:var(--muted)}}.overall{{font-size:34px;color:var(--accent)}}.overall small{{font-size:14px;color:var(--muted)}}svg{{width:100%;height:auto;overflow:visible}}svg text{{fill:var(--text);font-size:11px}}.ring-label{{fill:var(--muted)}}.grid{{fill:none;stroke:var(--grid);stroke-width:1}}.axis{{stroke:var(--axis)}}.target{{fill:none;stroke:var(--target);stroke-width:2;stroke-dasharray:6 5}}.candidate{{fill:var(--accent-fill);stroke:var(--accent);stroke-width:3}}.score{{font-weight:600;fill:var(--accent)}}h3{{font-size:15px;margin:4px 0 8px}}.gaps{{margin:0;padding-left:22px}}.gaps li{{padding:7px 0;border-bottom:1px solid var(--border)}}.gaps li:last-child{{border-bottom:0}}.gaps span{{float:right;color:var(--accent)}}.gaps p{{margin:4px 0 0;color:var(--muted);font-size:13px}}.constraint{{font-size:12px;color:var(--muted);margin:12px 0 0}}@media(max-width:1040px){{.grid{{grid-template-columns:1fr}}main{{max-width:720px}}}}@media(max-width:560px){{main{{padding:18px}}.role-card{{padding:14px}}h1{{font-size:23px}}}}
</style>
</head>
<body><main>
<h1>多岗位能力雷达图</h1>
<p class="subtitle">外圈是岗位目标，蓝色区域是当前简历中可验证的能力证据。</p>
{notice}
<div class="grid">{''.join(cards)}</div>
</main></body></html>
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fit", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    fit_path = args.fit.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    result = json.loads(fit_path.read_text(encoding="utf-8"))
    svg_by_role = {key: radar_svg(role) for key, role in result["roles"].items()}
    svg_paths = {}
    for key, role in result["roles"].items():
        path = output_dir / f"role-fit-radar-{key}.svg"
        path.write_text(radar_svg(role, standalone=True), encoding="utf-8")
        svg_paths[key] = str(path)
    html_path = output_dir / "role-fit-radar.html"
    md_path = output_dir / "role-fit-radar.md"
    html_path.write_text(render_html(result, svg_by_role), encoding="utf-8")
    md_path.write_text(render_markdown(result), encoding="utf-8")
    print(json.dumps({"html": str(html_path), "markdown": str(md_path), "svgs": svg_paths}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
