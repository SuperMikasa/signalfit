# 岗位能力地图口径

- `jd_job_count`: 提及该能力的独立 active JD URL 数。
- `jd_signal_count`: 该能力的原子 JD 信号数。
- `real_interview_report_count`: 最新状态为 accepted 且 `evidence_type=real_interview_report` 的独立 `report_id` 数。
- `real_interview_question_count`: 上述报告中已验收的独立 `record_id` 数。
- 能力项的 `interview_report_count` 表示覆盖该能力的独立面经数，`interview_question_count` 表示对应问题数。
- `job_penetration`: `jd_job_count / 岗位族独立 JD 总数`。
- `market_score`: 85% JD 覆盖率 + 15% 独立面经覆盖率。若该岗位没有可追溯真实面经，则只使用 JD 覆盖率。
- `priority_weight`: 当前岗位 Top 能力内归一化的市场权重，供简历匹配计算总分。
- `coverage_status=provisional`: 完整市场基线仍未通过；排序可用于当前决策，但不是最终市场结论。

`eligibility_constraint` 永远不进入能力雷达图。
