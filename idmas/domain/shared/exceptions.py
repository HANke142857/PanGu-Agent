"""
领域异常定义。
错误码格式：IDMAS-{HTTP状态码}-{序号}
所有业务异常继承自 IDMASError，便于统一捕获。
"""

from __future__ import annotations


class IDMASError(Exception):
    """系统基础异常。所有自定义异常的根。"""

    code: str = "IDMAS-500-000"
    http_status: int = 500

    def __init__(self, message: str = "Internal error", detail: str | None = None) -> None:
        self.message = message
        self.detail = detail
        super().__init__(message)

    def __repr__(self) -> str:  # pragma: no cover
        return f"{self.__class__.__name__}(code={self.code!r}, message={self.message!r})"


class DomainError(IDMASError):
    """领域逻辑错误基类。"""
    code = "IDMAS-422-000"
    http_status = 422


# ------------------------------------------------------------------
# 资源不存在 (404)
# ------------------------------------------------------------------

class DrawingNotFoundError(DomainError):
    code = "IDMAS-404-001"
    http_status = 404

    def __init__(self, drawing_id: str) -> None:
        super().__init__(message=f"Drawing not found: {drawing_id}", detail=drawing_id)


class TaskNotFoundError(DomainError):
    code = "IDMAS-404-002"
    http_status = 404

    def __init__(self, task_id: str) -> None:
        super().__init__(message=f"Task not found: {task_id}", detail=task_id)


# ------------------------------------------------------------------
# 校验失败 (422)
# ------------------------------------------------------------------

class InvalidDrawingError(DomainError):
    """图纸校验失败，如尺寸超限 > 4096²。"""
    code = "IDMAS-422-001"


class InvalidTaskStateError(DomainError):
    """非法任务状态转换。"""
    code = "IDMAS-422-002"

    def __init__(self, current: str, target: str) -> None:
        super().__init__(
            message=f"Invalid task state transition: {current!r} → {target!r}",
            detail=f"current={current}, target={target}",
        )


# ------------------------------------------------------------------
# 业务逻辑异常
# ------------------------------------------------------------------

class ConflictDetectedError(DomainError):
    """Agent 之间检测到标号冲突，需对抗辩论裁决。"""
    code = "IDMAS-409-001"
    http_status = 409


class LowConfidenceError(DomainError):
    """置信度低于阈值，需人工审核。"""
    code = "IDMAS-422-003"

    def __init__(self, confidence: float, threshold: float) -> None:
        super().__init__(
            message=f"Confidence {confidence:.2f} below threshold {threshold:.2f}",
            detail=f"confidence={confidence}, threshold={threshold}",
        )


# ------------------------------------------------------------------
# 外部系统错误 (502 / 503)
# ------------------------------------------------------------------

class PLMConnectionError(IDMASError):
    """PLM 系统（Teamcenter/ENOVIA/IntePLM）连接失败。"""
    code = "IDMAS-502-001"
    http_status = 502


class VLLMInferenceError(IDMASError):
    """vLLM 推理失败（含 GPU OOM）。"""
    code = "IDMAS-502-002"
    http_status = 502


class OCRExtractionError(IDMASError):
    """PaddleOCR 提取失败。"""
    code = "IDMAS-502-003"
    http_status = 502


class KnowledgeSearchError(IDMASError):
    """知识库检索失败。"""
    code = "IDMAS-502-004"
    http_status = 502


class StorageError(IDMASError):
    """对象存储（MinIO 等）读写失败，通常是服务未启动或网络不通。"""
    code = "IDMAS-502-005"
    http_status = 502


# ------------------------------------------------------------------
# 认证 / 鉴权 (401 / 403)
# ------------------------------------------------------------------

class AuthenticationError(IDMASError):
    """认证失败（Token 无效或过期）。"""
    code = "IDMAS-401-001"
    http_status = 401

    def __init__(self, message: str = "Authentication failed") -> None:
        super().__init__(message=message)


class AuthorizationError(IDMASError):
    """权限不足。"""
    code = "IDMAS-403-001"
    http_status = 403

    def __init__(self, message: str = "Insufficient permissions") -> None:
        super().__init__(message=message)


# ------------------------------------------------------------------
# 限流 (429)
# ------------------------------------------------------------------

class RateLimitExceededError(IDMASError):
    """请求频率超限。"""
    code = "IDMAS-429-001"
    http_status = 429

    def __init__(self, retry_after: int = 60) -> None:
        super().__init__(
            message=f"Rate limit exceeded. Retry after {retry_after}s",
            detail=f"retry_after={retry_after}",
        )
        self.retry_after = retry_after
