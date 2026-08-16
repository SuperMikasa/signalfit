"use client";

import { ChangeEvent, useMemo, useRef, useState } from "react";
import baselineMap from "@/data/baseline/role-capability-map.json";
import exampleFit from "@/public/example-fit.json";
import { RadarChart } from "./radar-chart";

type Axis = {
  rank: number;
  label: string;
  candidate_score: number;
  market_score: number;
  gap_priority: number;
  learning_actions: string[];
};

type Gap = {
  label: string;
  candidate_score: number;
  gap_priority: number;
  learning_actions: string[];
};

type Role = {
  role_label: string;
  overall_score: number;
  axes: Axis[];
  gaps: Gap[];
  constraints_to_review: { signal_count: number };
};

type FitData = {
  schema_version: string;
  generated_at: string;
  baseline: { status: string; jd_signal_count: number; interview_count: number };
  candidate_label: string;
  roles: Record<string, Role>;
};

const roleOrder = ["ai_pm", "ai_fullstack", "fde"];
const marketRoles = baselineMap.roles as Record<string, {
  jd_job_count: number;
  jd_signal_count: number;
  real_interview_count: number;
}>;
const marketTotals = Object.values(marketRoles).reduce(
  (total, role) => ({
    jobs: total.jobs + role.jd_job_count,
    requirements: total.requirements + role.jd_signal_count,
    interviews: total.interviews + role.real_interview_count,
  }),
  { jobs: 0, requirements: 0, interviews: 0 },
);

const installCommand = "git clone https://github.com/SuperMikasa/signalfit.git && cd signalfit && ./signalfit doctor";
const agentPrompt = "请在当前目录使用 Coding Agent 一键启动 SignalFit：如果尚未存在 signalfit，先运行 git clone https://github.com/SuperMikasa/signalfit.git；进入 signalfit 后先运行 ./signalfit update 获取最新公开 AI 岗位基线，再读取 AGENTS.md，并分析我的本地简历：/absolute/path/to/resume.pdf。不要上传、复制或提交简历与生成结果。完成后总结我对 AI 产品、AI 全栈 / Agent 工程和 FDE 三个岗位的匹配度、最强证据、优先缺口，并给出本地雷达报告路径。";

function isFitData(value: unknown): value is FitData {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Partial<FitData>;
  return Boolean(candidate.roles && Object.keys(candidate.roles).length);
}

function scoreTone(score: number) {
  if (score >= 80) return "strong";
  if (score >= 55) return "partial";
  return "gap";
}

