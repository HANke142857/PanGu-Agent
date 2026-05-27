# =============================================================================
# Report SubGraph 状态定义 (ReportState)
#
# 状态字段:
#   - vision_result: dict | None        # Vision Agent结果
#   - design_result: dict | None        # Design Agent结果
#   - process_result: dict | None       # Process Agent结果
#   - knowledge_result: dict | None     # Knowledge Agent结果
#   - conflicts_resolved: list[dict]    # 已解决的冲突列表
#   - human_decisions: dict | None      # 人工审核决策
#   - report_sections: list[dict]       # 报告各章节
#   - summary: str | None               # 报告摘要
#   - final_report: dict | None         # 最终报告
# =============================================================================
