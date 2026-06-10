"""
知识库领域实体。

KnowledgeDocument ── 知识文档（向量检索单元）
Part              ── 部件实体（图谱节点）
Equipment         ── 设备实体（图谱节点）
FaultRecord       ── 故障记录实体（图谱节点，反馈闭环的核心数据）
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from uuid import UUID

from pydantic import BaseModel, Field
from enum import Enum


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class DocType(str, Enum):
    standard = "standard"   # 国家/行业标准
    manual   = "manual"     # 设备手册
    spec     = "spec"       # 企业规范
    faq      = "faq"        # 常见问题解答
    patent   = "patent"     # 专利文档


# ------------------------------------------------------------------
# KnowledgeDocument
# ------------------------------------------------------------------

class KnowledgeDocument(BaseModel):
    """
    知识文档实体，也是 Milvus 向量检索的基本单元。
    每个文档对应一个嵌入向量，通过 embedding_id 与向量库关联。
    """
    id:           UUID    = Field(default_factory=uuid.uuid4)
    title:        str
    content:      str
    doc_type:     DocType = DocType.manual
    tags:         list[str] = Field(default_factory=list)
    source:       str     = ""         # 文档来源，如 "GB/T 12345-2020"
    embedding_id: str     = ""         # Milvus 向量 ID
    created_at:   datetime = Field(default_factory=_now_utc)
    updated_at:   datetime = Field(default_factory=_now_utc)

    model_config = {"frozen": False}

    def add_tag(self, tag: str) -> None:
        if tag not in self.tags:
            self.tags.append(tag)

    def __repr__(self) -> str:
        return f"KnowledgeDocument(id={self.id}, title={self.title!r}, type={self.doc_type.value})"


# ------------------------------------------------------------------
# Part（部件——图谱节点）
# ------------------------------------------------------------------

class Part(BaseModel):
    """部件实体，在 Neo4j 知识图谱中作为节点存储。"""
    id:       UUID = Field(default_factory=uuid.uuid4)
    name:     str
    material: str  = ""   # 材质，如 "45# 钢"
    spec:     str  = ""   # 规格，如 "M12×1.25"
    tags:     list[str] = Field(default_factory=list)

    model_config = {"frozen": False}

    def __repr__(self) -> str:
        return f"Part(name={self.name!r}, material={self.material!r})"


# ------------------------------------------------------------------
# Equipment（设备——图谱节点）
# ------------------------------------------------------------------

class Equipment(BaseModel):
    """设备实体，在 Neo4j 知识图谱中作为节点存储。"""
    id:    UUID = Field(default_factory=uuid.uuid4)
    name:  str
    model: str  = ""   # 设备型号，如 "YE3-160M-4"
    manufacturer: str = ""

    model_config = {"frozen": False}

    def __repr__(self) -> str:
        return f"Equipment(name={self.name!r}, model={self.model!r})"


# ------------------------------------------------------------------
# FaultRecord（故障记录——反馈闭环核心）
# ------------------------------------------------------------------

class FaultRecord(BaseModel):
    """
    故障记录实体。
    - 来源：历史维修记录、人工审核反馈
    - 用途：训练数据、RAG 检索、故障树节点
    这是越用越准的反馈闭环的核心数据资产。
    """
    id:           UUID   = Field(default_factory=uuid.uuid4)
    code:         str                   # 故障代码，如 "F001"
    description:  str                   # 故障描述
    symptoms:     list[str] = Field(default_factory=list)   # 现象列表
    root_cause:   str  = ""             # 根本原因
    solution:     str  = ""             # 解决方案（来自实际维修记录）
    equipment_id: UUID | None = None    # 关联设备
    part_ids:     list[UUID] = Field(default_factory=list)  # 涉及部件
    verified:     bool = False          # 是否经过工程师验证
    created_at:   datetime = Field(default_factory=_now_utc)

    model_config = {"frozen": False}

    def verify(self) -> None:
        """工程师验证后标记，才可作为可信训练数据。"""
        self.verified = True

    def __repr__(self) -> str:
        return f"FaultRecord(code={self.code!r}, verified={self.verified})"
