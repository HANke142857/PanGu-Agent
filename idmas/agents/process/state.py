# =============================================================================
# Process SubGraph 状态定义 (ProcessState)
#
# 状态字段:
#   - labels: list[dict]               # 输入标号列表
#   - process_params: dict | None      # 提取的工艺参数
#   - param_check_results: list[dict]  # 参数合理性检查结果
#   - sequence_check: dict | None      # 工序逻辑检查
#   - warnings: list[str]              # 告警信息
#   - final_result: dict | None        # 最终结果
# =============================================================================
