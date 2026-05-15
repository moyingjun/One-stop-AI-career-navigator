"""
database.py — 向后兼容的 re-export 入口

实际实现已迁移至 Service/Utils/databases/db/history_db.py。
此文件保留是为了让所有现有的 `from database import ...` 语句无需修改即可继续工作。

新代码请直接从新路径导入：
    from Service.Utils.databases.db import insert_record, get_record_by_id, ...
"""

from Service.Utils.databases.db import (
    init_db,
    get_db,
    insert_record,
    get_recent_records,
    get_recent_records_by_user,
    get_record_by_id,
    delete_record,
    clear_all_records,
    toggle_save_record,
    get_saved_records,
    create_user,
    get_user_by_username,
)

__all__ = [
    "init_db",
    "get_db",
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
