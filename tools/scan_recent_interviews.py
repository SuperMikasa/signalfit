#!/usr/bin/env python3
"""Discover recent interview-report leads without promoting them into scoring."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import html
import json
import re
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any


NOWCODER_SEARCH = "https://www.nowcoder.com/search/all?"
RESULT_PATTERN = re.compile(
    r"show-time[^>]*>([^<]+)</div>.*?"
    r'<a href="(/(?:feed/main/detail/[a-f0-9]+|discuss/[0-9]+)[^"]*)"[^>]*>(.*?)</a>.*?'
    r'<div class="placeholder-text"[^>]*>(.*?)</div>',
    re.S,
)
TAG_PATTERN = re.compile(r"<[^>]+>")
EXCLUDED_TITLE_TERMS = (
    "汇总", "全解析", "问答", "八股", "学习路线", "高频题", "题库", "攻略", "投递记录", "笔试",
    "场景题", "保洁岗",
)


def clean_text(value: str) -> str:
    text = TAG_PATTERN.sub("", value)
    text = html.unescape(html.unescape(text)).replace("\xa0", " ")
    return " ".join(text.split())


def parse_display_date(value: str, as_of: date) -> date | None:
    value = clean_text(value)
    if value.startswith("今天"):
        return as_of
    if value.startswith("昨天"):
        return as_of - timedelta(days=1)
    match = re.match(r"(?:(\d{4})-)?(\d{2})-(\d{2})", value)
    if not match:
        return None
    year = int(match.group(1) or as_of.year)
    parsed = date(year, int(match.group(2)), int(match.group(3)))
    if not match.group(1) and parsed > as_of + timedelta(days=1):
        parsed = date(year - 1, parsed.month, parsed.day)
    return parsed


def likely_first_person_report(title: str, snippet: str) -> bool:
    combined = f"{title} {snippet}"
    if not any(term in combined for term in ("面经", "面试", "一面", "二面", "三面")):
        return False
    if title.strip().lower() in {"面经", "agent面经", "ai面经"}:
        return False
    if snippet.count("答：") >= 2:
        return False
    return not any(term in title for term in EXCLUDED_TITLE_TERMS)


def parse_nowcoder_results(body: bytes, role_family: str, as_of: date) -> list[dict[str, Any]]:
    source = body.decode("utf-8", errors="replace")
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for display_time, path, raw_title, raw_snippet in RESULT_PATTERN.findall(source):
        canonical_path = path.split("?", 1)[0]
        source_url = urllib.parse.urljoin("https://www.nowcoder.com", canonical_path)
        if source_url in seen:
            continue
        seen.add(source_url)
        title = clean_text(raw_title)
        snippet = clean_text(raw_snippet)
        published = parse_display_date(display_time, as_of)
        rows.append({
            "role_family": role_family,
            "source_platform": "nowcoder",
            "source_url": source_url,
            "title": title,
            "snippet": snippet,
            "display_time": clean_text(display_time),
            "discovered_published_at": published.isoformat() if published else None,
            "candidate_status": "needs_review" if likely_first_person_report(title, snippet) else "excluded_by_title_heuristic",
        })
    return rows


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def known_urls(evidence_dir: Path) -> set[str]:
    rows = read_jsonl(evidence_dir / "question-bank.jsonl") + read_jsonl(evidence_dir / "interview-source-leads.jsonl")
    return {str(row.get("source_url")) for row in rows if row.get("source_url")}


def fetch(url: str) -> tuple[int, bytes]:
    request = urllib.request.Request(url, headers={"User-Agent": "SignalFit/0.7 public evidence discovery"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return int(response.status), response.read()


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def run(args: argparse.Namespace) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    as_of = date.fromisoformat(args.as_of)
    window_start = as_of - timedelta(days=args.days - 1)
    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    existing = known_urls(args.evidence_dir)
    candidates: list[dict[str, Any]] = []
    source_runs: list[dict[str, Any]] = []
    log = [
        f"SignalFit 面经增量发现：{as_of.isoformat()}，窗口 {window_start.isoformat()} 至 {as_of.isoformat()}",
        "口径：只发现候选链接并保存搜索快照；未经人工验收不进入能力地图。",
        "",
    ]
    raw_day = args.raw_dir / as_of.isoformat() / "interviews"
    raw_day.mkdir(parents=True, exist_ok=True)

    for query in catalog.get("queries", []):
        query_id = str(query["id"])
        provider = str(query["provider"])
        role_family = str(query["role_family"])
        request_url = NOWCODER_SEARCH + urllib.parse.urlencode({"query": query["query"]})
        started_at = datetime.now().astimezone().isoformat()
        error = None
        status = None
        body = b""
        try:
            status, body = fetch(request_url)
            parsed = parse_nowcoder_results(body, role_family, as_of) if provider == "nowcoder_search" else []
        except Exception as exc:  # network errors must stay visible in the run log
            parsed = []
            error = f"{type(exc).__name__}: {exc}"
        snapshot = raw_day / f"{query_id}.html.gz"
        with gzip.open(snapshot, "wb") as handle:
            handle.write(body)
        recent = [row for row in parsed if row["discovered_published_at"] and window_start.isoformat() <= row["discovered_published_at"] <= as_of.isoformat()]
        reviewable = [row for row in recent if row["candidate_status"] == "needs_review"]
        new_rows = []
        for row in reviewable:
            row.update({
                "query_id": query_id,
                "query": query["query"],
                "discovered_at": as_of.isoformat(),
                "is_new_url": row["source_url"] not in existing,
            })
            if row["is_new_url"]:
                new_rows.append(row)
                existing.add(row["source_url"])
        candidates.extend(new_rows)
        source_run = {
            "query_id": query_id,
            "provider": provider,
            "role_family": role_family,
            "query": query["query"],
            "request_url": request_url,
            "http_status": status,
            "started_at": started_at,
            "finished_at": datetime.now().astimezone().isoformat(),
            "raw_results": len(parsed),
            "recent_results": len(recent),
            "reviewable_results": len(reviewable),
            "new_candidate_urls": len(new_rows),
            "raw_snapshot_path": str(snapshot),
            "raw_body_sha256": hashlib.sha256(body).hexdigest(),
            "error": error,
        }
        source_runs.append(source_run)
        log.append(
            f"网站=nowcoder｜查询={query['query']}｜HTTP={status or '-'}｜原始结果={len(parsed)}｜"
            f"14天内={len(recent)}｜待验收={len(reviewable)}｜新链接={len(new_rows)}"
        )
        log.append(f"  请求={request_url}")
        log.append(f"  Raw={snapshot}")
        if error:
            log.append(f"  错误={error}")

    log.extend(["", "需要外部或登录态人工发现的来源："])
    for source in catalog.get("manual_sources", []):
        log.append(f"- 网站={source['platform']}｜状态={source['status']}｜原因={source['reason']}")
    log.extend([
        "",
        f"发现结论：新候选链接 {len(candidates)}｜查询运行 {len(source_runs)}｜自动入库 0",
    ])
    return candidates, source_runs, log


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--as-of", default=date.today().isoformat())
    parser.add_argument("--days", type=int, default=14)
    parser.add_argument("--catalog", type=Path, default=root / "data/evidence/interview-search-catalog.json")
    parser.add_argument("--evidence-dir", type=Path, default=root / "data/evidence")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--raw-dir", type=Path, required=True)
    args = parser.parse_args()
    candidates, source_runs, log = run(args)
    write_jsonl(args.output_dir / "interview-candidates.jsonl", candidates)
    write_jsonl(args.output_dir / "interview-source-runs.jsonl", source_runs)
    output = "\n".join(log) + "\n"
    (args.output_dir / "interview-source-run.log").write_text(output, encoding="utf-8")
    print(output, end="")
    # A single search failure must stay visible without preventing the remaining
    # audit stages from running. Fail the command only when every query failed.
    return 1 if source_runs and all(row["error"] for row in source_runs) else 0


if __name__ == "__main__":
    raise SystemExit(main())
