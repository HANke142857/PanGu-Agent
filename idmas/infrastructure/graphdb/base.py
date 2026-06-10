"""
知识图谱抽象（RAG 的关系/图谱通道）。

    BaseGraphClient     : 抽象接口
    InMemoryGraphClient : 测试/开发用，进程内图（无需 Neo4j）
    Neo4jGraphClient    : 生产实现，见 neo4j_client.py（需 Neo4j）

图谱模型（参见技术设计 3.4）::

    节点: Part, Equipment, FaultRecord
    关系: Part -INSTALLED_IN-> Equipment -HAS_FAULT-> FaultRecord

query_label_relations(label_name) 返回以该部件为中心的一跳关系链，
供 Knowledge Agent 拼接为结构化上下文。
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel, Field


class GraphRelations(BaseModel):
    """以某部件为中心的关系视图。"""

    part:       str
    material:   str = ""
    equipment:  list[str] = Field(default_factory=list)   # 安装于哪些设备
    faults:     list[str] = Field(default_factory=list)   # 历史故障描述

    def as_text(self) -> str:
        parts = []
        if self.material:
            parts.append(f"材质 {self.material}")
        if self.equipment:
            parts.append("安装于 " + "、".join(self.equipment))
        if self.faults:
            parts.append("历史故障：" + "；".join(self.faults))
        return "；".join(parts)


class BaseGraphClient(ABC):
    @abstractmethod
    async def query_label_relations(self, label_name: str) -> GraphRelations | None:
        """查询部件的一跳关系链；无此节点返回 None。"""
        ...

    @abstractmethod
    async def upsert_part(self, name: str, material: str = "") -> None:
        ...

    @abstractmethod
    async def link_part_to_equipment(self, part: str, equipment: str) -> None:
        ...

    @abstractmethod
    async def add_fault(self, equipment: str, description: str) -> None:
        ...

    async def health_check(self) -> bool:
        return True


class InMemoryGraphClient(BaseGraphClient):
    """进程内知识图谱。"""

    def __init__(self) -> None:
        self._material: dict[str, str] = {}
        self._part_equipment: dict[str, list[str]] = {}     # part -> [equipment]
        self._equipment_faults: dict[str, list[str]] = {}   # equipment -> [fault desc]

    async def upsert_part(self, name: str, material: str = "") -> None:
        if material:
            self._material[name] = material
        self._part_equipment.setdefault(name, [])

    async def link_part_to_equipment(self, part: str, equipment: str) -> None:
        self._part_equipment.setdefault(part, [])
        if equipment not in self._part_equipment[part]:
            self._part_equipment[part].append(equipment)

    async def add_fault(self, equipment: str, description: str) -> None:
        bucket = self._equipment_faults.setdefault(equipment, [])
        if description not in bucket:
            bucket.append(description)

    def seed(self, part: str, material: str, equipment: str, faults: list[str]) -> None:
        """同步种子写入，供图构建（同步上下文）预置图谱使用。"""
        if material:
            self._material[part] = material
        bucket = self._part_equipment.setdefault(part, [])
        if equipment and equipment not in bucket:
            bucket.append(equipment)
        for f in faults:
            fb = self._equipment_faults.setdefault(equipment, [])
            if f not in fb:
                fb.append(f)

    async def query_label_relations(self, label_name: str) -> GraphRelations | None:
        if label_name not in self._part_equipment and label_name not in self._material:
            return None
        equipment = self._part_equipment.get(label_name, [])
        faults: list[str] = []
        for eq in equipment:
            faults.extend(self._equipment_faults.get(eq, []))
        return GraphRelations(
            part=label_name,
            material=self._material.get(label_name, ""),
            equipment=equipment,
            faults=faults,
        )
