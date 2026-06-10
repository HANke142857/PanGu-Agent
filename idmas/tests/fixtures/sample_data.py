"""
测试样本数据与构造器（供各测试复用）。
"""

from __future__ import annotations

import io
import uuid

# 1×1 PNG（最小合法 PNG 字节）
SAMPLE_PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)

SAMPLE_VISION_RESULT = {
    "success": True,
    "labels": [
        {"label_id": "1", "name": "轴承座", "confidence": 0.92,
         "bounding_box": {"x": 0.1, "y": 0.1, "width": 0.2, "height": 0.2},
         "needs_review": False},
        {"label_id": "2", "name": "输出轴", "confidence": 0.55,
         "bounding_box": {"x": 0.5, "y": 0.4, "width": 0.2, "height": 0.2},
         "needs_review": True},
    ],
}

SAMPLE_OCR_RESULT = [
    {"text": "3", "score": 0.95, "box": [0.75, 0.40, 0.93, 0.50]},
]

SAMPLE_KNOWLEDGE_DOCS = [
    {"name": "轴承座", "content": "支撑旋转轴的固定部件。"},
    {"name": "齿轮箱", "content": "变速传动装置。"},
]


def upload_file(filename: str = "drawing.png", content: bytes | None = None,
                content_type: str = "image/png") -> dict:
    """构造 TestClient.post(files=...) 用的 files 参数。"""
    return {"file": (filename, io.BytesIO(content or SAMPLE_PNG_BYTES), content_type)}


def new_uuid_str() -> str:
    return str(uuid.uuid4())
