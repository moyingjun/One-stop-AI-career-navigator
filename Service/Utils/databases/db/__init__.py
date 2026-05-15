"""
Service/Utils/databases/db/__init__.py

此包同时提供两套数据库能力：

1. SQLAlchemy 2.0 异步引擎（新架构）
   - engine, AsyncSessionLocal, Base
   - get_db()   — FastAPI 依赖注入用的异步 Session 生成器
   - init_db()  — 启动时建表（幂等）

2. SQLite history_db CRUD re-export（旧架构兼容层）
   - insert_record, get_recent_records, get_record_by_id, ...
   - create_user, get_user_by_username

调用方统一使用：
    from Service.Utils.databases.db import get_db, engine, init_db
    from Service.Utils.databases.db import insert_record

循环引用规避策略：
  - Base 定义在独立的 base.py，ORM 模型只引用 base.py，不触发本文件加载
  - history_db 的 CRUD 函数通过局部导入（函数内 import）暴露给外部
    避免模块级 from .history_db import ... 在包初始化时触发循环
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# Base 从独立地基导入，不在此处定义，防止 ORM 模型 → 本文件 → history_db 的循环
from .base import Base

from Service.Settings.config import DATABASE_URL

# ─────────────────────────────────────────────
# 异步引擎（全局单例，供 lifespan 管理生命周期）
# ─────────────────────────────────────────────
engine = create_async_engine(
    DATABASE_URL,
    echo=False,          # 生产环境关闭 SQL 日志；调试时可改为 True
    pool_pre_ping=True,  # 连接前探活，防止连接池中的失效连接
)

# ─────────────────────────────────────────────
# 异步 Session 工厂
# ─────────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # 提交后对象属性仍可访问，避免 lazy-load 异常
)


# ─────────────────────────────────────────────
# 依赖注入：异步 Session 生成器（新架构）
# ─────────────────────────────────────────────
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI 依赖注入用的异步 Session 生成器。

    用法：
        @router.get("/example")
        async def example(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ─────────────────────────────────────────────
# 数据库初始化（在 lifespan 的 yield 前调用）
# ─────────────────────────────────────────────
async def init_db() -> None:
    """
    异步创建所有已注册模型对应的数据库表（幂等，表已存在时跳过）。
    必须在所有 ORM 模型 import 之后调用，确保 Base.metadata 已收集到全部表定义。
    """
    # 延迟导入，确保模型已注册到 Base.metadata
    from Service.Utils.databases.models import user_model      # noqa: F401
    from Service.Utils.databases.models import knowledge_model  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# ─────────────────────────────────────────────
# SQLite history_db CRUD re-export（旧架构兼容层）
# 使用局部导入函数包装，避免模块级循环引用
# ─────────────────────────────────────────────

def insert_record(*args, **kwargs):
    from .history_db import insert_record as _fn
    return _fn(*args, **kwargs)


def get_recent_records(*args, **kwargs):
    from .history_db import get_recent_records as _fn
    return _fn(*args, **kwargs)


def get_recent_records_by_user(*args, **kwargs):
    from .history_db import get_recent_records_by_user as _fn
    return _fn(*args, **kwargs)


def get_record_by_id(*args, **kwargs):
    from .history_db import get_record_by_id as _fn
    return _fn(*args, **kwargs)


def delete_record(*args, **kwargs):
    from .history_db import delete_record as _fn
    return _fn(*args, **kwargs)


def clear_all_records(*args, **kwargs):
    from .history_db import clear_all_records as _fn
    return _fn(*args, **kwargs)


def toggle_save_record(*args, **kwargs):
    from .history_db import toggle_save_record as _fn
    return _fn(*args, **kwargs)


def get_saved_records(*args, **kwargs):
    from .history_db import get_saved_records as _fn
    return _fn(*args, **kwargs)


def create_user(*args, **kwargs):
    from .history_db import create_user as _fn
    return _fn(*args, **kwargs)


def get_user_by_username(*args, **kwargs):
    from .history_db import get_user_by_username as _fn
    return _fn(*args, **kwargs)


__all__ = [
    # 新架构
    "Base",
    "engine",
    "AsyncSessionLocal",
    "get_db",
    "init_db",
    # 旧架构兼容
    "insert_record",
    "get_recent_records",
    "get_recent_records_by_user",
    "get_record_by_id",
    "delete_record",
    "clear_all_records",
    "toggle_save_record",
    "get_saved_records",
    "create_user",
    "get_user_by_username",
]
