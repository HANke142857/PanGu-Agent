"""
PaddleOCR 客户端（生产）。

实现 BaseOCRClient，通过 HTTP 调用 PaddleOCR 服务。httpx 惰性导入——仅实例化并
访问时才需要安装，测试用 FakeOCRClient 不受影响。

服务约定：POST {OCR_URL}/ocr  body={"image_url": ...}
返回任一形态均可解析::

    {"results": [{"text","score","box"}, ...]}
    {"texts": [...], "scores": [...], "boxes": [...]}

降级：调用失败由上层 Vision 节点捕获，按"无 OCR 结果"继续，不阻断主流程。
"""

from __future__ import annotations

import logging
from typing import Any

from idmas.infrastructure.ocr.base import BaseOCRClient

logger = logging.getLogger(__name__)


class PaddleOCRClient(BaseOCRClient):
    def __init__(self, url: str, timeout: int = 30) -> None:
        self._url = url.rstrip("/")
        self._timeout = timeout

    @staticmethod
    def _normalize(payload: dict) -> list[dict[str, Any]]:
        """把服务响应统一成 [{text, score, box}]。"""
        if isinstance(payload.get("results"), list):
            out = []
            for item in payload["results"]:
                out.append({
                    "text":  str(item.get("text", "")),
                    "score": float(item.get("score", 0.0)),
                    "box":   item.get("box", []),
                })
            return out

        texts  = payload.get("texts") or []
        scores = payload.get("scores") or []
        boxes  = payload.get("boxes") or []
        out = []
        for i, text in enumerate(texts):
            out.append({
                "text":  str(text),
                "score": float(scores[i]) if i < len(scores) else 0.0,
                "box":   boxes[i] if i < len(boxes) else [],
            })
        return out

    async def extract(self, image_url: str) -> list[dict[str, Any]]:
        import httpx  # 惰性导入

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(f"{self._url}/ocr", json={"image_url": image_url})
            resp.raise_for_status()
            return self._normalize(resp.json())

    async def health_check(self) -> bool:
        import httpx  # 惰性导入

        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self._url}/health")
                return resp.status_code == 200
        except Exception:  # noqa: BLE001
            return False
