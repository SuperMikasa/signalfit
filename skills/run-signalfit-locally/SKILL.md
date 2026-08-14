---
name: run-signalfit-locally
description: 在本机读取 Markdown、TXT、PDF 或 DOCX 简历，使用公开 AI 岗位能力基线生成 AI 产品、AI 全栈/Agent 工程和 FDE 的证据匹配分、缺口清单、SVG 与 HTML 雷达图。用户要求通过 OpenCode、Claude Code、Codex 或其他 Coding Agent 私密分析简历、运行 SignalFit、部署本地结果页时使用。
---

# Run SignalFit Locally

1. 若用户明确要求最新公开基线，先运行 `./signalfit update`。该命令只下载公开能力地图，不上传简历；网络不可用时说明将使用仓库内 provisional 基线。
2. 从仓库根目录运行 `./signalfit doctor`。
3. 对用户明确提供的本地简历运行：

```bash
./signalfit analyze <resume.md|txt|pdf|docx>
```

4. 读取 `.signalfit/latest.json` 指向的 `resume-role-fit.md`。
5. 报告三个岗位的证据覆盖分、最强证据、优先缺口与单列硬约束。
6. 向用户提供 `role-fit-radar.html` 的本地路径。只有用户需要本地 HTTP 预览时才运行 `./signalfit serve`。
7. 不上传、复制到 tracked 文件、提交或公开简历与生成结果。
8. 不把分数描述为录用概率，不推断简历中没有的能力。

PDF 缺少读取器时，在仓库虚拟环境中安装 `requirements.txt`；MD、TXT 和 DOCX 使用标准库即可。除非用户明确要求最新基线，不要在分析简历时联网刷新。
