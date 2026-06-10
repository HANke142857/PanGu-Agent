"""
LangChain Tools 工厂。

把基础设施客户端包装为 LangChain StructuredTool，供需要 tool-calling 的 Agent 使用。
工厂式绑定（注入客户端），不在模块层硬编码，便于测试替换 Fake。
"""
from __future__ import annotations

from typing import Any

from langchain_core.tools import StructuredTool

from idmas.infrastructure.ocr.base import BaseOCRClient
from idmas.infrastructure.vectordb.base import BaseEmbedder, BaseVectorClient


def make_knowledge_search_tool(
    vector_client: BaseVectorClient,
    embedder: BaseEmbedder,
    collection: str,
    top_k: int = 5,
) -> StructuredTool:
    """向量检索企业知识库的 tool。"""

    async def search_knowledge_base(query: str) -> list[dict[str, Any]]:
        embedding = embedder.embed_one(query)
        hits = await vector_client.search(collection, embedding, top_k=top_k)
        return [{"id": h.id, "score": round(h.score, 4), **h.metadata} for h in hits]

    return StructuredTool.from_function(
        coroutine=search_knowledge_base,
        name="search_knowledge_base",
        description="按文本向量检索企业知识库，返回相关条目。",
    )


def make_ocr_tool(ocr_client: BaseOCRClient) -> StructuredTool:
    """PaddleOCR 提取文字/坐标的 tool。"""

    async def ocr_extract_labels(image_url: str) -> list[dict[str, Any]]:
        return await ocr_client.extract(image_url)

    return StructuredTool.from_function(
        coroutine=ocr_extract_labels,
        name="ocr_extract_labels",
        description="对图纸图片做 OCR，返回 [{text, score, box}]。",
    )
