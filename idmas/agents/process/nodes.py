# =============================================================================
# Process SubGraph 节点函数
#
# 节点函数:
#   - extract_params_node(state: ProcessState) -> dict
#     从Vision/OCR结果中提取工艺参数 (温度、压力、转速等)
#
#   - check_params_node(state: ProcessState) -> dict
#     对比知识库中的工艺标准，校验参数合理性
#
#   - check_sequence_node(state: ProcessState) -> dict
#     检查工序逻辑顺序是否合理
#
#   - finalize_node(state: ProcessState) -> dict
#     汇总工艺分析结果
# =============================================================================
