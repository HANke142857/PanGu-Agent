# =============================================================================
# Report SubGraph 节点函数
#
# 节点函数:
#   - collect_results_node(state: ReportState) -> dict
#     收集Vision/Design/Process/Knowledge各Agent结果
#     合并冲突解决信息和人工审核决策
#
#   - generate_sections_node(state: ReportState) -> dict
#     使用LLM为每个分析维度生成报告章节
#
#   - generate_summary_node(state: ReportState) -> dict
#     生成报告摘要和关键发现
#
#   - format_report_node(state: ReportState) -> dict
#     格式化为最终报告结构(JSON/Markdown)
#
#   - finalize_node(state: ReportState) -> dict
#     输出最终报告
# =============================================================================
