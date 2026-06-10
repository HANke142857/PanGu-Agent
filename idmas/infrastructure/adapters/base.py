"""
PLM 适配器抽象。

各品牌 PLM（Teamcenter / ENOVIA / IntePLM）实现统一接口；回写的幂等与签名校验
在基类用模板方法收口，子类只实现品牌相关的 _do_writeback / get_document。

    BasePLMAdapter  : 抽象接口 + 幂等回写模板
    HTTPPLMAdapter  : 基于 httpx 的通用 REST 实现（品牌子类复用）
    FakePLMAdapter  : 测试/开发用，进程内记录回写（无需真实 PLM）

回写幂等：key = sha256(doc_id + data)，命中则跳过（MVP 用进程内集合，
生产替换为 Redis，TTL=7d）。
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class PLMDocument(BaseModel):
    doc_id:    str
    title:     str = ""
    revision:  str = ""
    metadata:  dict[str, Any] = Field(default_factory=dict)


class PLMWriteResult(BaseModel):
    success:       bool
    doc_id:        str
    target_system: str
    skipped:       bool = False          # 幂等命中而跳过
    message:       str  = ""


def _idempotency_key(doc_id: str, data: dict) -> str:
    body = json.dumps(data, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return f"{doc_id}:{hashlib.sha256(body).hexdigest()}"


class BasePLMAdapter(ABC):
    """PLM 适配器抽象基类。"""

    system: str = "base"

    def __init__(self, webhook_secret: str = "") -> None:
        self._webhook_secret = webhook_secret
        self._idempotent: set[str] = set()   # MVP 幂等存储；生产用 Redis

    # ── 回写（幂等模板方法）─────────────────────────────────────────────
    async def writeback(self, doc_id: str, data: dict) -> PLMWriteResult:
        key = _idempotency_key(doc_id, data)
        if key in self._idempotent:
            logger.info("[plm:%s] 幂等命中，跳过回写 doc=%s", self.system, doc_id)
            return PLMWriteResult(
                success=True, doc_id=doc_id, target_system=self.system,
                skipped=True, message="幂等命中，已跳过",
            )
        result = await self._do_writeback(doc_id, data)
        if result.success:
            self._idempotent.add(key)
        return result

    @abstractmethod
    async def _do_writeback(self, doc_id: str, data: dict) -> PLMWriteResult:
        """子类实现品牌相关的实际写入。"""
        ...

    @abstractmethod
    async def get_document(self, doc_id: str) -> PLMDocument | None:
        ...

    async def get_bom(self, doc_id: str) -> dict:
        return {}

    # ── Webhook 签名校验（HMAC-SHA256）─────────────────────────────────
    def verify_webhook(self, signature: str, payload: bytes) -> bool:
        if not self._webhook_secret:
            return False
        expected = hmac.new(self._webhook_secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature or "")

    async def health_check(self) -> bool:
        return True


class FakePLMAdapter(BasePLMAdapter):
    """进程内 Fake：记录回写历史，供测试 / 离线开发。"""

    system = "fake"

    def __init__(self, webhook_secret: str = "", documents: dict[str, PLMDocument] | None = None) -> None:
        super().__init__(webhook_secret)
        self._documents = documents or {}
        self.writebacks: list[tuple[str, dict]] = []   # 便于测试断言

    async def _do_writeback(self, doc_id: str, data: dict) -> PLMWriteResult:
        self.writebacks.append((doc_id, data))
        return PLMWriteResult(success=True, doc_id=doc_id, target_system=self.system, message="已回写(fake)")

    async def get_document(self, doc_id: str) -> PLMDocument | None:
        return self._documents.get(doc_id) or PLMDocument(doc_id=doc_id, title=f"Fake文档 {doc_id}")


class HTTPPLMAdapter(BasePLMAdapter):
    """基于 httpx 的通用 REST 适配器，品牌子类配置 base_url / 路径。"""

    system = "http"
    writeback_path = "/documents/{doc_id}/attributes"
    document_path = "/documents/{doc_id}"

    def __init__(self, base_url: str, token: str = "", webhook_secret: str = "") -> None:
        super().__init__(webhook_secret)
        self._base_url = base_url.rstrip("/")
        self._token = token

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._token}"} if self._token else {}

    async def _do_writeback(self, doc_id: str, data: dict) -> PLMWriteResult:
        import httpx  # 惰性导入

        url = self._base_url + self.writeback_path.format(doc_id=doc_id)
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(url, json=data, headers=self._headers())
                resp.raise_for_status()
            return PLMWriteResult(success=True, doc_id=doc_id, target_system=self.system, message="已回写")
        except Exception as exc:  # noqa: BLE001 — 失败交由上层重试/DLQ
            logger.warning("[plm:%s] 回写失败 doc=%s: %s", self.system, doc_id, exc)
            return PLMWriteResult(
                success=False, doc_id=doc_id, target_system=self.system, message=str(exc)
            )

    async def get_document(self, doc_id: str) -> PLMDocument | None:
        import httpx  # 惰性导入

        url = self._base_url + self.document_path.format(doc_id=doc_id)
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(url, headers=self._headers())
                if resp.status_code == 404:
                    return None
                resp.raise_for_status()
                body = resp.json()
            return PLMDocument(
                doc_id=doc_id,
                title=str(body.get("title", "")),
                revision=str(body.get("revision", "")),
                metadata=body,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("[plm:%s] 取文档失败 doc=%s: %s", self.system, doc_id, exc)
            return None
