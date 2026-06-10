"""
全局配置管理 (Pydantic Settings)
从 .env 文件或环境变量加载，类型安全，支持 dev/staging/production 三环境。
"""

from __future__ import annotations

from enum import Enum
from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnv(str, Enum):
    development = "development"
    staging     = "staging"
    production  = "production"


class LogLevel(str, Enum):
    DEBUG   = "DEBUG"
    INFO    = "INFO"
    WARNING = "WARNING"
    ERROR   = "ERROR"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ------------------------------------------------------------------
    # 应用
    # ------------------------------------------------------------------
    APP_ENV:          AppEnv   = AppEnv.development
    APP_DEBUG:        bool     = True
    APP_LOG_LEVEL:    LogLevel = LogLevel.INFO
    APP_CORS_ORIGINS: list[str] = Field(default=["http://localhost:3000"])

    # ------------------------------------------------------------------
    # PostgreSQL
    # ------------------------------------------------------------------
    # 仓储后端：memory（开发/测试，进程内）| sql（PostgreSQL 持久化）
    DB_BACKEND:        str = "memory"
    DATABASE_URL:      str = "postgresql+asyncpg://idmas:password@localhost:5432/idmas"
    DB_POOL_SIZE:      int = Field(default=10,  ge=1,  le=100)
    DB_MAX_OVERFLOW:   int = Field(default=20,  ge=0,  le=100)
    DB_POOL_TIMEOUT:   int = Field(default=30,  ge=1,  le=300)

    # ------------------------------------------------------------------
    # Redis
    # ------------------------------------------------------------------
    REDIS_URL: str = "redis://localhost:6379/0"

    # ------------------------------------------------------------------
    # vLLM
    # ------------------------------------------------------------------
    VLLM_URL:            str   = "http://localhost:8000"
    VLLM_MODEL:          str   = "qwen2.5-vl-7b-finetuned"
    VLLM_MAX_TOKENS:     int   = Field(default=2048, ge=128,  le=8192)
    VLLM_TEMPERATURE:    float = Field(default=0.1,  ge=0.0,  le=2.0)
    VLLM_TIMEOUT:        int   = Field(default=60,   ge=10,   le=300)
    VLLM_MAX_CONCURRENT: int   = Field(default=8,    ge=1,    le=32)

    # ------------------------------------------------------------------
    # OCR (PaddleOCR)
    # ------------------------------------------------------------------
    # OCR 后端：fake（确定性假结果，开发/测试）| paddle（生产）
    OCR_BACKEND: str = "fake"
    OCR_URL:     str = "http://localhost:8100"
    OCR_TIMEOUT: int = Field(default=30, ge=5, le=120)

    # ------------------------------------------------------------------
    # Milvus / 向量检索
    # ------------------------------------------------------------------
    # 向量库后端：memory（内存 + 预置 KB，开发/测试）| milvus（生产）
    VECTOR_BACKEND: str = "memory"
    EMBEDDING_DIM:  int = Field(default=768, ge=8, le=4096)
    MILVUS_HOST: str = "localhost"
    MILVUS_PORT: int = Field(default=19530, ge=1, le=65535)

    # ------------------------------------------------------------------
    # Neo4j / 知识图谱
    # ------------------------------------------------------------------
    # 图谱后端：memory（内存 + 预置图谱，开发/测试）| neo4j（生产）
    GRAPH_BACKEND:  str = "memory"
    NEO4J_URI:      str = "bolt://localhost:7687"
    NEO4J_USER:     str = "neo4j"
    NEO4J_PASSWORD: str = "password"

    # ------------------------------------------------------------------
    # Elasticsearch / 全文检索
    # ------------------------------------------------------------------
    # 搜索后端：memory（内存 token 重叠，开发/测试）| es（生产）
    SEARCH_BACKEND: str = "memory"
    ES_URL: str = "http://localhost:9200"

    # ------------------------------------------------------------------
    # MinIO / 对象存储
    # ------------------------------------------------------------------
    # 存储后端：memory（进程内，开发/测试）| minio（生产）
    STORAGE_BACKEND:  str = "memory"
    MINIO_ENDPOINT:   str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET:     str = "idmas-drawings"
    MINIO_SECURE:     bool = False

    # ------------------------------------------------------------------
    # RabbitMQ
    # ------------------------------------------------------------------
    # 任务队列后端：eager（单机/测试，发布即就地处理）| rabbitmq（独立 Worker 消费）
    MQ_BACKEND:   str = "eager"
    RABBITMQ_URL: str = "amqp://idmas:password@localhost:5672"

    # ------------------------------------------------------------------
    # JWT
    # ------------------------------------------------------------------
    JWT_PRIVATE_KEY_PATH: str = "/path/to/private.pem"
    JWT_PUBLIC_KEY_PATH:  str = "/path/to/public.pem"
    JWT_ALGORITHM:        str = "RS256"
    JWT_EXPIRE_MINUTES:   int = Field(default=60, ge=5, le=1440)

    # ------------------------------------------------------------------
    # 可观测性
    # ------------------------------------------------------------------
    LANGFUSE_HOST:               str = "http://localhost:3000"
    LANGFUSE_PUBLIC_KEY:         str = "pk-placeholder"
    LANGFUSE_SECRET_KEY:         str = "sk-placeholder"
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://localhost:4317"

    # ------------------------------------------------------------------
    # 业务阈值（运行时可覆盖，无需改代码）
    # ------------------------------------------------------------------
    CONFIDENCE_HIGH_THRESHOLD: Annotated[float, Field(ge=0.0, le=1.0)] = 0.85
    CONFIDENCE_LOW_THRESHOLD:  Annotated[float, Field(ge=0.0, le=1.0)] = 0.60
    IMAGE_MAX_DIMENSION:       int = Field(default=4096, ge=256, le=16384)

    @field_validator("APP_CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors(cls, v: str | list[str]) -> list[str]:
        """支持逗号分隔的字符串形式：APP_CORS_ORIGINS=http://a.com,http://b.com"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == AppEnv.production

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == AppEnv.development


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """单例获取配置（进程内缓存）。测试时用 get_settings.cache_clear() 重置。"""
    return Settings()


# 方便直接 `from config.settings import settings` 使用
settings = get_settings()
