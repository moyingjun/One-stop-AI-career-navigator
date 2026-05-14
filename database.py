import sqlite3
import json
import os
from datetime import datetime, timezone
from typing import Optional

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "history.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    # 创建用户表（多租户鉴权基础），使用 IF NOT EXISTS 保证幂等，不破坏已有数据
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
    try:
        conn.execute("ALTER TABLE history_records ADD COLUMN extra_data TEXT DEFAULT '{}'")
    except Exception:
        pass
    try:
        conn.execute("ALTER TABLE history_records ADD COLUMN chat_history TEXT DEFAULT '[]'")
    except Exception:
        pass
    try:
        conn.execute("ALTER TABLE history_records ADD COLUMN is_saved INTEGER DEFAULT 0")
    except Exception:
        pass
    # 为 history_records 表添加 user_id 列，支持多租户数据隔离（存量记录默认 NULL，向后兼容）
    try:
        conn.execute("ALTER TABLE history_records ADD COLUMN user_id INTEGER")
    except Exception:
        # 列已存在时跳过，保证幂等
        pass
    # 为 user_id 列创建索引，加速按用户查询历史记录
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_history_user_id ON history_records(user_id)"
    )
    conn.commit()
    conn.close()


def _normalize_record(row):
    record = dict(row)
    record["is_saved"] = bool(record.get("is_saved", 0))
    return record


def insert_record(category: str, user_input: str, ai_result: str, scores: dict = None, extra_data: dict = None, chat_history: list = None, is_saved: bool = False, user_id: Optional[int] = None):
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO history_records (category, user_input, ai_result, scores, extra_data, chat_history, is_saved, created_at, user_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
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
        )
    )
    record_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return record_id


def get_recent_records(limit: int = 10):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM history_records ORDER BY id DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    return [_normalize_record(row) for row in rows]


def get_record_by_id(record_id: int):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM history_records WHERE id = ?",
        (record_id,)
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


def toggle_save_record(record_id: int, is_saved: bool):
    conn = get_db()
    cursor = conn.execute(
        "UPDATE history_records SET is_saved = ? WHERE id = ?",
        (1 if is_saved else 0, record_id)
    )
    conn.commit()
    updated = cursor.rowcount > 0
    conn.close()
    return get_record_by_id(record_id) if updated else None


def get_saved_records():
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM history_records WHERE is_saved = 1 ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return [_normalize_record(row) for row in rows]


# ─────────────────────────────────────────────
# 多租户用户管理函数（阶段一：SaaS 鉴权基础）
# ─────────────────────────────────────────────

def create_user(username: str, password_hash: str, email: Optional[str] = None) -> int:
    """
    插入新用户记录，返回新用户的自增 id。

    前置条件：username 在 users 表中唯一（调用方应先检查，重复时 sqlite3 会抛出
              IntegrityError，由上层路由捕获并返回 HTTP 409）。
    后置条件：返回值为正整数 user_id，created_at 设为当前 UTC 时间。

    参数：
        username      — 用户名（TEXT UNIQUE NOT NULL）
        password_hash — bcrypt 哈希后的密码（明文绝不写入数据库）
        email         — 可选邮箱地址

    返回：
        新用户的 id（int）
    """
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
    """
    按用户名查询 users 表，返回用户信息字典或 None。

    后置条件：用户存在时返回包含所有列的 dict；用户不存在时返回 None。

    参数：
        username — 待查询的用户名

    返回：
        dict（含 id, username, password_hash, email, created_at）或 None
    """
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM users WHERE username = ?",
        (username,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_recent_records_by_user(user_id: int, limit: int = 10, **filters) -> list:
    """
    查询指定用户的历史记录，严格按 user_id 隔离，禁止越权访问。

    关键安全约束：
        - SQL 必须包含 WHERE user_id = ?，使用参数化占位符
        - 严禁通过字符串拼接构造 SQL（防止 SQL 注入，满足 Requirements 5.5, 5.6, 16.1）

    支持的可选过滤器（通过 **filters 传入）：
        category (str) — 按记录分类过滤，例如 'resume_diagnosis'、'interview_evaluate'

    参数：
        user_id — 当前已认证用户的 id（由 get_current_user() 依赖注入提供）
        limit   — 最多返回的记录数，默认 10
        **filters — 可选过滤条件（目前支持 category）

    返回：
        list[dict]，每条记录经 _normalize_record() 标准化处理
    """
    conn = get_db()

    # 基础查询：强制附加 WHERE user_id = ? 保证数据隔离
    # 所有条件均使用参数化占位符，严禁字符串拼接
    sql = "SELECT * FROM history_records WHERE user_id = ?"
    params: list = [user_id]

    # 可选过滤：按 category 精确匹配
    category = filters.get("category")
    if category is not None:
        sql += " AND category = ?"
        params.append(category)

    # 按 id 倒序（最新优先），并限制返回数量
    sql += " ORDER BY id DESC LIMIT ?"
    params.append(limit)

    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [_normalize_record(row) for row in rows]
