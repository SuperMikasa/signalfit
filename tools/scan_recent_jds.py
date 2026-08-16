#!/usr/bin/env python3
"""Scan official ATS boards for recent AI Product, AI Engineering and FDE jobs."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = ROOT / "data" / "evidence" / "source-catalog.json"
USER_AGENT = "SignalFit/0.6 (+https://github.com/SuperMikasa/signalfit)"

ROLE_LABELS = {
    "ai_pm": "AI 产品",
    "ai_fullstack": "AI 全栈 / Agent 工程",
    "fde": "FDE / 前线部署工程",
}

ROLE_PATTERNS = {
    "fde": re.compile(
        r"\b(forward[ -]deploy(?:ed|ment)?|field ai|applied ai architect|ai solutions? engineer|"
        r"ai solutions? architect|customer ai engineer|deployment strategist|ai accelerator)\b",
        re.I,
    ),
    "ai_pm": re.compile(
        r"\b(product manager|product lead|head of product|director of product|product owner)\b",
        re.I,
    ),
    "ai_fullstack": re.compile(
        r"\b(applied ai|ai engineer|agent(?:ic)? engineer|llm engineer|gen(?:erative)? ai engineer|"
        r"ai product engineer|full[ -]?stack.*ai|software engineer.*(?:ai|agent|llm)|"
        r"founding engineer.*(?:ai|agent|llm))\b",
        re.I,
    ),
}

AI_RELEVANCE = re.compile(
    r"\b(ai|artificial intelligence|llm|large language model|agentic|agents?|genai|generative ai|"
    r"rag|retrieval.augmented|claude|openai|anthropic)\b",
    re.I,
)

EXPLICIT_AI_TITLE = re.compile(
    r"\b(ai|genai|generative ai|agent|agentic|llm|claude|intelligence)\b",
    re.I,
)

EXCLUDED_TITLES = re.compile(
    r"\b(intern|internship|research scientist|research engineer|data scientist|"
    r"machine learning scientist|sales|recruiter|marketing|designer)\b",
    re.I,
)

CAPABILITY_RULES: dict[str, tuple[str, tuple[str, ...]]] = {
    "agent_architecture": (
        "岗位要求设计、构建或管理基于 LLM 的 Agent、工具调用与工作流编排。",
        ("agent", "agentic", "tool use", "function calling", "mcp", "orchestration", "multi-agent"),
    ),
    "rag_context_engineering": (
        "岗位要求处理检索增强生成、向量检索、数据摄取或上下文工程。",
        ("rag", "retrieval", "vector", "embedding", "context engineering", "chunking"),
    ),
    "llm_evaluation": (
        "岗位要求用评测、实验、质量门禁或反馈闭环衡量 AI 系统效果。",
        ("eval", "evaluation", "experiment", "a/b", "benchmark", "quality gate", "hallucination"),
    ),
    "production_reliability": (
        "岗位要求提升生产级 AI 系统的可靠性、可观察性、调试与故障恢复能力。",
        ("production", "reliability", "observability", "monitoring", "debug", "tracing", "incident"),
    ),
    "api_system_integration": (
        "岗位要求通过 API、数据连接器或企业系统集成落地 AI 能力。",
        ("api", "integration", "connector", "webhook", "crm", "erp", "enterprise system"),
    ),
    "fullstack_delivery": (
        "岗位要求跨前后端完成 AI 原型、产品功能或生产应用的端到端交付。",
        ("full stack", "full-stack", "frontend", "backend", "react", "typescript", "end-to-end"),
    ),
    "coding_python": (
        "岗位要求具备 Python 或同等级工程编码能力，并能直接实现 AI 功能。",
        ("python", "pytorch", "software engineering", "write code", "coding", "hands-on development"),
    ),
    "cloud_devops": (
        "岗位要求在云平台、容器或 CI/CD 环境中部署和运营 AI 服务。",
        ("aws", "gcp", "azure", "kubernetes", "docker", "container", "ci/cd"),
    ),
    "system_design": (
        "岗位要求设计可扩展的系统、数据架构或分布式 AI 基础设施。",
        ("system design", "architecture", "distributed", "scalable", "data architecture"),
    ),
    "customer_discovery": (
        "岗位要求理解客户问题、澄清需求，并把业务场景转化为可实施方案。",
        ("customer needs", "customer problem", "discovery", "requirements", "use cases", "stakeholder"),
    ),
    "customer_communication": (
        "岗位要求面向客户和跨职能团队进行技术沟通、演示、培训或影响决策。",
        ("customer-facing", "present", "demo", "workshop", "training", "communicat", "cross-functional"),
    ),
    "project_delivery": (
        "岗位要求从定义、开发到上线负责项目推进与端到端结果。",
        ("end-to-end", "ship", "launch", "deliver", "execution", "ownership", "roadmap"),
    ),
    "product_metrics": (
        "岗位要求通过指标、实验、采用率或 ROI 衡量 AI 产品业务效果。",
        ("metrics", "kpi", "roi", "adoption", "conversion", "business impact", "measure success"),
    ),
    "security_safety": (
        "岗位要求处理 AI 系统的安全、权限、合规、隐私或护栏设计。",
        ("security", "privacy", "compliance", "guardrail", "audit", "governance", "safety"),
    ),
    "data_sql_pipeline": (
        "岗位要求建设 SQL、数据管道、数据模型或面向 AI 的数据基础设施。",
        ("sql", "data pipeline", "etl", "data model", "database", "data engineering"),
    ),
    "product_strategy": (
        "岗位要求定义 AI 产品愿景、策略、路线图与优先级。",
        ("product strategy", "product vision", "roadmap", "priorit", "product direction", "0 to 1"),
    ),
}

ROLE_PRIORITY = {
    "ai_pm": ("product_strategy", "customer_discovery", "project_delivery", "product_metrics", "llm_evaluation", "agent_architecture", "customer_communication"),
    "ai_fullstack": ("agent_architecture", "coding_python", "production_reliability", "fullstack_delivery", "llm_evaluation", "rag_context_engineering", "system_design"),
    "fde": ("customer_discovery", "customer_communication", "api_system_integration", "fullstack_delivery", "project_delivery", "agent_architecture", "production_reliability"),
}


def fetch_json(url: str) -> Any:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urlopen(request, timeout=45) as response:
        return json.load(response)


def strip_html(value: str) -> str:
    value = re.sub(r"<script\b[^>]*>.*?</script>", " ", value or "", flags=re.I | re.S)
    value = re.sub(r"<style\b[^>]*>.*?</style>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def parse_day(value: Any) -> date | None:
    if not value:
        return None
    text = str(value).strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text).date()
    except ValueError:
        try:
            return date.fromisoformat(text[:10])
        except ValueError:
            return None


def provider_url(provider: str, board: str) -> str:
    if provider == "ashby":
        return f"https://api.ashbyhq.com/posting-api/job-board/{quote(board, safe='')}"
    if provider == "greenhouse":
        return f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true"
    if provider == "lever":
        return f"https://api.lever.co/v0/postings/{board}?mode=json"
    raise ValueError(f"unsupported provider: {provider}")


def normalize_jobs(source: dict[str, str], payload: Any) -> list[dict[str, Any]]:
    provider = source["provider"]
    rows = payload.get("jobs", []) if isinstance(payload, dict) else payload if isinstance(payload, list) else []
    jobs: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if provider == "ashby":
            description = row.get("descriptionPlain") or strip_html(str(row.get("descriptionHtml") or ""))
            jobs.append({
                "provider": provider,
                "board": source["board"],
                "company": source["company"],
                "allow_generic_ai_pm": bool(source.get("allow_generic_ai_pm")),
                "provider_job_id": str(row.get("id") or ""),
                "title": str(row.get("title") or ""),
                "source_url": str(row.get("jobUrl") or row.get("applyUrl") or ""),
                "location": str(row.get("location") or row.get("address", {}).get("postalAddress", {}).get("addressLocality") or "Unspecified"),
                "posted_at": row.get("publishedAt"),
                "timestamp_basis": "publishedAt",
                "description": str(description or ""),
            })
        elif provider == "greenhouse":
            location = row.get("location") or {}
            jobs.append({
                "provider": provider,
                "board": source["board"],
                "company": source["company"] if str(row.get("company_name") or "") in {"", "Job Board"} else str(row["company_name"]),
                "allow_generic_ai_pm": bool(source.get("allow_generic_ai_pm")),
                "provider_job_id": str(row.get("id") or ""),
                "title": str(row.get("title") or ""),
                "source_url": str(row.get("absolute_url") or ""),
                "location": str(location.get("name") if isinstance(location, dict) else location or "Unspecified"),
                "posted_at": row.get("first_published"),
                "timestamp_basis": "first_published",
                "description": strip_html(str(row.get("content") or "")),
            })
        else:
            categories = row.get("categories") or {}
            created_at = row.get("createdAt")
            posted_at = None
            if isinstance(created_at, (int, float)):
                posted_at = datetime.fromtimestamp(created_at / 1000, tz=timezone.utc).isoformat()
            jobs.append({
                "provider": provider,
                "board": source["board"],
                "company": source["company"],
                "allow_generic_ai_pm": bool(source.get("allow_generic_ai_pm")),
                "provider_job_id": str(row.get("id") or ""),
                "title": str(row.get("text") or ""),
                "source_url": str(row.get("hostedUrl") or row.get("applyUrl") or ""),
                "location": str(categories.get("location") if isinstance(categories, dict) else "Unspecified"),
                "posted_at": posted_at,
                "timestamp_basis": "createdAt",
                "description": " ".join(str(row.get(key) or "") for key in ("descriptionPlain", "descriptionBodyPlain", "additionalPlain", "openingPlain")),
            })
    return jobs


def classify_role(job: dict[str, Any]) -> tuple[str, str] | None:
    title = job["title"]
    description = job["description"]
    combined = f"{title} {description[:8000]}"
    if EXCLUDED_TITLES.search(title):
        return None
    if ROLE_PATTERNS["fde"].search(title) and not ROLE_PATTERNS["ai_pm"].search(title) and AI_RELEVANCE.search(combined):
        return "fde", "explicit_target"
    if ROLE_PATTERNS["ai_pm"].search(title) and AI_RELEVANCE.search(combined):
        if EXPLICIT_AI_TITLE.search(title):
            return "ai_pm", "explicit_target"
        if job.get("allow_generic_ai_pm") and not re.search(r"\bcommunications?\b", title, re.I):
            return "ai_pm", "verified_ai_native"
        return "ai_pm", "adjacent_review"
    if ROLE_PATTERNS["ai_fullstack"].search(title) and AI_RELEVANCE.search(combined):
        return "ai_fullstack", "explicit_target"
    return None


def capability_scores(role: str, title: str, description: str) -> list[tuple[str, int]]:
    text = f"{title}. {description}".lower()
    priority = {key: len(ROLE_PRIORITY[role]) - index for index, key in enumerate(ROLE_PRIORITY[role])}
    scores: list[tuple[str, int]] = []
    for key, (_, patterns) in CAPABILITY_RULES.items():
        hits = sum(min(3, text.count(pattern.lower())) for pattern in patterns)
        if hits:
            scores.append((key, hits * 10 + priority.get(key, 0)))
    scores.sort(key=lambda item: (-item[1], item[0]))
    return scores


def experience_hint(description: str) -> str | None:
    matches = re.findall(r"\b(\d{1,2})(?:\s*\+)?\s*(?:years?|yrs?)\b", description, flags=re.I)
    values = [int(value) for value in matches if 0 < int(value) < 20]
    return f"{min(values)}+ 年相关经验" if values else None


def source_id(job: dict[str, Any]) -> str:
    identity = f"{job['provider']}:{job['board']}:{job['provider_job_id']}:{job['source_url']}"
    return f"ats-{hashlib.sha256(identity.encode()).hexdigest()[:16]}"


def public_job(job: dict[str, Any], role: str, scope_tier: str, posted_day: date, retrieved_at: date) -> dict[str, Any]:
    description = job["description"]
    return {
        "source_id": source_id(job),
        "source_title": job["title"],
        "company": job["company"],
        "role_family": role,
        "scope_tier": scope_tier,
        "review_status": "needs_review" if scope_tier == "adjacent_review" else "accepted",
        "source_url": job["source_url"],
        "provider": job["provider"],
        "board": job["board"],
        "provider_job_id": job["provider_job_id"],
        "posted_at": posted_day.isoformat(),
        "timestamp_basis": job["timestamp_basis"],
        "retrieved_at": retrieved_at.isoformat(),
        "location": job["location"],
        "description_sha256": hashlib.sha256(description.encode()).hexdigest(),
        "validation_method": "official_ats_api+strict_date_window+body_readable",
    }


def signal_rows(job: dict[str, Any], role: str, scope_tier: str, posted_day: date, retrieved_at: date) -> list[dict[str, Any]]:
    public = public_job(job, role, scope_tier, posted_day, retrieved_at)
    scores = capability_scores(role, job["title"], job["description"])
    selected = scores[:5]
    if len(selected) < 4:
        return []
    rows: list[dict[str, Any]] = []
    for index, (key, _) in enumerate(selected):
        rows.append({
            "source_id": public["source_id"],
            "source_title": public["source_title"],
            "company": public["company"],
            "role_family": role,
            "scope_tier": scope_tier,
            "source_url": public["source_url"],
            "posted_at": public["posted_at"],
            "timestamp_basis": public["timestamp_basis"],
            "retrieved_at": public["retrieved_at"],
            "active_status": "active",
            "evidence_kind": "official_jd",
            "capability_key": key,
            "importance": "core" if index < 2 else "supporting",
            "signal": CAPABILITY_RULES[key][0],
            "validation_method": public["validation_method"],
        })
    constraint_parts = [f"工作地点或模式：{job['location']}"]
    years = experience_hint(job["description"])
    if years:
        constraint_parts.append(f"职位正文出现{years}要求")
    rows.append({
        "source_id": public["source_id"],
        "source_title": public["source_title"],
        "company": public["company"],
        "role_family": role,
        "scope_tier": scope_tier,
        "source_url": public["source_url"],
        "posted_at": public["posted_at"],
        "timestamp_basis": public["timestamp_basis"],
        "retrieved_at": public["retrieved_at"],
        "active_status": "active",
        "evidence_kind": "official_jd",
        "capability_key": "eligibility_constraint",
        "importance": "constraint",
        "signal": "；".join(constraint_parts) + "。",
        "validation_method": public["validation_method"],
    })
    return rows


def scan_source(source: dict[str, str]) -> tuple[dict[str, str], list[dict[str, Any]], str | None]:
    try:
        payload = fetch_json(provider_url(source["provider"], source["board"]))
        return source, normalize_jobs(source, payload), None
    except Exception as exc:  # network/provider error is part of the audit report
        return source, [], f"{type(exc).__name__}: {exc}"


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows), encoding="utf-8")


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "# 最近 14 天 AI 岗位覆盖报告",
        "",
        f"时间窗：{report['window']['start']} 至 {report['window']['end']}（含首尾）",
        f"来源：{report['sources']['succeeded']} / {report['sources']['attempted']} 个官方 ATS 看板读取成功",
        f"扫描：{report['jobs']['raw']} 个 active 职位；时间窗内 {report['jobs']['within_window']} 个；目标岗位 {report['jobs']['accepted']} 个",
        "",
        "| 岗位 | 已验收 JD | 待复核相邻岗 | 原子信号 | 公司数 |",
        "|---|---:|---:|---:|---:|",
    ]
    for role, label in ROLE_LABELS.items():
        item = report["roles"].get(role, {})
        lines.append(f"| {label} | {item.get('jobs', 0)} | {item.get('needs_review', 0)} | {item.get('signals', 0)} | {item.get('companies', 0)} |")
    lines.extend([
        "",
        "## 淘汰漏斗",
        "",
        f"- 超出 14 天：{report['jobs']['outside_window']}",
        f"- 缺失可验证发布日期：{report['jobs']['missing_date']}",
        f"- 非目标岗位或 AI 相关性不足：{report['jobs']['not_target_role']}",
        f"- AI 相邻岗待人工复核：{report['jobs']['adjacent_review']}",
        f"- 正文能力信号不足：{report['jobs']['insufficient_signals']}",
        f"- URL 重复：{report['jobs']['duplicates']}",
        "",
        "## 失败来源",
        "",
    ])
    failures = report["sources"]["failures"]
    if failures:
        lines.extend(f"- {item['provider']} / {item['board']}: {item['error']}" for item in failures)
    else:
        lines.append("- 无")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--as-of", type=date.fromisoformat, default=datetime.now(timezone.utc).date())
    parser.add_argument("--days", type=int, default=14)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data" / "evidence" / "recent-14d")
    parser.add_argument("--promote", type=Path, help="also write accepted signals to this canonical JSONL path")
    parser.add_argument("--merge-existing", action="store_true", help="preserve older canonical URLs when promoting")
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    if args.days < 1 or args.days > 90:
        raise SystemExit("--days must be between 1 and 90")

    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    sources = catalog.get("sources", [])
    window_start = args.as_of - timedelta(days=args.days - 1)
    all_jobs: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    succeeded = 0
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [executor.submit(scan_source, source) for source in sources]
        for future in as_completed(futures):
            source, jobs, error = future.result()
            if error:
                failures.append({**source, "error": error})
            else:
                succeeded += 1
                all_jobs.extend(jobs)

    counters = Counter({
        "raw": len(all_jobs),
        "missing_date": 0,
        "outside_window": 0,
        "within_window": 0,
        "not_target_role": 0,
        "adjacent_review": 0,
        "duplicates": 0,
        "insufficient_signals": 0,
        "accepted": 0,
    })
    discovered_jobs: list[dict[str, Any]] = []
    accepted_jobs: list[dict[str, Any]] = []
    accepted_signals: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    for job in sorted(all_jobs, key=lambda item: (str(item.get("posted_at") or ""), item["company"], item["title"]), reverse=True):
        posted_day = parse_day(job.get("posted_at"))
        if not posted_day:
            counters["missing_date"] += 1
            continue
        if not (window_start <= posted_day <= args.as_of):
            counters["outside_window"] += 1
            continue
        counters["within_window"] += 1
        classification = classify_role(job)
        if not classification:
            counters["not_target_role"] += 1
            continue
        role, scope_tier = classification
        url = job["source_url"].split("?")[0].rstrip("/")
        if not url or url in seen_urls:
            counters["duplicates"] += 1
            continue
        public = public_job(job, role, scope_tier, posted_day, args.as_of)
        discovered_jobs.append(public)
        if scope_tier == "adjacent_review":
            seen_urls.add(url)
            counters["adjacent_review"] += 1
            continue
        rows = signal_rows(job, role, scope_tier, posted_day, args.as_of)
        if not rows:
            counters["insufficient_signals"] += 1
            continue
        seen_urls.add(url)
        accepted_jobs.append(public)
        accepted_signals.extend(rows)
    counters["accepted"] = len(accepted_jobs)

    role_report: dict[str, Any] = {}
    for role in ROLE_LABELS:
        jobs = [job for job in accepted_jobs if job["role_family"] == role]
        needs_review = [
            job for job in discovered_jobs
            if job["role_family"] == role and job["review_status"] == "needs_review"
        ]
        signals = [row for row in accepted_signals if row["role_family"] == role]
        role_report[role] = {
            "jobs": len(jobs),
            "needs_review": len(needs_review),
            "signals": len(signals),
            "companies": len({job["company"] for job in jobs}),
        }

    report = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "window": {"start": window_start.isoformat(), "end": args.as_of.isoformat(), "days": args.days},
        "sources": {
            "attempted": len(sources),
            "succeeded": succeeded,
            "failed": len(failures),
            "failures": sorted(failures, key=lambda item: (item["provider"], item["board"])),
        },
        "jobs": dict(counters),
        "roles": role_report,
    }
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(output_dir / "recent-jobs.jsonl", discovered_jobs)
    write_jsonl(output_dir / "jd-signals.jsonl", accepted_signals)
    (output_dir / "coverage-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output_dir / "coverage-report.md").write_text(render_report(report), encoding="utf-8")
    if args.promote:
        promoted = accepted_signals
        promote_path = args.promote.resolve()
        if args.merge_existing and promote_path.exists():
            existing = [json.loads(line) for line in promote_path.read_text(encoding="utf-8").splitlines() if line.strip()]
            new_urls = {str(row.get("source_url") or "").split("?")[0].rstrip("/") for row in accepted_signals}
            promoted = [
                row for row in existing
                if (
                    (parse_day(row.get("posted_at")) is None or parse_day(row.get("posted_at")) < window_start)
                    and str(row.get("source_url") or "").split("?")[0].rstrip("/") not in new_urls
                )
            ] + accepted_signals
        write_jsonl(promote_path, promoted)
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
