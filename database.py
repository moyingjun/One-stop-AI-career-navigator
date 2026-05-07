import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "history.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
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
    conn.commit()
    conn.close()


def _normalize_record(row):
    record = dict(row)
    record["is_saved"] = bool(record.get("is_saved", 0))
    return record


def insert_record(category: str, user_input: str, ai_result: str, scores: dict = None, extra_data: dict = None, chat_history: list = None, is_saved: bool = False):
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO history_records (category, user_input, ai_result, scores, extra_data, chat_history, is_saved, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            category,
            user_input[:2000],
            ai_result[:5000],
            json.dumps(scores or {}, ensure_ascii=False),
            json.dumps(extra_data or {}, ensure_ascii=False),
            json.dumps(chat_history or [], ensure_ascii=False),
            1 if is_saved else 0,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
