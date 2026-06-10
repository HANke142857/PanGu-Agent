"""
Knowledge SubGraph 构建。

向量检索可注入实现：
  - 默认（VECTOR_BACKEND=memory）：内存向量库 + 预置 KB，零依赖、可复现
  - 生产（VECTOR_BACKEND=milvus）：MilvusVectorClient（知识需预先灌入 Milvus）

用法::

    graph  = build_knowledge_graph()                 # 默认内存 KB
    result = await graph.ainvoke({"query": "...", "labels": [...]})

    # 注入自定义向量库
    graph  = build_knowledge_graph(vector_client=my_client, embedder=my_embedder)
"""
from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from idmas.agents.knowledge.nodes import (
    graph_query_node,
    keyword_search_node,
    knowledge_finalize_node,
    make_vector_search_node,
    merge_context_node,
    rag_generate_node,
)
from idmas.agents.knowledge.state import KnowledgeState
from idmas.config.settings import get_settings
from idmas.infrastructure.vectordb.base import (
    BaseEmbedder,
    BaseVectorClient,
    HashingEmbedder,
    InMemoryVectorClient,
    VectorItem,
)
from idmas.infrastructure.vectordb.milvus_client import KNOWLEDGE_COLLECTION, MilvusVectorClient

# 预置知识库（内存后端的种子数据；生产由灌库流程写入 Milvus）
DEFAULT_KNOWLEDGE: dict[str, str] = {
    "轴承座":  "支撑旋转轴的固定部件，材料通常为铸铁或铸钢，需定期润滑。",
    "齿轮箱":  "变速传动装置，由齿轮系组成，需检查油位和密封性。",
    "输出轴":  "将动力传递到外部负载的轴，注意轴端密封和联轴器对中精度。",
    "轴承":    "减少摩擦的支撑元件，包括滚动轴承和滑动轴承，需关注磨损和温升。",
    "密封圈":  "防止泄漏的密封元件，使用寿命受温度和压力影响。",
}


def _build_seeded_memory_client(embedder: BaseEmbedder) -> InMemoryVectorClient:
    """构造并用预置 KB 种子填充内存向量库。"""
    client = InMemoryVectorClient()
    items = [
        VectorItem(
            id=name,
            embedding=embedder.embed_one(name),
            metadata={"text": name, "knowledge": desc},
        )
        for name, desc in DEFAULT_KNOWLEDGE.items()
    ]
    client.add(KNOWLEDGE_COLLECTION, items)
    return client


def build_knowledge_graph(
    vector_client: BaseVectorClient | None = None,
    embedder: BaseEmbedder | None = None,
):
    settings = get_settings()
    embedder = embedder or HashingEmbedder(dim=settings.EMBEDDING_DIM)

    if vector_client is None:
        if settings.VECTOR_BACKEND == "milvus":
            vector_client = MilvusVectorClient(
                host=settings.MILVUS_HOST,
                port=settings.MILVUS_PORT,
                dim=settings.EMBEDDING_DIM,
                collection=KNOWLEDGE_COLLECTION,
            )
        else:
            vector_client = _build_seeded_memory_client(embedder)

    vector_search_node = make_vector_search_node(
        vector_client, embedder, collection=KNOWLEDGE_COLLECTION
    )

    builder = StateGraph(KnowledgeState)
    builder.add_node("vector_search",   vector_search_node)
    builder.add_node("keyword_search",  keyword_search_node)
    builder.add_node("graph_query",     graph_query_node)
    builder.add_node("merge_context",   merge_context_node)
    builder.add_node("rag_generate",    rag_generate_node)
    builder.add_node("finalize",        knowledge_finalize_node)
    builder.add_edge(START,             "vector_search")
    builder.add_edge("vector_search",   "keyword_search")
    builder.add_edge("keyword_search",  "graph_query")
    builder.add_edge("graph_query",     "merge_context")
    builder.add_edge("merge_context",   "rag_generate")
    builder.add_edge("rag_generate",    "finalize")
    builder.add_edge("finalize",        END)
    return builder.compile()
