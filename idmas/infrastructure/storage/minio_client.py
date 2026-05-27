# =============================================================================
# MinIO 对象存储客户端
#
# 职责:
#   - 图纸文件上传/下载
#   - Presigned URL生成 (L3数据=5min过期, L2数据=1h过期)
#   - 文件SHA256校验
#   - Bucket策略管理
#
# 配置:
#   - MINIO_ENDPOINT: MinIO地址
#   - MINIO_ACCESS_KEY / MINIO_SECRET_KEY: 认证
#   - MINIO_BUCKET: 默认Bucket (idmas-drawings)
#
# 方法:
#   - upload(file_data, object_name, content_type) -> str
#   - download(object_name) -> bytes
#   - get_presigned_url(object_name, expires_seconds) -> str
#   - delete(object_name) -> None
#   - compute_sha256(file_data) -> str
#   - ensure_bucket(bucket_name) -> None
#   - health_check() -> bool
#
# 存储加密: SSE-S3 (AES-256) 服务端加密
# =============================================================================
