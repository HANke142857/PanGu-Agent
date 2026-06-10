"""
知识库仓储接口（Repository Interface）。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from idmas.domain.knowledge.entities import Equipment, FaultRecord, KnowledgeDocument, Part


class KnowledgeRepository(ABC):
    """知识库仓储抽象接口（向量 + 图谱 + 关系型的统一门面）。"""

    # ------------------------------------------------------------------
    # 文档检索
    # ------------------------------------------------------------------

    @abstractmethod
    async def search_by_vector(
        self,
        embedding: list[float],
        top_k: int = 5,
    ) -> list[KnowledgeDocument]:
        """向量相似度检索（Milvus）。"""
        ...

    @abstractmethod
    async def search_by_keyword(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[KnowledgeDocument]:
        """关键词全文检索（Elasticsearch）。"""
        ...

    @abstractmethod
    async def save_document(self, doc: KnowledgeDocument) -> KnowledgeDocument:
        ...

    # ------------------------------------------------------------------
    # 图谱检索（Neo4j）
    # ------------------------------------------------------------------

    @abstractmethod
    async def get_part_by_name(self, name: str) -> Part | None:
        ...

    @abstractmethod
    async def get_equipment_relations(self, part_id: UUID) -> list[Equipment]:
        """获取部件所属的设备列表（图谱关系）。"""
        ...

    @abstractmethod
    async def get_fault_records(self, equipment_id: UUID) -> list[FaultRecord]:
        """获取设备的历史故障记录。"""
        ...

    @abstractmethod
    async def save_fault_record(self, record: FaultRecord) -> FaultRecord:
        """保存故障记录（反馈闭环写入口）。"""
        ...
