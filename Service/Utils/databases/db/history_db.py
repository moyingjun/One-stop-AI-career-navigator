"""
Service/Utils/databases/db/history_db.py — SQLite 数据库访问层

封装所有对 history_records 和 users 表的 CRUD 操作。
上层调用方（Router、Service）通过此模块与数据库交互，不直接操作 sqlite3。
"""

import sqlite3
import json
import os
from datetime import datetime, timezone
from typing import Optional

# DB 文件路径：定位到项目根目录的 history.db
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.normpath(os.path.join(_THIS_DIR, "../../../../history.db"))


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化数据库表结构，幂等执行（服务启动时调用）。"""
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            email TEXT,
            created_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS history_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            user_input TEXT DEFAULT '',
            ai_result TEXT DEFAULT '',
            scores TEXT DEFAULT '{}',
            extra_data TEXT DEFAULT '{}',
            chat_history TEXT DEFAULT '[]',
            is_saved INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)
    # 幂等 ALTER TABLE：列已存在时跳过
    for alter_sql in [
        "ALTER TABLE history_records ADD COLUMN extra_data TEXT DEFAULT '{}'",
        "ALTER TABLE history_records ADD COLUMN chat_history TEXT DEFAULT '[]'",
        "ALTER TABLE history_records ADD COLUMN is_saved INTEGER DEFAULT 0",
        "ALTER TABLE history_records ADD COLUMN user_id INTEGER",
    ]:
        try:
            conn.execute(alter_sql)
        except Exception:
            pass
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_history_user_id ON history_records(user_id)"
    )
    conn.commit()
    conn.close()


def _normalize_record(row) -> dict:
    record = dict(row)
    record["is_saved"] = bool(record.get("is_saved", 0))
    return record


# ─────────────────────────────────────────────
# 历史记录 CRUD
# ─────────────────────────────────────────────

def insert_record(
    category: str,
    user_input: str,
    ai_result: str,
    scores: dict = None,
    extra_data: dict = None,
    chat_history: list = None,
    is_saved: bool = False,
    user_id: Optional[int] = None,
) -> int:
    """插入一条历史记录，返回新记录的自增 id。"""
    conn = get_db()
    cursor = conn.execute(
        """INSERT INTO history_records
           (category, user_input, ai_result, scores, extra_data, chat_history, is_saved, created_at, user_id)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            category,
            user_input[:2000],
            ai_result[:5000],
            json.dumps(scores or {}, ensure_ascii=False),
            json.dumps(extra_data or {}, ensure_ascii=False),
            json.dumps(chat_history or [], ensure_ascii=False),
            1 if is_saved else 0,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            user_id,
        ),
    )
    record_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return record_id


def get_recent_records(limit: int = 10) -> list:
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM history_records ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [_normalize_record(row) for row in rows]


def get_recent_records_by_user(user_id: int, limit: int = 10, **filters) -> list:
    """按 user_id 隔离查询历史记录（多租户安全约束）。"""
    conn = get_db()
    sql = "SELECT * FROM history_records WHERE user_id = ?"
    params: list = [user_id]
    category = filters.get("category")
    if category is not None:
        sql += " AND category = ?"
        params.append(category)
    sql += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [_normalize_record(row) for row in rows]


def get_record_by_id(record_id: int) -> Optional[dict]:
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM history_records WHERE id = ?", (record_id,)
    ).fetchone()
    conn.close()
    return _normalize_record(row) if row else None


def delete_record(record_id: int) -> bool:
    conn = get_db()
    cursor = conn.execute("DELETE FROM history_records WHERE id = ?", (record_id,))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted


def clear_all_records() -> int:
    conn = get_db()
    cursor = conn.execute("DELETE FROM history_records")
    deleted_count = cursor.rowcount
    try:
        conn.execute("DELETE FROM sqlite_sequence WHERE name = 'history_records'")
    except Exception:
        pass
    conn.commit()
    conn.close()
    return deleted_count


def clear_records_by_user(user_id: int) -> int:
    """
    清空指定用户的所有历史记录（多租户安全版本）。

    🚨 铁律：只删除 user_id = :user_id 的记录，绝不清空全表。
    """
    conn = get_db()
    cursor = conn.execute(
        "DELETE FROM history_records WHERE user_id = ?", (user_id,)
    )
    deleted_count = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted_count


def toggle_save_record(record_id: int, is_saved: bool) -> Optional[dict]:
    conn = get_db()
    cursor = conn.execute(
        "UPDATE history_records SET is_saved = ? WHERE id = ?",
        (1 if is_saved else 0, record_id),
    )
    conn.commit()
    updated = cursor.rowcount > 0
    conn.close()
    return get_record_by_id(record_id) if updated else None


def get_saved_records() -> list:
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM history_records WHERE is_saved = 1 ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return [_normalize_record(row) for row in rows]


# ─────────────────────────────────────────────
# 用户管理 CRUD
# ─────────────────────────────────────────────

def create_user(username: str, password_hash: str, email: Optional[str] = None) -> int:
    """插入新用户，返回新用户 id。用户名重复时由调用方捕获 IntegrityError。"""
    conn = get_db()
    created_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    cursor = conn.execute(
        "INSERT INTO users (username, password_hash, email, created_at) VALUES (?, ?, ?, ?)",
        (username, password_hash, email, created_at),
    )
    new_user_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return new_user_id


def get_user_by_username(username: str) -> Optional[dict]:
    """按用户名查询，返回用户字典或 None。"""
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM users WHERE username = ?", (username,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None
