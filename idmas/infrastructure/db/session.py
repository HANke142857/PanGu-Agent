# =============================================================================
# 数据库会话管理
#
# 职责:
#   - 创建SQLAlchemy async engine (asyncpg)
#   - 创建async session工厂
#   - 提供FastAPI依赖注入的session获取函数
#
# 配置:
#   - DATABASE_URL: PostgreSQL连接串
#     postgresql+asyncpg://idmas:{password}@{host}:5432/idmas
#   - DB_POOL_SIZE: 连接池大小 (默认20)
#   - DB_MAX_OVERFLOW: 最大溢出 (默认10)
#   - DB_POOL_TIMEOUT: 获取连接超时 (默认30s)
#
# 方法:
#   - get_engine() -> AsyncEngine
#   - get_session_factory() -> async_sessionmaker
#   - get_db() -> AsyncGenerator[AsyncSession, None]  # FastAPI Depends
#   - init_db() -> None  # 初始化连接池
#   - close_db() -> None  # 关闭连接池
# =============================================================================
