#!/usr/bin/env python3
"""Scan official ATS boards for recent AI Product, AI Engineering and FDE jobs."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from threading import Lock
from time import perf_counter
from typing import Any
from urllib.error import HTTPError, URLError

from source_adapters import HttpClient, get_adapter, resolve_source, write_raw_snapshot


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = ROOT / "data" / "evidence" / "source-catalog.json"
USER_AGENT = "SignalFit/0.7 (+https://github.com/SuperMikasa/signalfit)"

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


class ChineseRunLogger:
    def __init__(self, quiet: bool = False) -> None:
        self.quiet = quiet
        self.lines: list[str] = []
        self._lock = Lock()

    def emit(self, message: str) -> None:
        stamp = datetime.now().astimezone().isoformat(timespec="seconds")
        line = f"[{stamp}] {message}"
        with self._lock:
            self.lines.append(line)
            if not self.quiet:
                print(line, file=sys.stderr, flush=True)

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(self.lines) + "\n", encoding="utf-8")


@dataclass
class SourceScan:
    source_key: str
    source_index: int
    configured_source: dict[str, Any]
    effective_source: dict[str, Any]
    started_at: str
    finished_at: str
    elapsed_ms: int
    jobs: list[dict[str, Any]] = field(default_factory=list)
    request_url: str | None = None
    final_url: str | None = None
    http_status: int | None = None
    outcome: str = "success"
    error: str | None = None
    raw_snapshot_path: str | None = None
    raw_body_sha256: str | None = None
    resolver_snapshot_path: str | None = None
    resolver_body_sha256: str | None = None
    resolution: dict[str, str] | None = None


def _source_key(index: int, source: dict[str, Any]) -> str:
    identity = f"{index}:{source.get('provider')}:{source.get('board')}:{source.get('company')}"
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]


def _display_raw_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path.resolve())


def _failure_outcome(exc: Exception) -> str:
    if isinstance(exc, HTTPError):
        if exc.code == 404:
            return "migration_suspected"
        if exc.code in {401, 403, 429}:
            return "access_limited"
    if isinstance(exc, ValueError) and "auto source" in str(exc):
        return "resolver_required"
    if isinstance(exc, URLError):
        return "environment_unavailable"
    return "failed"


def validate_source_catalog(catalog: Any) -> list[dict[str, Any]]:
    if not isinstance(catalog, dict):
        raise ValueError("source catalog must be a JSON object")
    sources = catalog.get("sources")
    if not isinstance(sources, list):
        raise ValueError("catalog sources must be a list")
    seen: set[tuple[str, str, str]] = set()
    for index, source in enumerate(sources):
        if not isinstance(source, dict):
            raise ValueError(f"source #{index} must be an object")
        provider = str(source.get("provider") or "")
        company = str(source.get("company") or "")
        if not company:
            raise ValueError(f"source #{index} requires company")
        if provider == "auto":
            careers_url = str(source.get("careers_url") or "")
            if not careers_url.startswith("https://"):
                raise ValueError(f"auto source #{index} requires an HTTPS careers_url")
            identity_value = careers_url
        else:
            get_adapter(provider)
            board = str(source.get("board") or "")
            if not board:
                raise ValueError(f"{provider} source #{index} requires board")
            identity_value = board
        identity = (provider, identity_value, company)
        if identity in seen:
            raise ValueError(f"duplicate source #{index}: {provider} / {company} / {identity_value}")
        seen.add(identity)
    return sources


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
        "validation_method": job.get("validation_method") or "official_ats_api+strict_date_window+body_readable",
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


def scan_source(
    source_index: int,
    source: dict[str, Any],
    client: HttpClient,
    raw_dir: Path,
    snapshot_day: date,
    raw_cache: bool,
    logger: ChineseRunLogger,
) -> SourceScan:
    source_key = _source_key(source_index, source)
    configured = dict(source)
    effective = dict(source)
    resolution_payload = None
    resolver_raw_path = None
    resolver_raw_sha = None
    started_at = datetime.now(timezone.utc).isoformat()
    started_clock = perf_counter()
    logger.emit(
        f"开始扫描：{source.get('provider', 'auto')} / {source.get('company', '未知公司')} "
        f"（{source.get('board') or source.get('careers_url') or '未配置入口'}）"
    )
    try:
        if source.get("provider") == "auto":
            effective, resolution, resolver_response = resolve_source(source, client)
            resolution_payload = {
                "provider": resolution.provider,
                "board": resolution.board,
                "evidence_url": resolution.evidence_url,
            }
            logger.emit(
                f"来源识别：{source.get('company', '未知公司')} → "
                f"{resolution.provider} / {resolution.board}"
            )
            if raw_cache:
                resolver_source = dict(source)
                resolver_source["provider"] = "resolver"
                resolver_source["board"] = source.get("careers_url")
                snapshot_path, resolver_raw_sha = write_raw_snapshot(
                    raw_dir, snapshot_day, resolver_source, resolver_response
                )
                resolver_raw_path = _display_raw_path(snapshot_path)
                logger.emit(
                    f"Resolver Raw 快照：{source.get('company')} → {resolver_raw_path}"
                    f"（sha256 {resolver_raw_sha[:12]}…）"
                )
        adapter = get_adapter(str(effective.get("provider") or ""))
        response = adapter.fetch(effective, client)
        raw_path = None
        raw_sha = None
        if raw_cache:
            snapshot_path, raw_sha = write_raw_snapshot(raw_dir, snapshot_day, effective, response)
            raw_path = _display_raw_path(snapshot_path)
        jobs = adapter.normalize(effective, response)
        for job in jobs:
            job["_source_key"] = source_key
        finished_at = datetime.now(timezone.utc).isoformat()
        elapsed_ms = round((perf_counter() - started_clock) * 1000)
        logger.emit(
            f"读取完成：{effective.get('provider')} / {effective.get('company')}，"
            f"HTTP {response.status_code}，获取 active 职位 {len(jobs)} 个，"
            f"入口 {response.request_url}，耗时 {elapsed_ms}ms"
        )
        if raw_path:
            logger.emit(f"Raw 快照：{effective.get('company')} → {raw_path}（sha256 {raw_sha[:12]}…）")
        return SourceScan(
            source_key=source_key,
            source_index=source_index,
            configured_source=configured,
            effective_source=effective,
            started_at=started_at,
            finished_at=finished_at,
            elapsed_ms=elapsed_ms,
            jobs=jobs,
            request_url=response.request_url,
            final_url=response.final_url,
            http_status=response.status_code,
            raw_snapshot_path=raw_path,
            raw_body_sha256=raw_sha,
            resolver_snapshot_path=resolver_raw_path,
            resolver_body_sha256=resolver_raw_sha,
            resolution=resolution_payload,
        )
    except Exception as exc:  # network/provider error is part of the audit report
        finished_at = datetime.now(timezone.utc).isoformat()
        elapsed_ms = round((perf_counter() - started_clock) * 1000)
        error = f"{type(exc).__name__}: {exc}"
        outcome = _failure_outcome(exc)
        request_url = getattr(exc, "url", None)
        http_status = getattr(exc, "code", None)
        logger.emit(
            f"读取失败：{source.get('provider')} / {source.get('company')}，"
            f"状态 {outcome}，HTTP {http_status or '-'}，原因 {error}，"
            f"入口 {request_url or source.get('careers_url') or source.get('board') or '-'}"
        )
        return SourceScan(
            source_key=source_key,
            source_index=source_index,
            configured_source=configured,
            effective_source=effective,
            started_at=started_at,
            finished_at=finished_at,
            elapsed_ms=elapsed_ms,
            outcome=outcome,
            error=error,
            request_url=str(request_url) if request_url else None,
            http_status=int(http_status) if http_status else None,
            resolver_snapshot_path=resolver_raw_path,
            resolver_body_sha256=resolver_raw_sha,
            resolution=resolution_payload,
        )


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows), encoding="utf-8")


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "# 最近 14 天 AI 岗位覆盖报告",
        "",
        f"时间窗：{report['window']['start']} 至 {report['window']['end']}（含首尾）",
        f"来源：{report['sources']['succeeded']} / {report['sources']['attempted']} 个官方招聘来源读取成功",
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
        "## 运行与 Raw 产物",
        "",
        f"- 中文详细日志：`{report['artifacts']['human_log']}`",
        f"- 逐来源机器日志：`{report['artifacts']['source_runs']}`",
        f"- Raw 快照目录：`{report['artifacts']['raw_cache']}`",
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


def source_run_record(scan: SourceScan, counts: Counter[str]) -> dict[str, Any]:
    configured = scan.configured_source
    effective = scan.effective_source
    return {
        "schema_version": 1,
        "source_key": scan.source_key,
        "source_index": scan.source_index,
        "company": configured.get("company"),
        "configured_provider": configured.get("provider"),
        "resolved_provider": effective.get("provider"),
        "board": effective.get("board") or configured.get("board"),
        "careers_url": configured.get("careers_url"),
        "request_url": scan.request_url,
        "final_url": scan.final_url,
        "http_status": scan.http_status,
        "outcome": scan.outcome,
        "started_at": scan.started_at,
        "finished_at": scan.finished_at,
        "elapsed_ms": scan.elapsed_ms,
        "raw_jobs": len(scan.jobs),
        "within_window": counts["within_window"],
        "target_jobs": counts["target_jobs"],
        "accepted": counts["accepted"],
        "needs_review": counts["needs_review"],
        "outside_window": counts["outside_window"],
        "missing_date": counts["missing_date"],
        "not_target_role": counts["not_target_role"],
        "duplicates": counts["duplicates"],
        "insufficient_signals": counts["insufficient_signals"],
        "raw_snapshot_path": scan.raw_snapshot_path,
        "raw_body_sha256": scan.raw_body_sha256,
        "resolver_snapshot_path": scan.resolver_snapshot_path,
        "resolver_body_sha256": scan.resolver_body_sha256,
        "resolution": scan.resolution,
        "error": scan.error,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--as-of", type=date.fromisoformat, default=datetime.now(timezone.utc).date())
    parser.add_argument("--days", type=int, default=14)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data" / "evidence" / "recent-14d")
    parser.add_argument("--raw-dir", type=Path, default=ROOT / ".signalfit-cache" / "raw")
    parser.add_argument("--no-raw-cache", action="store_true", help="do not persist private raw source snapshots")
    parser.add_argument("--quiet", action="store_true", help="write detailed logs to disk without streaming them to stderr")
    parser.add_argument("--promote", type=Path, help="also write accepted signals to this canonical JSONL path")
    parser.add_argument("--merge-existing", action="store_true", help="preserve older canonical URLs when promoting")
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    if args.days < 1 or args.days > 90:
        raise SystemExit("--days must be between 1 and 90")
    if args.workers < 1 or args.workers > 32:
        raise SystemExit("--workers must be between 1 and 32")

    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    try:
        sources = validate_source_catalog(catalog)
    except ValueError as exc:
        raise SystemExit(f"invalid source catalog: {exc}") from exc
    window_start = args.as_of - timedelta(days=args.days - 1)
    output_dir = args.output_dir.resolve()
    raw_dir = args.raw_dir.resolve()
    logger = ChineseRunLogger(quiet=args.quiet)
    client = HttpClient(USER_AGENT)
    logger.emit(
        f"SignalFit v0.7 开始：时间窗 {window_start.isoformat()} 至 {args.as_of.isoformat()}，"
        f"来源 {len(sources)} 个，并发 {args.workers}，Raw 缓存 {'关闭' if args.no_raw_cache else raw_dir}"
    )

    all_jobs: list[dict[str, Any]] = []
    scans: list[SourceScan] = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [
            executor.submit(
                scan_source,
                index,
                source,
                client,
                raw_dir,
                args.as_of,
                not args.no_raw_cache,
                logger,
            )
            for index, source in enumerate(sources)
        ]
        for future in as_completed(futures):
            scan = future.result()
            scans.append(scan)
            all_jobs.extend(scan.jobs)
    scans.sort(key=lambda item: item.source_index)
    succeeded = sum(scan.error is None for scan in scans)
    failures = [
        {
            "provider": scan.configured_source.get("provider"),
            "board": scan.configured_source.get("board") or scan.configured_source.get("careers_url"),
            "company": scan.configured_source.get("company"),
            "outcome": scan.outcome,
            "http_status": scan.http_status,
            "request_url": scan.request_url,
            "error": scan.error,
        }
        for scan in scans if scan.error
    ]

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
    source_counts: dict[str, Counter[str]] = defaultdict(Counter)
    seen_urls: set[str] = set()
    for job in sorted(all_jobs, key=lambda item: (str(item.get("posted_at") or ""), item["company"], item["title"]), reverse=True):
        job_source_key = str(job.get("_source_key") or "unknown")
        per_source = source_counts[job_source_key]
        posted_day = parse_day(job.get("posted_at"))
        if not posted_day:
            counters["missing_date"] += 1
            per_source["missing_date"] += 1
            continue
        if not (window_start <= posted_day <= args.as_of):
            counters["outside_window"] += 1
            per_source["outside_window"] += 1
            continue
        counters["within_window"] += 1
        per_source["within_window"] += 1
        classification = classify_role(job)
        if not classification:
            counters["not_target_role"] += 1
            per_source["not_target_role"] += 1
            continue
        per_source["target_jobs"] += 1
        role, scope_tier = classification
        url = job["source_url"].split("?")[0].rstrip("/")
        if not url or url in seen_urls:
            counters["duplicates"] += 1
            per_source["duplicates"] += 1
            continue
        public = public_job(job, role, scope_tier, posted_day, args.as_of)
        discovered_jobs.append(public)
        if scope_tier == "adjacent_review":
            seen_urls.add(url)
            counters["adjacent_review"] += 1
            per_source["needs_review"] += 1
            continue
        rows = signal_rows(job, role, scope_tier, posted_day, args.as_of)
        if not rows:
            counters["insufficient_signals"] += 1
            per_source["insufficient_signals"] += 1
            continue
        seen_urls.add(url)
        accepted_jobs.append(public)
        accepted_signals.extend(rows)
        per_source["accepted"] += 1
    counters["accepted"] = len(accepted_jobs)

    source_runs = [source_run_record(scan, source_counts[scan.source_key]) for scan in scans]
    for run in source_runs:
        logger.emit(
            f"来源汇总：{run['resolved_provider']} / {run['company']}，原始 {run['raw_jobs']}，"
            f"14 天内 {run['within_window']}，目标 {run['target_jobs']}，"
            f"已验收 {run['accepted']}，待复核 {run['needs_review']}，状态 {run['outcome']}"
        )

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
        "schema_version": 2,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "window": {"start": window_start.isoformat(), "end": args.as_of.isoformat(), "days": args.days},
        "sources": {
            "attempted": len(sources),
            "succeeded": succeeded,
            "failed": len(failures),
            "outcomes": dict(Counter(scan.outcome for scan in scans)),
            "failures": sorted(failures, key=lambda item: (str(item["provider"]), str(item["board"]))),
        },
        "jobs": dict(counters),
        "roles": role_report,
        "artifacts": {
            "human_log": "source-run.log",
            "source_runs": "source-runs.jsonl",
            "raw_cache": _display_raw_path(raw_dir) if not args.no_raw_cache else "disabled",
        },
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(output_dir / "recent-jobs.jsonl", discovered_jobs)
    write_jsonl(output_dir / "jd-signals.jsonl", accepted_signals)
    write_jsonl(output_dir / "source-runs.jsonl", source_runs)
    logger.emit(
        f"扫描完成：成功来源 {succeeded}/{len(sources)}，active 职位 {len(all_jobs)}，"
        f"14 天内 {counters['within_window']}，已验收 {counters['accepted']}，"
        f"待复核 {counters['adjacent_review']}"
    )
    all_sources_failed = bool(sources) and succeeded == 0
    if all_sources_failed:
        logger.emit("运行失败：所有来源均不可读取；保留审计日志，但本轮不得视为有效侦查。")
    logger.write(output_dir / "source-run.log")
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
    return 2 if all_sources_failed else 0


if __name__ == "__main__":
    sys.exit(main())
