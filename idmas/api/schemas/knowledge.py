"""知识检索 Pydantic Schema。"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

SearchType = Literal["vector", "keyword", "graph", "hybrid"]


class KnowledgeSearchRequest(BaseModel):
    query:       str = Field(min_length=1, description="检索文本")
    top_k:       int = Field(default=5, ge=1, le=20)
    search_type: SearchType = "hybrid"


class KnowledgeResult(BaseModel):
    doc_id:  str
    title:   str
    content: str
    score:   float
    source:  str                 # vector / keyword / graph
    tags:    list[str] = Field(default_factory=list)


class KnowledgeSearchResponse(BaseModel):
    results:     list[KnowledgeResult]
    total:       int
    search_type: str
