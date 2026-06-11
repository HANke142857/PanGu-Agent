"""
图纸仓储接口（Repository Interface）。
只定义抽象契约，具体实现在 infrastructure/db 层。
依赖倒置：domain 不知道 PostgreSQL 的存在。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from idmas.domain.drawing.entities import Drawing, DrawingLabel


class DrawingRepository(ABC):
    """图纸仓储抽象接口。"""

    @abstractmethod
    async def get_by_id(self, drawing_id: UUID) -> Drawing | None:
        """按 ID 获取图纸，不存在返回 None。"""
        ...

    @abstractmethod
    async def save(self, drawing: Drawing) -> Drawing:
        """新增或更新图纸（upsert 语义）。返回持久化后的对象。"""
        ...

    @abstractmethod
    async def list_by_user(
        self,
        user_id: UUID,
        offset: int = 0,
        limit: int  = 20,
    ) -> list[Drawing]:
        """分页查询指定用户上传的图纸列表。"""
        ...

    @abstractmethod
    async def search_by_title(self, keyword: str, limit: int = 20) -> list[Drawing]:
        """按标题关键词模糊检索图纸。"""
        ...

    @abstractmethod
    async def list_all(self, offset: int = 0, limit: int = 20) -> list[Drawing]:
        """分页查询全部图纸（不限用户），按创建时间倒序。"""
        ...

    @abstractmethod
    async def count_all(self) -> int:
        """统计图纸总数（用于分页 total）。"""
        ...

    @abstractmethod
    async def delete(self, drawing_id: UUID) -> None:
        """逻辑删除图纸（lifecycle_state → obsolete）。"""
        ...

    # ------------------------------------------------------------------
    # 标号相关
    # ------------------------------------------------------------------

    @abstractmethod
    async def get_labels(self, drawing_id: UUID) -> list[DrawingLabel]:
        """获取指定图纸的全部标号。"""
        ...

    @abstractmethod
    async def save_labels(self, labels: list[DrawingLabel]) -> None:
        """批量保存标号（新增或覆盖）。"""
        ...

    @abstractmethod
    async def update_label(self, label: DrawingLabel) -> None:
        """更新单个标号（人工修正场景）。"""
        ...
