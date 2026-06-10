"""
OCR 抽象。

与项目其它基础设施一致（抽象接口 + Fake + 真实实现）::

    BaseOCRClient   : 抽象接口，Vision Agent 低置信度重试时依赖它
    FakeOCRClient   : 测试/开发用，返回确定性结果（无需 OCR 服务）
    PaddleOCRClient : 生产实现，见 paddle_client.py（需 PaddleOCR 服务）

extract(image_url) 返回 list[dict]，每项 ``{"text": str, "score": float, "box": list}``，
与 vision_prompts.build_ocr_augmented_prompt 的约定一致。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseOCRClient(ABC):
    @abstractmethod
    async def extract(self, image_url: str) -> list[dict[str, Any]]:
        """识别图片中的文字，返回 [{text, score, box}, ...]。"""
        ...

    async def health_check(self) -> bool:
        return True


class FakeOCRClient(BaseOCRClient):
    """确定性 Fake：返回固定的标号文字，供测试 / 离线开发。"""

    def __init__(self, results: list[dict[str, Any]] | None = None) -> None:
        self._results = results if results is not None else [
            {"text": "3",   "score": 0.95, "box": [0.75, 0.40, 0.93, 0.50]},
            {"text": "输出轴", "score": 0.88, "box": [0.75, 0.50, 0.93, 0.60]},
        ]

    async def extract(self, image_url: str) -> list[dict[str, Any]]:
        return list(self._results)
