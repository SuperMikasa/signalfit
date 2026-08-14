---
name: score-resume-role-fit
description: 读取 Markdown、TXT、PDF 或 DOCX 简历，按最新多岗位能力地图分别计算 AI 产品、AI 全栈/Agent 工程、FDE 匹配度，返回可定位的简历证据、能力缺口、学习动作和独立硬约束清单。用户要求判断简历匹配度、比较适合岗位、找缺失能力或制定补强计划时使用。
---

# Score Resume Role Fit

1. 先用 build-role-capability-map 生成最新 `role-capability-map.json`。
2. 运行：

```bash
python3 scripts/score_resume_role_fit.py \
  --map <role-capability-map.json> \
  --resume <resume.md|txt|pdf|docx> \
  --output-dir <output-dir>
```

3. 回读 `resume-role-fit.json` 和 `resume-role-fit.md`。
4. 每条已匹配能力必须附简历行号和原文证据；没有证据时记为缺口，不得根据项目背景自行补写。
5. 总分只聚合能力轴；地点、毕业、工时、签证和用工方式放在 `constraints_to_review`。
6. 若地图为 provisional，必须同步提示评分也为 provisional。

评分解释见 [scoring.md](references/scoring.md)。
