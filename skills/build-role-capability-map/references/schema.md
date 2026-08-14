# 岗位能力地图口径

- `jd_job_count`: 提及该能力的独立 active JD URL 数。
- `jd_signal_count`: 该能力的原子 JD 信号数。
- `interview_count`: 最新状态为 accepted 且 `evidence_type=real_interview_report` 的独立题目数。
- `job_penetration`: `jd_job_count / 岗位族独立 JD 总数`。
- `market_score`: 85% JD 覆盖率 + 15% 真实面经占比。若该岗位没有真实面经，则只使用 JD 覆盖率。
- `priority_weight`: 当前岗位 Top 能力内归一化的市场权重，供简历匹配计算总分。
- `coverage_status=provisional`: 完整市场基线仍未通过；排序可用于当前决策，但不是最终市场结论。

`eligibility_constraint` 永远不进入能力雷达图。
