#!/usr/bin/env python3
"""Build separate, evidence-backed capability maps for target AI roles."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


TIMEZONE = ZoneInfo("America/New_York")

ROLE_LABELS = {
    "ai_pm": "AI 产品",
    "ai_fullstack": "AI 全栈 / Agent 工程",
    "fde": "FDE / 前线部署工程",
}

CAPABILITIES: dict[str, dict[str, Any]] = {
    "agent_architecture": {
        "label": "Agent 架构与运行时",
        "evidence_groups": [
            {"name": "Agent 基础", "patterns": ["agent", "智能体"]},
            {"name": "编排与工具", "patterns": ["langgraph", "tool use", "工具调用", "mcp", "subagent", "multi-agent", "multi agent", "工作流编排"]},
            {"name": "上下文与记忆", "patterns": ["memory", "记忆", "context engineering", "上下文工程", "rag", "检索"]},
            {"name": "LLM 实现", "patterns": ["llm api", "agent loop", "prompt", "提示", "大模型", "llm"]},
        ],
        "learning_actions": ["实现一个带工具调用、记忆和失败恢复的 Agent", "为 Agent 补充可观察运行轨迹与回归用例"],
    },
    "rag_context_engineering": {
        "label": "RAG 与上下文工程",
        "evidence_groups": [
            {"name": "检索", "patterns": ["rag", "检索", "retrieval", "向量"]},
            {"name": "上下文", "patterns": ["context engineering", "上下文工程", "context window", "上下文"]},
            {"name": "数据摄取", "patterns": ["ingest", "数据摄取", "文本 ingest", "结构化 json", "embedding"]},
        ],
        "learning_actions": ["完成一个带召回评测的 RAG 项目", "记录 chunking、召回和上下文压缩的实验结果"],
    },
    "llm_evaluation": {
        "label": "LLM 评测与实验",
        "evidence_groups": [
            {"name": "评测", "patterns": ["eval", "评测", "准确率", "quality gate", "回归测试"]},
            {"name": "实验", "patterns": ["a/b", "ab test", "实验", "量化", "剪枝", "微调"]},
            {"name": "指标", "patterns": ["指标", "metric", "bias", "偏差", "可解释"]},
        ],
        "learning_actions": ["建立 30-50 条任务级 LLM eval 数据集", "展示一次模型或 Prompt 变更前后的质量、延迟和成本对比"],
    },
    "production_reliability": {
        "label": "生产可靠性、监控与排障",
        "evidence_groups": [
            {"name": "可靠性", "patterns": ["可靠性", "reliability", "容错", "失败恢复", "重试"]},
            {"name": "监控", "patterns": ["监控", "observability", "日志", "trace", "告警"]},
            {"name": "排障", "patterns": ["排障", "debug", "诊断", "故障", "恢复"]},
            {"name": "测试", "patterns": ["测试", "test", "回归", "验收"]},
        ],
        "learning_actions": ["给现有 Agent 增加 tracing、告警和失败重放", "整理一次真实生产故障的定位与修复复盘"],
    },
    "api_system_integration": {
        "label": "API、Webhook 与企业系统集成",
        "evidence_groups": [
            {"name": "API", "patterns": ["api", "接口"]},
            {"name": "事件集成", "patterns": ["webhook", "回调", "事件", "消息队列"]},
            {"name": "企业系统", "patterns": ["erp", "pos", "oms", "wms", "saas", "多租户"]},
            {"name": "数据契约", "patterns": ["json", "数据流", "schema", "标准化", "落库"]},
        ],
        "learning_actions": ["准备一个第三方系统集成的端到端架构案例", "补充幂等、鉴权、重试和数据一致性说明"],
    },
    "fullstack_delivery": {
        "label": "全栈原型与生产交付",
        "evidence_groups": [
            {"name": "前端", "patterns": ["react", "next.js", "nextjs", "前端", "web"]},
            {"name": "后端", "patterns": ["node.js", "nodejs", "backend", "后端", "python", "sqlite"]},
            {"name": "生产交付", "patterns": ["上线", "生产", "部署", "交付", "production"]},
            {"name": "端到端", "patterns": ["端到端", "0 到 1", "0-1", "从 0 到 1", "全栈"]},
        ],
        "learning_actions": ["用限时方式完成一个 AI 功能从 API 到前端的可部署原型", "补充部署、测试和性能证据"],
    },
    "coding_python": {
        "label": "Python 与工程编码",
        "evidence_groups": [
            {"name": "Python", "patterns": ["python", "pytorch", "scikit-learn"]},
            {"name": "工程实现", "patterns": ["开发", "实现", "代码", "工程师", "engineer"]},
            {"name": "测试质量", "patterns": ["测试", "pytest", "回归", "验收"]},
            {"name": "算法与复杂度", "patterns": ["leetcode", "算法", "数据结构", "时间复杂度", "空间复杂度"]},
        ],
        "learning_actions": ["完成 LeetCode 高频基础题并记录可解释解法", "用 Python 实现一个可测试的 Agent 或 RAG 服务"],
    },
    "cloud_devops": {
        "label": "云平台、CI/CD 与容器化",
        "evidence_groups": [
            {"name": "云平台", "patterns": ["aws", "google cloud", "gcp", "azure", "云平台"]},
            {"name": "容器", "patterns": ["docker", "kubernetes", "k8s", "容器"]},
            {"name": "交付流水线", "patterns": ["ci/cd", "cicd", "github actions", "流水线", "自动部署"]},
        ],
        "learning_actions": ["将一个 AI 服务容器化并部署到云环境", "增加 CI 测试、镜像构建和回滚流程"],
    },
    "system_design": {
        "label": "系统与数据架构设计",
        "evidence_groups": [
            {"name": "系统架构", "patterns": ["系统设计", "架构", "多租户", "分布式"]},
            {"name": "数据架构", "patterns": ["数据模型", "数据层", "数据库", "sqlite", "schema"]},
            {"name": "规模与边界", "patterns": ["扩展", "规模", "权限", "rbac", "作用域"]},
        ],
        "learning_actions": ["为一个现有项目画出容量、数据流和故障边界", "准备多租户、权限和一致性取舍说明"],
    },
    "customer_discovery": {
        "label": "客户发现、需求澄清与方案设计",
        "evidence_groups": [
            {"name": "用户研究", "patterns": ["用户研究", "customer discovery", "客户发现", "访谈"]},
            {"name": "需求", "patterns": ["需求拆解", "需求澄清", "prd", "核心场景", "mvp"]},
            {"name": "方案", "patterns": ["方案设计", "流程", "原型", "概念设计"]},
            {"name": "客户交付", "patterns": ["客户", "门店", "教授", "商户", "合作伙伴"]},
        ],
        "learning_actions": ["整理一个从模糊客户问题到可验收方案的案例", "补充 POC 范围、成功指标和需求变更取舍"],
    },
    "customer_communication": {
        "label": "技术沟通、演示与影响力",
        "evidence_groups": [
            {"name": "沟通对象", "patterns": ["客户", "商户", "教授", "跨团队", "合作伙伴"]},
            {"name": "表达", "patterns": ["面向客户演示", "方案演示", "培训", "汇报", "技术沟通", "presented", "workshop"]},
            {"name": "影响", "patterns": ["推动", "协调", "支持", "获得", "使用"]},
        ],
        "learning_actions": ["准备 10 分钟面向非技术客户的方案 Demo", "用 STAR 结构整理一次跨团队推动案例"],
    },
    "project_delivery": {
        "label": "项目推进与端到端交付",
        "evidence_groups": [
            {"name": "所有权", "patterns": ["主导", "独立", "负责", "owner", "创始人"]},
            {"name": "过程", "patterns": ["需求", "设计", "开发", "测试", "迭代"]},
            {"name": "交付", "patterns": ["上线", "交付", "通过验收", "落地"]},
            {"name": "结果", "patterns": ["降低", "提高", "覆盖", "支持", "用户使用"]},
        ],
        "learning_actions": ["把一个项目压缩成目标、约束、行动、结果和复盘", "补齐时间线、风险和验收证据"],
    },
    "product_metrics": {
        "label": "产品指标、A/B 测试与 ROI",
        "evidence_groups": [
            {"name": "指标", "patterns": ["指标", "转化率", "参与度", "留存", "效率"]},
            {"name": "实验", "patterns": ["a/b", "ab test", "实验", "验证"]},
            {"name": "商业结果", "patterns": ["roi", "成本", "收入", "降低约", "提高"]},
            {"name": "数据分析", "patterns": ["数据分析", "用户行为数据", "经营数据"]},
        ],
        "learning_actions": ["为 Agent 功能定义离线质量、线上行为和商业三层指标", "准备一次 A/B 测试或 ROI 归因案例"],
    },
    "security_safety": {
        "label": "安全、权限与合规",
        "evidence_groups": [
            {"name": "权限", "patterns": ["权限", "rbac", "角色", "作用域"]},
            {"name": "安全", "patterns": ["安全", "鉴权", "隐私", "合规"]},
            {"name": "防护", "patterns": ["guardrail", "审计", "脱敏", "风险"]},
        ],
        "learning_actions": ["补充 Agent 权限、数据隔离和审计设计", "准备一次 Prompt Injection 或敏感数据防护方案"],
    },
    "data_sql_pipeline": {
        "label": "SQL、数据管道与数据建模",
        "evidence_groups": [
            {"name": "SQL 或数据库", "patterns": ["sql", "sqlite", "数据库", "落库"]},
            {"name": "数据管道", "patterns": ["数据流", "pipeline", "ingest", "etl", "数据管道"]},
            {"name": "建模", "patterns": ["数据模型", "schema", "结构化 json", "标准化"]},
        ],
        "learning_actions": ["完成一个 SQL 分析与数据建模练习", "说明一条真实数据管道的质量、幂等和回放机制"],
    },
    "product_strategy": {
        "label": "AI 产品策略与路线图",
        "evidence_groups": [
            {"name": "产品方向", "patterns": ["产品路线", "路线图", "product strategy", "产品策略", "0 到 1", "从 0 到 1"]},
            {"name": "AI 产品", "patterns": ["genai 产品", "ai 产品", "ai insight", "智友", "agent 早期用户研究"]},
            {"name": "发现与定义", "patterns": ["用户研究", "市场研究", "核心场景", "mvp", "需求"]},
            {"name": "迭代决策", "patterns": ["a/b", "指标", "数据分析", "迭代", "优先级"]},
        ],
        "learning_actions": ["为一个 AI 产品写一页市场、用户、方案、指标路线图", "准备一次模型能力、用户价值和商业约束的取舍案例"],
    },
}

TOPIC_TO_CAPABILITY = {
    "agent": "agent_architecture",
    "rag": "rag_context_engineering",
    "evals": "llm_evaluation",
    "reliability": "production_reliability",
    "deployment": "production_reliability",
    "backend": "api_system_integration",
    "coding": "coding_python",
    "python": "coding_python",
    "system_design": "system_design",
    "customer_delivery": "customer_discovery",
    "customer_communication": "customer_communication",
    "project_delivery": "project_delivery",
    "product_metrics": "product_metrics",
    "product": "product_strategy",
    "security": "security_safety",
    "fullstack": "fullstack_delivery",
    "cloud": "cloud_devops",
    "sql": "data_sql_pipeline",
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def latest_statuses(rows: list[dict[str, Any]]) -> dict[str, str]:
    result: dict[str, str] = {}
    for row in rows:
        record_id = str(row.get("record_id") or "")
        status = str(row.get("status") or "")
        if record_id and status:
            result[record_id] = status
    return result


def baseline_metadata(scout_root: Path) -> dict[str, Any]:
    path = scout_root / "baseline" / "baseline-progress.json"
    if not path.exists():
        return {"status": "unknown", "current_batch": None, "completed_batches": []}
    try:
        progress = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"status": "unknown", "current_batch": None, "completed_batches": []}
    completed = [key for key, value in (progress.get("batches") or {}).items() if value == "complete"]
    return {
        "status": str(progress.get("status") or "unknown"),
        "current_batch": progress.get("current_batch"),
        "completed_batches": completed,
        "window": progress.get("window"),
        "coverage": progress.get("coverage"),
    }


def accepted_interview_snapshot(scout_root: Path) -> dict[str, Any]:
    """Read a public-safe aggregate of previously accepted interview evidence.

    The public repository intentionally does not republish full interview posts.
    When the raw accepted-question files are unavailable, this snapshot preserves
    only reviewed counts and short question summaries from the prior baseline.
    """
    path = scout_root / "accepted-interview-snapshot.json"
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    roles = payload.get("roles") if isinstance(payload, dict) else None
    return roles if isinstance(roles, dict) else {}


def build_maps(scout_root: Path, top_n: int) -> dict[str, Any]:
    signals = read_jsonl(scout_root / "jd-signals.jsonl")
    questions = read_jsonl(scout_root / "question-bank.jsonl")
    statuses = latest_statuses(read_jsonl(scout_root / "record-status.jsonl"))
    accepted_questions = [
        row for row in questions
        if statuses.get(str(row.get("record_id") or "")) == "accepted"
        and row.get("evidence_type") == "real_interview_report"
    ]
    interview_snapshot = accepted_interview_snapshot(scout_root)
    baseline = baseline_metadata(scout_root)
    maps: dict[str, Any] = {}

    for role, role_label in ROLE_LABELS.items():
        role_signals = [
            row for row in signals
            if row.get("role_family") == role
            and row.get("active_status") != "closed"
            and row.get("source_url")
        ]
        role_jobs = {str(row["source_url"]) for row in role_signals}
        constraints = [row for row in role_signals if row.get("capability_key") == "eligibility_constraint"]
        ability_signals = [row for row in role_signals if row.get("capability_key") != "eligibility_constraint"]
        role_interviews = [row for row in accepted_questions if row.get("role_family") == role]

        aggregates: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "jd_urls": set(),
                "core_urls": set(),
                "companies": set(),
                "signals": [],
                "interview_report_ids": set(),
                "interview_question_ids": set(),
                "interview_questions": [],
            }
        )
        for row in ability_signals:
            key = str(row.get("capability_key") or "")
            if not key:
                continue
            item = aggregates[key]
            item["jd_urls"].add(str(row["source_url"]))
            if row.get("importance") == "core":
                item["core_urls"].add(str(row["source_url"]))
            if row.get("company"):
                item["companies"].add(str(row["company"]))
            item["signals"].append(str(row.get("signal") or ""))
        for row in role_interviews:
            key = TOPIC_TO_CAPABILITY.get(str(row.get("topic") or ""))
            if not key:
                continue
            item = aggregates[key]
            record_id = str(row.get("record_id") or "")
            report_id = str(row.get("report_id") or record_id)
            item["interview_report_ids"].add(report_id)
            item["interview_question_ids"].add(record_id)
            item["interview_questions"].append(str(row.get("question") or ""))

        role_interview_report_total = len({
            str(row.get("report_id") or row.get("record_id") or "") for row in role_interviews
        })
        role_interview_question_total = len({
            str(row.get("record_id") or "") for row in role_interviews
        })
        snapshot_role = interview_snapshot.get(role) if isinstance(interview_snapshot.get(role), dict) else {}
        legacy_snapshot_question_count = int(snapshot_role.get("accepted_record_count") or 0)
        use_snapshot = role_interview_report_total == 0 and bool(snapshot_role)
        if use_snapshot:
            role_interview_question_total = legacy_snapshot_question_count
            for key, snapshot_item in (snapshot_role.get("capabilities") or {}).items():
                if not isinstance(snapshot_item, dict):
                    continue
                item = aggregates[str(key)]
                snapshot_count = int(snapshot_item.get("interview_count") or 0)
                item["interview_question_ids"].update(
                    f"snapshot:{role}:{key}:{index}" for index in range(snapshot_count)
                )
                item["interview_questions"].extend(
                    str(value) for value in (snapshot_item.get("sample_questions") or []) if value
                )
        capabilities: list[dict[str, Any]] = []
        for key, item in aggregates.items():
            jd_count = len(item["jd_urls"])
            interview_report_count = len(item["interview_report_ids"])
            interview_question_count = len(item["interview_question_ids"])
            penetration = jd_count / len(role_jobs) if role_jobs else 0.0
            interview_share = (
                interview_report_count / role_interview_report_total
                if role_interview_report_total else 0.0
            )
            if role_interview_report_total:
                market_score = round(100 * (0.85 * penetration + 0.15 * interview_share))
            else:
                market_score = round(100 * penetration)
            taxonomy = CAPABILITIES.get(key, {
                "label": key,
                "evidence_groups": [{"name": key, "patterns": [key]}],
                "learning_actions": [f"补充 {key} 的项目和面试证据"],
            })
            capabilities.append({
                "capability_key": key,
                "label": taxonomy["label"],
                "market_score": market_score,
                "job_penetration": round(penetration, 4),
                "jd_job_count": jd_count,
                "jd_signal_count": len(item["signals"]),
                "core_job_count": len(item["core_urls"]),
                # Backwards-compatible alias. It now means independent reports,
                # never extracted questions.
                "interview_count": interview_report_count,
                "interview_report_count": interview_report_count,
                "interview_question_count": interview_question_count,
                "companies": sorted(item["companies"]),
                "sample_signals": [value for value in item["signals"] if value][:3],
                "sample_interview_questions": [value for value in item["interview_questions"] if value][:3],
                "resume_evidence_groups": taxonomy["evidence_groups"],
                "learning_actions": taxonomy["learning_actions"],
            })

        capabilities.sort(
            key=lambda row: (
                -row["jd_job_count"],
                -row["core_job_count"],
                -row["interview_report_count"],
                row["label"],
            )
        )
        top = capabilities[:top_n]
        score_total = sum(max(1, row["market_score"]) for row in top) or 1
        for index, row in enumerate(top, start=1):
            row["rank"] = index
            row["priority_weight"] = round(max(1, row["market_score"]) / score_total, 6)

        maps[role] = {
            "role_family": role,
            "role_label": role_label,
            "coverage_status": "complete" if baseline["status"] == "complete" else "provisional",
            "jd_job_count": len(role_jobs),
            "jd_signal_count": len(role_signals),
            # Backwards-compatible alias for consumers on schema v1.
            "real_interview_count": role_interview_report_total,
            "real_interview_report_count": role_interview_report_total,
            "real_interview_question_count": role_interview_question_total,
            "legacy_snapshot_question_count": legacy_snapshot_question_count,
            "interview_evidence_mode": "traceable_rows" if role_interview_report_total else "legacy_snapshot",
            "top_capabilities": top,
            "constraints": {
                "signal_count": len(constraints),
                "items": [
                    {
                        "signal": row.get("signal"),
                        "company": row.get("company"),
                        "source_url": row.get("source_url"),
                    }
                    for row in constraints[:10]
                ],
            },
        }

    return {
        "schema_version": 2,
        "generated_at": datetime.now(TIMEZONE).isoformat(),
        "source_root": "data/evidence",
        "baseline": baseline,
        "roles": maps,
    }


def render_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# 多岗位 AI 能力地图",
        "",
        f"生成时间：{result['generated_at']}",
        f"完整基线：{result['baseline']['status']}；当前批次：{result['baseline']['current_batch']}",
        "",
        "> provisional 表示完整市场基线尚未通过。地点、经验与用工约束单列，不计入能力匹配分。",
    ]
    for role in result["roles"].values():
        lines.extend([
            "",
            f"## {role['role_label']}",
            "",
            f"覆盖：{role['jd_job_count']} 个独立 JD / {role['jd_signal_count']} 条 JD 信号 / "
            f"{role['real_interview_report_count']} 份可追溯真实面经 / "
            f"{role['real_interview_question_count']} 道已验收问题；状态：{role['coverage_status']}",
            "",
            "| Top | 能力 | 市场分 | 独立 JD | JD 信号 | 面经覆盖 | 问题数 |",
            "|---:|---|---:|---:|---:|---:|---:|",
        ])
        for item in role["top_capabilities"]:
            lines.append(
                f"| {item['rank']} | {item['label']} | {item['market_score']} | "
                f"{item['jd_job_count']} | {item['jd_signal_count']} | "
                f"{item['interview_report_count']} | {item['interview_question_count']} |"
            )
        lines.extend(["", f"硬约束信号：{role['constraints']['signal_count']} 条（不计能力分）。"])
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scout-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--top", type=int, default=6)
    args = parser.parse_args()
    if args.top < 3 or args.top > 10:
        raise SystemExit("--top must be between 3 and 10")
    scout_root = args.scout_root.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    result = build_maps(scout_root, args.top)
    json_path = output_dir / "role-capability-map.json"
    md_path = output_dir / "role-capability-map.md"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(result), encoding="utf-8")
    print(json.dumps({"json": str(json_path), "markdown": str(md_path), "roles": list(result["roles"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
