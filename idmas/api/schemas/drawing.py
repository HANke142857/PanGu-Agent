# =============================================================================
# 图纸管理 Pydantic Schema
#
# 请求Schema:
#   - DrawingUploadRequest: 图纸上传请求 (multipart/form-data)
#     - file: UploadFile (png/jpg/pdf/dwg/dxf)
#     - title: str
#     - drawing_type: DrawingType枚举
#     - source_system: str | None
#     - source_doc_id: str | None
#     - metadata: dict | None
#
# 响应Schema:
#   - DrawingResponse: 图纸详情
#     - id, title, drawing_type, file_format
#     - file_url (presigned URL)
#     - file_size_bytes, image_width, image_height
#     - lifecycle_state, source_system
#     - created_at, updated_at
#
#   - DrawingListResponse: 图纸列表 (分页)
#
# 校验规则:
#   - 文件大小上限: 50MB
#   - 图片尺寸上限: 4096×4096
#   - 允许格式: png, jpg, jpeg, pdf, dwg, dxf
# =============================================================================
