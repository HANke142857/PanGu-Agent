# =============================================================================
# Design SubGraph 构建
#
# 节点:
#   - load_standards: 加载相关设计标准
#   - check_compliance: 标号命名合规性检查
#   - check_bom: BOM一致性检查
#   - generate_suggestions: 生成改进建议
#   - finalize: 输出最终结果
#
# 流程:
#   load_standards → check_compliance → check_bom → generate_suggestions → finalize
# =============================================================================
