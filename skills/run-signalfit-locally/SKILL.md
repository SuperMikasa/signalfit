---
name: run-signalfit-locally
description: 在本机读取 Markdown、TXT、PDF 或 DOCX 简历，使用仓库内公开岗位能力基线生成 AI 产品、AI 全栈/Agent 工程和 FDE 的证据匹配分、缺口清单、SVG 与 HTML 雷达图。用户要求通过 Codex、Claude Code、Kimi Code 或其他 coding CLI 私密分析简历、运行 SignalFit、部署本地结果页时使用。
---

# Run SignalFit Locally

1. 从仓库根目录运行 `./signalfit doctor`。
2. 对用户明确提供的本地简历运行：

```bash
./signalfit analyze <resume.md|txt|pdf|docx>
```

3. 读取 `.signalfit/latest.json` 指向的 `resume-role-fit.md`。
4. 报告三个岗位的证据覆盖分、最强证据、优先缺口与单列硬约束。
5. 向用户提供 `role-fit-radar.html` 的本地路径。只有用户需要本地 HTTP 预览时才运行 `./signalfit serve`。
6. 不上传、复制到 tracked 文件、提交或公开简历与生成结果。
7. 不把分数描述为录用概率，不推断简历中没有的能力。

PDF 缺少读取器时，在仓库虚拟环境中安装 `requirements.txt`；MD、TXT 和 DOCX 使用标准库即可。市场基线更新属于维护者工作流，除非用户明确要求，不要在分析简历时联网刷新。
