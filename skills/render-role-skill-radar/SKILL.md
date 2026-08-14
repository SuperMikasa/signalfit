---
name: render-role-skill-radar
description: 将 score-resume-role-fit 生成的多岗位评分 JSON 渲染为 AI 产品、AI 全栈/Agent 工程、FDE 雷达图、响应式 HTML 和中文缺口摘要。用户要求雷达图、可视化比较岗位匹配度、展示优势短板或导出能力画像时使用。
---

# Render Role Skill Radar

1. 读取 `resume-role-fit.json`。
2. 运行：

```bash
python3 scripts/render_role_skill_radar.py \
  --fit <resume-role-fit.json> \
  --output-dir <output-dir>
```

3. 回读 `role-fit-radar.html`、三个岗位 SVG 和 `role-fit-radar.md`。
4. 雷达图外圈代表岗位 Top 能力目标 100；候选人多边形代表简历证据分。
5. 图旁只列优先缺口和建议，不把地点/毕业/签证等约束画进能力轴。
6. 若输入地图为 provisional，在页面顶部显示醒目标识。

视觉口径见 [radar-contract.md](references/radar-contract.md)。
