# =============================================================================
# Design SubGraph 状态定义 (DesignState)
#
# 状态字段:
#   - labels: list[dict]              # 输入标号列表 (来自Vision)
#   - drawing_type: str               # 图纸类型
#   - design_standards: list[dict]    # 匹配到的设计标准
#   - compliance_results: list[dict]  # 合规检查结果
#   - bom_check: dict | None          # BOM一致性检查
#   - suggestions: list[str]          # 改进建议
#   - final_result: dict | None       # 最终结果
# =============================================================================
