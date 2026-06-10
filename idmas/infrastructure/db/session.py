"""
数据库会话管理。

职责：
  - 按配置创建 SQLAlchemy async engine（asyncpg）
  - 提供 async_sessionmaker 工厂
  - 提供 FastAPI 依赖注入用的 get_db()
  - init_db / close_db 管理连接池生命周期

引擎以模块级单例缓存；测试可用 create_engine_from_url() 自带 SQLite 引擎，
不触碰全局单例。
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from idmas.config.settings import get_settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def create_engine_from_url(url: str, **kwargs) -> AsyncEngine:
    """从连接串构造异步引擎。SQLite 不支持连接池参数，自动跳过。"""
    if url.startswith("sqlite"):
        return create_async_engine(url, future=True, **kwargs)
    settings = get_settings()
    return create_async_engine(
        url,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_timeout=settings.DB_POOL_TIMEOUT,
        pool_pre_ping=True,
        future=True,
        **kwargs,
    )


def get_engine() -> AsyncEngine:
    """获取全局引擎单例（首次调用按 settings.DATABASE_URL 创建）。"""
    global _engine
    if _engine is None:
        _engine = create_engine_from_url(get_settings().DATABASE_URL)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """获取全局 session 工厂单例。"""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            expire_on_commit=False,
            class_=AsyncSession,
        )
    return _session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖：产出一个请求作用域的会话，请求结束自动关闭。"""
    factory = get_session_factory()
    async with factory() as session:
        yield session


async def init_db() -> None:
    """初始化连接池（应用启动时调用）。仅做一次握手以触发连接建立。"""
    engine = get_engine()
    async with engine.connect():
        pass


async def close_db() -> None:
    """关闭连接池（应用退出时调用）。"""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None