export default function Home() {
  const [fitData, setFitData] = useState<FitData>(exampleFit as FitData);
  const [selectedRole, setSelectedRole] = useState("ai_fullstack");
  const [importMessage, setImportMessage] = useState("正在查看匿名示例数据");
  const [copyState, setCopyState] = useState<"prompt" | "error" | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);

  const availableRoles = useMemo(
    () => roleOrder.filter((key) => fitData.roles[key]),
    [fitData],
  );
  const role = fitData.roles[selectedRole] ?? fitData.roles[availableRoles[0]];

  async function importFit(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      const nextData = JSON.parse(await file.text());
      if (!isFitData(nextData)) throw new Error("缺少 roles 字段");
      setFitData(nextData);
      const firstRole = roleOrder.find((key) => nextData.roles[key]) ?? Object.keys(nextData.roles)[0];
      setSelectedRole(firstRole);
      setImportMessage(`已在本地载入 ${file.name}，文件未上传`);
    } catch (error) {
      setImportMessage(`无法读取：${error instanceof Error ? error.message : "JSON 格式不正确"}`);
    } finally {
      event.target.value = "";
    }
  }

  async function copyText(value: string) {
    try {
      await navigator.clipboard.writeText(value);
      setCopyState("prompt");
      window.setTimeout(() => setCopyState(null), 2200);
    } catch {
      setCopyState("error");
    }
  }

  return (
    <main>
      <nav className="topbar" aria-label="主导航">
        <a className="brand" href="#top" aria-label="SignalFit 首页">
          <span className="brand-mark" aria-hidden="true">SF</span>
          <span>SignalFit</span>
        </a>
        <div className="nav-links">
          <a href="#map">能力地图</a>
          <a href="#method">方法</a>
          <a href="#start">Agent 启动</a>
          <a href="#loop">持续更新</a>
          <a href="#open-source">开源</a>
        </div>
        <a className="github-link" href="https://github.com/SuperMikasa/signalfit" target="_blank" rel="noreferrer">GitHub 源码 <span aria-hidden="true">↗</span></a>
      </nav>

      <section className="hero" id="top">
        <div className="hero-copy">
          <p className="eyebrow"><span>AI ROLE INTELLIGENCE</span><span aria-hidden="true">/</span><span>v0.6</span></p>
          <h1>只看 AI 岗位。<br /><em>沿着证据找差距。</em></h1>
          <p className="hero-intro">
            SignalFit 只做 AI 相关岗位。目前聚焦 AI 产品、AI 全栈 / Agent 工程和 FDE，把公开 JD、已核验面经与简历证据压缩成可解释的匹配度和补强路径。
          </p>
          <p className="market-proof">当前累计 <strong>{marketTotals.requirements} 条 AI 岗位要求</strong>，来自 {marketTotals.jobs} 份独立 JD，并纳入 {marketTotals.interviews} 条已验收真实面经。最近 14 天已扫描 105 个可读官方 ATS 看板与 10299 个 active 职位。</p>
          <div className="role-scope" aria-label="当前覆盖的 AI 岗位">
            <span>AI 产品</span><span>AI 全栈 / Agent 工程</span><span>FDE</span>
          </div>
          <div className="hero-actions">
            <button className="primary-action" onClick={() => document.querySelector("#start")?.scrollIntoView({ behavior: "smooth" })}>
              使用 Coding Agent 一键启动 <span aria-hidden="true">↓</span>
            </button>
            <button className="secondary-action" onClick={() => fileInput.current?.click()}>
              导入评分 JSON
            </button>
            <input ref={fileInput} type="file" accept="application/json,.json" onChange={importFit} hidden />
          </div>
          <p className="privacy-note"><span aria-hidden="true">●</span> {importMessage}</p>
        </div>

        <aside className="signal-board" aria-label="证据流水线概览">
          <div className="board-header"><span>证据流水线</span><span>持续更新</span></div>
          <div className="signal-flow">
            <div><b>01</b><span>独立 JD</span><strong>{marketTotals.jobs}</strong><small>公开有效岗位</small></div>
            <i aria-hidden="true">→</i>
            <div><b>02</b><span>岗位要求</span><strong>{marketTotals.requirements}</strong><small>原子能力信号</small></div>
            <i aria-hidden="true">→</i>
            <div><b>03</b><span>真实面经</span><strong>{marketTotals.interviews}</strong><small>已验收记录</small></div>
          </div>
          <div className="board-foot">
            <span className="status-dot" />
            <p><b>{baselineMap.baseline.status === "complete" ? "完整基线" : "provisional / 临时基线"}</b><br />排名会随新增证据重算</p>
            <time>{new Date(baselineMap.generated_at).toLocaleDateString("zh-CN")}</time>
          </div>
        </aside>
      </section>

      <section className="workspace" id="map">
        <header className="section-heading">
          <div><p className="section-kicker">AI ROLE MAP / 岗位坐标</p><h2>三个 AI 方向，一套证据口径</h2></div>
          <p>蓝色虚线代表岗位市场信号，绿色实线代表简历证据覆盖。硬约束单列，不混入能力分。</p>
        </header>

        <div className="role-switcher" role="tablist" aria-label="选择岗位">
          {availableRoles.map((key) => (
            <button
              key={key}
              role="tab"
              aria-selected={selectedRole === key}
              onClick={() => setSelectedRole(key)}
            >
              <div>
                <span>{fitData.roles[key].role_label}</span>
                <small>{marketRoles[key].jd_job_count} JD · {marketRoles[key].jd_signal_count} 条要求 · {marketRoles[key].real_interview_count} 面经</small>
              </div>
              <strong>{fitData.roles[key].overall_score}</strong>
            </button>
          ))}
        </div>

        <div className="instrument-grid">
          <article className="radar-panel">
            <div className="panel-heading">
              <div><p>简历证据覆盖</p><h3>{role.role_label}</h3></div>
              <div className={`overall-score ${scoreTone(role.overall_score)}`}><strong>{role.overall_score}</strong><span>/100</span></div>
            </div>
            <RadarChart axes={role.axes} label={role.role_label} />
            <div className="radar-key" aria-label="雷达图数据图例">
              <span><i className="market-key" />岗位市场信号</span>
              <span><i className="evidence-key" />简历证据覆盖</span>
            </div>
          </article>

          <article className="gap-panel">
            <div className="panel-heading"><div><p>优先补强</p><h3>按市场权重 × 证据缺口排序</h3></div><span className="gap-count">{role.gaps.length} 项</span></div>
            <ol className="gap-list">
              {role.gaps.length ? role.gaps.map((gap, index) => (
                <li key={gap.label}>
                  <div className="gap-rank">{String(index + 1).padStart(2, "0")}</div>
                  <div className="gap-copy"><h4>{gap.label}</h4><p>{gap.learning_actions[0]}</p></div>
                  <div className={`gap-score ${scoreTone(gap.candidate_score)}`}><strong>{gap.candidate_score}</strong><span>证据分</span></div>
                </li>
              )) : <li className="empty-state">当前 Top 能力均已有强证据。继续补充可量化结果。</li>}
            </ol>
            <div className="constraint-strip"><span>不计分的硬约束</span><strong>{role.constraints_to_review.signal_count}</strong><p>地点、工时、签证与毕业时间需申请前单独核对</p></div>
          </article>
        </div>

        <div className="capability-ledger" aria-label={`${role.role_label} Top 能力表`}>
          <div className="ledger-head"><span>排名 / 能力</span><span>市场信号</span><span>简历证据</span><span>缺口优先级</span></div>
          {role.axes.map((axis) => (
            <div className="ledger-row" key={axis.label}>
              <div><b>{String(axis.rank).padStart(2, "0")}</b><strong>{axis.label}</strong></div>
              <div className="meter" data-label="市场信号"><i style={{ "--value": `${axis.market_score}%` } as React.CSSProperties} /><span>{axis.market_score}</span></div>
              <div className="meter evidence" data-label="简历证据"><i style={{ "--value": `${axis.candidate_score}%` } as React.CSSProperties} /><span>{axis.candidate_score}</span></div>
              <div className="priority-cell" data-label="缺口优先级"><span className={`priority ${axis.gap_priority >= 8 ? "high" : axis.gap_priority >= 4 ? "medium" : "low"}`}>{axis.gap_priority.toFixed(1)}</span></div>
            </div>
          ))}
        </div>
      </section>

      <section className="method-section" id="method">
        <header className="section-heading"><div><p className="section-kicker">METHOD / 方法边界</p><h2>透明，比一个神秘总分更重要</h2></div></header>
        <div className="method-grid">
          <article><span>DATA</span><h3>两条 AI 岗位证据线，绝不混算</h3><p>官方 JD 回答 AI 团队在招什么；候选人面经回答实际怎么考。只有读取正文且通过验收的记录才进入统计。</p></article>
          <article><span>SCORE</span><h3>只评简历能证明的内容</h3><p>能力分来自概念覆盖、项目证明和证据广度。技能列表不能冒充项目经历，没有证据就显示为缺口。</p></article>
          <article><span>BOUNDARY</span><h3>硬约束独立核对</h3><p>地点、工时、签证、学历和毕业时间会影响可申请性，但不代表能力强弱，因此从雷达图和总分中排除。</p></article>
        </div>
      </section>

      <section className="agent-launch-section" id="start">
        <div className="launch-intro">
          <p className="section-kicker">AGENT QUICKSTART / 开箱即用</p>
          <h2>打开 Coding Agent。<br /><em>一条指令直接启动。</em></h2>
          <p>OpenCode、Claude Code、Codex 都可以。复制一条启动指令，Agent 会自行克隆仓库、读取 <code>AGENTS.md</code>，并在本机完成评分、证据提取、缺口排序和雷达报告。</p>
          <div className="agent-chips" aria-label="兼容的 Coding Agent">
            <span>OpenCode</span><span>Claude Code</span><span>Codex</span><span>其他 Coding Agent</span><strong>均可使用</strong>
          </div>
          <div className="local-route" aria-label="本地数据流">
            <div><b>INPUT</b><strong>你的简历路径</strong></div>
            <span aria-hidden="true">→</span>
            <div><b>LOCAL</b><strong>.signalfit/</strong></div>
            <span aria-hidden="true">→</span>
            <div><b>OUTPUT</b><strong>雷达报告</strong></div>
          </div>
        </div>

        <div className="launch-console" aria-label="Coding Agent 启动指令">
          <div className="console-bar">
            <div><i /><i /><i /></div>
            <span>SIGNALFIT / LOCAL SESSION</span>
            <strong>NO UPLOAD</strong>
          </div>

          <div className="console-step prompt-step">
            <div className="step-label"><b>01</b><span>复制并粘贴给 OpenCode / Claude Code / Codex</span></div>
            <div className="copy-panel prompt-panel">
              <p>{agentPrompt}</p>
              <button type="button" onClick={() => copyText(agentPrompt)}>
                {copyState === "prompt" ? "已复制，可以启动 ✓" : "复制一键启动指令"}
              </button>
            </div>
            <small>粘贴前，把 <code>/absolute/path/to/resume.pdf</code> 换成你电脑上的真实简历路径。</small>
          </div>

          <div className="manual-fallback">
            <span>MANUAL FALLBACK / 手动备用</span>
            <code>{installCommand}</code>
          </div>

          <div className="console-foot">
            <span className="local-lock"><b aria-hidden="true">●</b> 简历与结果默认只留在本机</span>
            <a href="https://github.com/SuperMikasa/signalfit" target="_blank" rel="noreferrer">打开 GitHub <span aria-hidden="true">↗</span></a>
          </div>
          <p className="copy-status" role="status" aria-live="polite">
            {copyState === "error" ? "浏览器未允许复制，请手动选中指令。" : ""}
          </p>
        </div>
      </section>

      <section className="community-loop-section" id="loop">
        <header className="section-heading">
          <div><p className="section-kicker">LIVING BASELINE / 持续更新</p><h2>用一次，也让 AI 能力地图更准。</h2></div>
          <p>用户获取最新公开基线；仓库每周检查新鲜度；社区把新的官方 JD 和真实面经反向提交给维护者。</p>
        </header>
        <div className="loop-grid">
          <article>
            <b>USER UPDATE</b><strong>01</strong><h3>一条命令同步最新基线</h3>
            <code>./signalfit update</code>
            <p>只下载公开能力地图，不上传简历。离线时仍可继续使用仓库内 provisional 基线。</p>
          </article>
          <article>
            <b>WEEKLY CHECK</b><strong>02</strong><h3>每周检查是否过期</h3>
            <p>GitHub 定时检查基线生成时间。超过新鲜度目标就自动创建维护任务，提醒重新核验 JD 与面经。</p>
            <a href="https://github.com/SuperMikasa/signalfit/actions/workflows/baseline-refresh.yml" target="_blank" rel="noreferrer">查看更新状态 <span aria-hidden="true">↗</span></a>
          </article>
          <article className="contribution-card">
            <b>COMMUNITY IN</b><strong>03</strong><h3>把岗位证据反向告诉我们</h3>
            <p>结构化提交先进入审核队列；只有可核验的官方 JD 和 accepted 真实面经才会进入下一版能力地图。</p>
            <div className="contribution-links">
              <a href="https://github.com/SuperMikasa/signalfit/issues/new?template=contribute-ai-jd.yml" target="_blank" rel="noreferrer">提交 AI JD</a>
              <a href="https://github.com/SuperMikasa/signalfit/issues/new?template=contribute-interview.yml" target="_blank" rel="noreferrer">提交真实面经</a>
            </div>
          </article>
        </div>
      </section>

      <section className="open-source-section" id="open-source">
        <div className="source-copy">
          <p className="section-kicker">OPEN SOURCE / 开放协议</p>
          <h2>为 AI 岗位准备，把简历留在本机。</h2>
          <p>项目以 MIT 协议开放，并只围绕 AI 产品、AI 全栈 / Agent 工程和 FDE 构建能力基线。使用 OpenCode、Claude Code、Codex 或其他 Coding Agent 读取 AGENTS.md，即可在本机生成评分、证据清单和雷达报告。</p>
          <div className="source-actions">
            <a className="primary-action" href="https://github.com/SuperMikasa/signalfit" target="_blank" rel="noreferrer">在 GitHub 获取项目</a>
            <a className="secondary-action" href="https://github.com/SuperMikasa/signalfit#use-with-any-coding-cli" target="_blank" rel="noreferrer">本地运行说明</a>
            <a className="secondary-action" href="https://github.com/SuperMikasa/signalfit/tree/main/data/evidence" target="_blank" rel="noreferrer">查看公开证据</a>
            <a className="secondary-action" href="/example-fit.json" download>示例 JSON</a>
          </div>
          <p className="mirror-note"><code>./signalfit analyze /path/to/resume.pdf</code> · local-first · no upload</p>
        </div>
        <div className="pipeline-code" aria-label="开源处理流程">
          <div><span>01</span><code>git clone signalfit</code><p>获取公开基线与 Agent 说明</p></div>
          <div><span>02</span><code>./signalfit update</code><p>同步最新公开 AI 能力基线</p></div>
          <div><span>03</span><code>./signalfit analyze</code><p>本地简历 → 证据与缺口</p></div>
          <div><span>04</span><code>./signalfit serve</code><p>本机展示能力雷达</p></div>
        </div>
      </section>

      <footer><a className="brand" href="#top"><span className="brand-mark">SF</span><span>SignalFit</span></a><p>Built for AI roles. Evidence, not vibes.</p><span>MIT License · 2026</span></footer>
    </main>
  );
}
