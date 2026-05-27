# =============================================================================
# 图纸管理路由
#
# 端点:
#   POST /api/v1/drawings           上传图纸 (限流: 20/min)
#     - 校验文件格式 (png/jpg/pdf/dwg/dxf)
#     - 校验图片尺寸 (>4096² 拒绝, 返回IDMAS-400-003)
#     - 上传到MinIO
#     - 计算SHA256校验值
#     - 创建drawings记录
#     - 返回drawing_id和file_url
#
#   GET  /api/v1/drawings/{id}      获取图纸信息
#     - 返回图纸元数据 + presigned下载URL
#     - L3数据presigned URL过期: 5分钟
#     - L2数据presigned URL过期: 1小时
#
#   GET  /api/v1/drawings           图纸列表 (支持分页、搜索)
# =============================================================================
