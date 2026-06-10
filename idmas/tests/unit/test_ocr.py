"""
OCR 客户端单元测试。
"""

from __future__ import annotations

import pytest

from idmas.infrastructure.ocr.base import FakeOCRClient
from idmas.infrastructure.ocr.paddle_client import PaddleOCRClient


class TestFakeOCR:
    async def test_default_results(self):
        ocr = FakeOCRClient()
        out = await ocr.extract("memory://x.png")
        assert [w["text"] for w in out] == ["3", "输出轴"]
        assert all({"text", "score", "box"} <= w.keys() for w in out)

    async def test_custom_results(self):
        ocr = FakeOCRClient(results=[{"text": "A1", "score": 0.9, "box": [0, 0, 1, 1]}])
        out = await ocr.extract("x")
        assert out[0]["text"] == "A1"

    async def test_health(self):
        assert await FakeOCRClient().health_check() is True


class TestPaddleNormalize:
    def test_results_shape(self):
        payload = {"results": [
            {"text": "3", "score": 0.95, "box": [1, 2, 3, 4]},
            {"text": "轴", "score": 0.8},
        ]}
        out = PaddleOCRClient._normalize(payload)
        assert out[0] == {"text": "3", "score": 0.95, "box": [1, 2, 3, 4]}
        assert out[1]["box"] == []          # 缺失补默认

    def test_parallel_arrays_shape(self):
        payload = {"texts": ["a", "b"], "scores": [0.9, 0.7], "boxes": [[0], [1]]}
        out = PaddleOCRClient._normalize(payload)
        assert [w["text"] for w in out] == ["a", "b"]
        assert out[1]["score"] == 0.7

    def test_empty_payload(self):
        assert PaddleOCRClient._normalize({}) == []


class TestPaddleConstruction:
    def test_strip_trailing_slash(self):
        c = PaddleOCRClient("http://localhost:8100/", timeout=10)
        assert c._url == "http://localhost:8100"
        assert c._timeout == 10


class TestOCRRetryNodeWiring:
    async def test_injected_client_used(self):
        from idmas.agents.vision.nodes import make_ocr_retry_node

        ocr = FakeOCRClient(results=[{"text": "Z9", "score": 0.7, "box": []}])
        node = await make_ocr_retry_node(ocr)
        out = await node({"image_url": "x", "retry_count": 0})
        assert out["ocr_results"][0]["text"] == "Z9"
        assert out["retry_count"] == 1

    async def test_none_falls_back_to_fake(self):
        from idmas.agents.vision.nodes import make_ocr_retry_node

        node = await make_ocr_retry_node(None)
        out = await node({"image_url": "x"})
        assert [w["text"] for w in out["ocr_results"]] == ["3", "输出轴"]

    async def test_failure_degrades_to_empty(self):
        from idmas.agents.vision.nodes import make_ocr_retry_node

        class _BoomOCR(FakeOCRClient):
            async def extract(self, image_url):  # noqa: ANN001
                raise RuntimeError("ocr down")

        node = await make_ocr_retry_node(_BoomOCR())
        out = await node({"image_url": "x", "retry_count": 1})
        assert out["ocr_results"] == []
        assert out["retry_count"] == 2
