# =============================================================================
# 环境变量管理 (Pydantic Settings)
#
# 职责:
#   - 从.env文件或环境变量加载配置
#   - 类型校验和默认值
#   - 不同环境(dev/staging/production)配置区分
#
# 配置类:
#   - Settings: 主配置类 (BaseSettings)
#     应用:
#       - APP_ENV: development | staging | production
#       - APP_DEBUG: bool
#       - APP_LOG_LEVEL: DEBUG | INFO | WARN | ERROR
#       - APP_CORS_ORIGINS: list[str]
#
#     数据库:
#       - DATABASE_URL: PostgreSQL连接串
#       - DB_POOL_SIZE / DB_MAX_OVERFLOW / DB_POOL_TIMEOUT
#
#     Redis:
#       - REDIS_URL: Redis连接地址
#
#     vLLM:
#       - VLLM_URL / VLLM_MODEL / VLLM_MAX_TOKENS / VLLM_TEMPERATURE / VLLM_TIMEOUT
#
#     OCR:
#       - OCR_URL / OCR_TIMEOUT
#
#     Milvus:
#       - MILVUS_HOST / MILVUS_PORT
#
#     Neo4j:
#       - NEO4J_URI / NEO4J_USER / NEO4J_PASSWORD
#
#     Elasticsearch:
#       - ES_URL
#
#     MinIO:
#       - MINIO_ENDPOINT / MINIO_ACCESS_KEY / MINIO_SECRET_KEY / MINIO_BUCKET
#
#     RabbitMQ:
#       - RABBITMQ_URL
#
#     JWT:
#       - JWT_PRIVATE_KEY_PATH / JWT_PUBLIC_KEY_PATH / JWT_ALGORITHM / JWT_EXPIRE_MINUTES
#
#     可观测性:
#       - LANGFUSE_HOST / LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY
#       - OTEL_EXPORTER_OTLP_ENDPOINT
#
# 密钥管理:
#   - 开发: .env 文件 (gitignored)
#   - 测试: GitLab CI Variables (masked)
#   - 生产: HashiCorp Vault
# =============================================================================
