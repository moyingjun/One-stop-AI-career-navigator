"""
Service/Utils/databases/db/__init__.py — PostgreSQL 数据库层唯一入口

提供：
  1. SQLAlchemy 2.0 异步引擎（PostgreSQL）
     - engine, AsyncSessionLocal, Base
     - get_db()   — FastAPI 依赖注入用的异步 Session 生成器
     - init_db()  — 启动时建表（幂等）

  2. 历史记录 CRUD 封装（PostgreSQL async 版本）
     - 所有函数均为 async，接受 AsyncSession 参数
     - 返回格式与旧 SQLite 版本兼容（dict）

旧 SQLite 实现（history_db.py）已重命名为 legacy_sqlite_history_db.py，
不再被主路径 import，保留为备份。
"""

from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from .base import Base
from Service.Settings.config import DATABASE_URL

# ─────────────────────────────────────────────
# 异步引擎（全局单例，供 lifespan 管理生命周期）
# ─────────────────────────────────────────────
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
)

# ─────────────────────────────────────────────
# 异步 Session 工厂
# ─────────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ─────────────────────────────────────────────
# 依赖注入：异步 Session 生成器
# ─────────────────────────────────────────────
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ─────────────────────────────────────────────
# 数据库初始化（lifespan 中调用）
# ─────────────────────────────────────────────
async def init_db() -> None:
    """
    异步创建所有已注册模型对应的数据库表（幂等，表已存在时跳过）。
    """
    # 延迟导入确保所有 ORM 模型已注册到 Base.metadata
    from Service.Utils.databases.models import user_model       # noqa: F401
    from Service.Utils.databases.models import knowledge_model  # noqa: F401
    from Service.Utils.databases.models import history_model    # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# ─────────────────────────────────────────────
# PostgreSQL 历史记录 CRUD（async，直接暴露）
# ─────────────────────────────────────────────
# 这些是 async 函数，调用方需要 await，且需要传入 AsyncSession。
# Router 层通过 Depends(get_db) 获取 session 后直接调用。

from .pg_history_db import (  # noqa: E402
    insert_record,
    get_recent_records_by_user,
    get_record_by_id,
    delete_record,
    clear_records_by_user,
    toggle_save_record,
    count_saved_records_by_user,
    upsert_session_record,
    get_record_by_session_id,
    enforce_unsaved_cap,
)


__all__ = [
    # 新架构：PostgreSQL 异步引擎
    "Base",
    "engine",
    "AsyncSessionLocal",
    "get_db",
    "init_db",
    # PostgreSQL 历史记录 CRUD（async）
    "insert_record",
    "get_recent_records_by_user",
    "get_record_by_id",
    "delete_record",
    "clear_records_by_user",
    "toggle_save_record",
    "count_saved_records_by_user",
    "upsert_session_record",
    "get_record_by_session_id",
    "enforce_unsaved_cap",
]
