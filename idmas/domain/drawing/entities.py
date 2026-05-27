# =============================================================================
# 图纸领域实体
#
# 包含:
#   - Drawing: 图纸实体(聚合根)
#     - id: UUID
#     - source_system: 来源系统 (Teamcenter/ENOVIA/IntePLM)
#     - source_doc_id: 来源系统文档ID
#     - title: 图纸标题
#     - drawing_type: 图纸类型 (装配图/零件图/工艺图等)
#     - file_format: 文件格式 (png/jpg/pdf/dwg)
#     - file_url: MinIO文件URL
#     - file_size_bytes: 文件大小
#     - image_width / image_height: 图片尺寸
#     - lifecycle_state: 生命周期状态 (draft/released/obsolete)
#     - metadata: 扩展元数据(JSONB)
#
#   - DrawingLabel: 标号实体
#     - id: UUID
#     - label_id: 标号编号 (如 "1", "2", "3")
#     - name: 标号名称 (如 "轴承座", "齿轮箱")
#     - confidence: 识别置信度 (0.0~1.0)
#     - spatial_info: 空间位置信息
#     - bounding_box: 边界框坐标
#     - source: 来源 (vision_agent/ocr/human)
# =============================================================================
