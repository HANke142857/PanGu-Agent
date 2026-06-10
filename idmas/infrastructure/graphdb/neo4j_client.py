"""
Neo4j 知识图谱客户端（生产）。

实现 BaseGraphClient。neo4j 异步驱动惰性导入——仅实例化并访问时才需要安装，
测试用 InMemoryGraphClient 不受影响。

图谱模型::

    (:Part {name, material}) -[:INSTALLED_IN]-> (:Equipment {name}) -[:HAS_FAULT]-> (:Fault {description})

降级：Neo4j 不可用时图谱通道跳过，不影响向量/关键词检索。
"""

from __future__ import annotations

import logging

from idmas.infrastructure.graphdb.base import BaseGraphClient, GraphRelations

logger = logging.getLogger(__name__)


class Neo4jGraphClient(BaseGraphClient):
    def __init__(self, uri: str, user: str, password: str) -> None:
        self._uri = uri
        self._auth = (user, password)
        self._driver = None

    def _get_driver(self):
        if self._driver is None:
            from neo4j import AsyncGraphDatabase  # 惰性导入

            self._driver = AsyncGraphDatabase.driver(self._uri, auth=self._auth)
        return self._driver

    async def upsert_part(self, name: str, material: str = "") -> None:
        driver = self._get_driver()
        async with driver.session() as session:
            await session.run(
                "MERGE (p:Part {name: $name}) SET p.material = $material",
                name=name, material=material,
            )

    async def link_part_to_equipment(self, part: str, equipment: str) -> None:
        driver = self._get_driver()
        async with driver.session() as session:
            await session.run(
                """
                MERGE (p:Part {name: $part})
                MERGE (e:Equipment {name: $equipment})
                MERGE (p)-[:INSTALLED_IN]->(e)
                """,
                part=part, equipment=equipment,
            )

    async def add_fault(self, equipment: str, description: str) -> None:
        driver = self._get_driver()
        async with driver.session() as session:
            await session.run(
                """
                MERGE (e:Equipment {name: $equipment})
                MERGE (f:Fault {description: $description})
                MERGE (e)-[:HAS_FAULT]->(f)
                """,
                equipment=equipment, description=description,
            )

    async def query_label_relations(self, label_name: str) -> GraphRelations | None:
        driver = self._get_driver()
        async with driver.session() as session:
            result = await session.run(
                """
                MATCH (p:Part {name: $name})
                OPTIONAL MATCH (p)-[:INSTALLED_IN]->(e:Equipment)
                OPTIONAL MATCH (e)-[:HAS_FAULT]->(f:Fault)
                RETURN p.material AS material,
                       collect(DISTINCT e.name) AS equipment,
                       collect(DISTINCT f.description) AS faults
                """,
                name=label_name,
            )
            record = await result.single()
            if record is None:
                return None
            equipment = [e for e in (record["equipment"] or []) if e]
            faults = [f for f in (record["faults"] or []) if f]
            return GraphRelations(
                part=label_name,
                material=record["material"] or "",
                equipment=equipment,
                faults=faults,
            )

    async def health_check(self) -> bool:
        try:
            driver = self._get_driver()
            async with driver.session() as session:
                await session.run("RETURN 1")
            return True
        except Exception:  # noqa: BLE001
            return False

    async def close(self) -> None:
        if self._driver is not None:
            await self._driver.close()
            self._driver = None
