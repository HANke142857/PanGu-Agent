# =============================================================================
# 图纸领域值对象
#
# 包含:
#   - DrawingType: 图纸类型枚举 (assembly/part/process/schematic)
#   - FileFormat: 文件格式枚举 (png/jpg/pdf/dwg/dxf)
#   - LifecycleState: 生命周期状态枚举 (draft/released/obsolete)
#   - BoundingBox: 边界框值对象 (x, y, width, height)
#   - SpatialInfo: 空间信息值对象 (position, quadrant, region)
#   - ImageDimension: 图片尺寸值对象 (width, height)
#     - 校验规则: 单边不超过4096像素
# =============================================================================
