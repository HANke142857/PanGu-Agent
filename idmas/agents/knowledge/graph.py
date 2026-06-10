"""
Knowledge SubGraph 构建。

RAG 三路检索可分别注入实现，默认走内存（预置 KB），生产按 settings 选择：
  - 向量：VECTOR_BACKEND=memory|milvus
  - 关键词：SEARCH_BACKEND=memory|es
  - 图谱：GRAPH_BACKEND=memory|neo4j

用法::

    graph  = build_knowledge_graph()                 # 默认内存三路
    result = await graph.ainvoke({"query": "...", "labels": [...]})
"""
from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from idmas.agents.knowledge.nodes import (
    knowledge_finalize_node,
    make_graph_query_node,
    make_keyword_search_node,
    make_vector_search_node,
    merge_context_node,
    rag_generate_node,
)
from idmas.agents.knowledge.state import KnowledgeState
from idmas.config.settings import get_settings
from idmas.infrastructure.graphdb.base import BaseGraphClient, InMemoryGraphClient
from idmas.infrastructure.search.base import (
    KNOWLEDGE_INDEX,
    BaseSearchClient,
    InMemorySearchClient,
)
from idmas.infrastructure.vectordb.base import (
    BaseEmbedder,
    BaseVectorClient,
    HashingEmbedder,
    InMemoryVectorClient,
    VectorItem,
)
from idmas.infrastructure.vectordb.milvus_client import KNOWLEDGE_COLLECTION, MilvusVectorClient

# 预置知识库（内存后端的种子；生产由灌库流程写入各中间件）
DEFAULT_KNOWLEDGE: dict[str, str] = {
    "轴承座":  "支撑旋转轴的固定部件，材料通常为铸铁或铸钢，需定期润滑。",
    "齿轮箱":  "变速传动装置，由齿轮系组成，需检查油位和密封性。",
    "输出轴":  "将动力传递到外部负载的轴，注意轴端密封和联轴器对中精度。",
    "轴承":    "减少摩擦的支撑元件，包括滚动轴承和滑动轴承，需关注磨损和温升。",
    "密封圈":  "防止泄漏的密封元件，使用寿命受温度和压力影响。",
}

# 部件 → (材质, 设备, 故障)，内存图谱种子
DEFAULT_GRAPH: dict[str, tuple[str, str, list[str]]] = {
    "轴承座": ("HT250 铸铁", "减速器", ["F001 轴承座异响，根因润滑不足"]),
    "齿轮箱": ("45# 钢", "传动总成", ["F012 齿轮箱漏油，密封圈老化"]),
    "输出轴": ("40Cr 合金钢", "减速器", []),
}


def _seeded_vector_client(embedder: BaseEmbedder) -> InMemoryVectorClient:
    client = InMemoryVectorClient()
    client.add(KNOWLEDGE_COLLECTION, [
        VectorItem(id=name, embedding=embedder.embed_one(name),
                   metadata={"text": name, "knowledge": desc})
        for name, desc in DEFAULT_KNOWLEDGE.items()
    ])
    return client


def _seeded_search_client() -> InMemorySearchClient:
    client = InMemorySearchClient()
    for name, desc in DEFAULT_KNOWLEDGE.items():
        client.add(KNOWLEDGE_INDEX, name, text=name, metadata={"knowledge": desc})
    return client


def _seeded_graph_client() -> InMemoryGraphClient:
    client = InMemoryGraphClient()
    for part, (material, equipment, faults) in DEFAULT_GRAPH.items():
        client.seed(part, material, equipment, faults)
    return client


def build_knowledge_graph(
    vector_client: BaseVectorClient | None = None,
    embedder: BaseEmbedder | None = None,
    search_client: BaseSearchClient | None = None,
    graph_client: BaseGraphClient | None = None,
):
    settings = get_settings()
    embedder = embedder or HashingEmbedder(dim=settings.EMBEDDING_DIM)

    # ── 向量通道 ──
    if vector_client is None:
        if settings.VECTOR_BACKEND == "milvus":
            vector_client = MilvusVectorClient(
                host=settings.MILVUS_HOST, port=settings.MILVUS_PORT,
                dim=settings.EMBEDDING_DIM, collection=KNOWLEDGE_COLLECTION,
            )
        else:
            vector_client = _seeded_vector_client(embedder)

    # ── 关键词通道 ──
    if search_client is None:
        if settings.SEARCH_BACKEND == "es":
            from idmas.infrastructure.search.es_client import ESSearchClient
            search_client = ESSearchClient(settings.ES_URL)
        else:
            search_client = _seeded_search_client()

    # ── 图谱通道 ──
    if graph_client is None:
        if settings.GRAPH_BACKEND == "neo4j":
            from idmas.infrastructure.graphdb.neo4j_client import Neo4jGraphClient
            graph_client = Neo4jGraphClient(
                settings.NEO4J_URI, settings.NEO4J_USER, settings.NEO4J_PASSWORD
            )
        else:
            graph_client = _seeded_graph_client()

    vector_search_node = make_vector_search_node(vector_client, embedder, collection=KNOWLEDGE_COLLECTION)
    keyword_search_node = make_keyword_search_node(search_client, index=KNOWLEDGE_INDEX)
    graph_query_node = make_graph_query_node(graph_client)

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
