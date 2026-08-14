---
name: build-role-capability-map
description: 从官方 JD 原子信号和已验收真实面经生成 AI 产品、AI 全栈/Agent 工程、FDE 等岗位的独立能力地图、Top 能力和约束清单。用户要求更新岗位能力地图、比较岗位方向、找市场 Top 能力或为简历匹配准备岗位基准时使用。
---

# Build Role Capability Map

1. 读取最新 `jd-signals.jsonl`、`question-bank.jsonl` 和 `record-status.jsonl`。公开仓库没有可再分发的面经原文时，可读取 `accepted-interview-snapshot.json` 中已验收记录的聚合计数与短摘要。
2. 运行：

```bash
python3 scripts/build_role_capability_map.py \
  --scout-root <interview-scout-root> \
  --output-dir <output-dir> \
  --top 6
```

3. 回读 `role-capability-map.json` 和 `role-capability-map.md`。
4. 分岗位报告 Top 能力、独立 JD 数、真实面经数和证据覆盖状态。
5. 只把 `accepted + real_interview_report` 计作真实面经；不得把官方招聘信号冒充面试原题。
6. 将地点、经验、毕业时间和用工方式放入 `constraints`，不得当成能力缺口。
7. 若 expanded baseline 未完成，必须将地图标为 `provisional`。
8. 公开仓库只保存 JD 原子化摘要、官方 URL 与检索日期，不镜像完整 JD 或含个人信息的面经正文。

字段与评分说明见 [schema.md](references/schema.md)。
