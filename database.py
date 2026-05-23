"""
database.py — 向后兼容的 re-export 入口

所有模块的 `from database import ...` 语句无需修改即可继续工作。
实现已完全迁移至 Service/Utils/databases/db/pg_history_db.py（PostgreSQL async）。

注意：这里 re-export 的函数均为 async 函数，调用方需要 await + AsyncSession 参数。
"""

from Service.Utils.databases.db import (
    init_db,
    get_db,
    engine,
    AsyncSessionLocal,
    Base,
    insert_record,
    get_recent_records_by_user,
    get_record_by_id,
    delete_record,
    clear_records_by_user,
    toggle_save_record,
    upsert_session_record,
    get_record_by_session_id,
    enforce_unsaved_cap,
)

__all__ = [
    "init_db",
    "get_db",
    "engine",
    "AsyncSessionLocal",
    "Base",
    "insert_record",
    "get_recent_records_by_user",
    "get_record_by_id",
    "delete_record",
    "clear_records_by_user",
    "toggle_save_record",
    "upsert_session_record",
    "get_record_by_session_id",
    "enforce_unsaved_cap",
]
