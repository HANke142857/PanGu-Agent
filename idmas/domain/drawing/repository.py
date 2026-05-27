# =============================================================================
# 图纸仓储接口 (Drawing Repository Interface)
#
# 定义抽象仓储接口，由 infrastructure 层实现
#
# 接口方法:
#   - get_by_id(drawing_id: UUID) -> Drawing | None
#   - save(drawing: Drawing) -> Drawing
#   - list_by_user(user_id: UUID, offset, limit) -> list[Drawing]
#   - search_by_title(keyword: str) -> list[Drawing]
#   - get_labels(drawing_id: UUID) -> list[DrawingLabel]
#   - save_labels(labels: list[DrawingLabel]) -> None
#   - update_label(label: DrawingLabel) -> None
# =============================================================================
