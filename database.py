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
    conn.commit()
    conn.close()


def insert_record(category: str, user_input: str, ai_result: str, scores: dict = None, extra_data: dict = None, chat_history: list = None):
    conn = get_db()
    conn.execute(
        "INSERT INTO history_records (category, user_input, ai_result, scores, extra_data, chat_history, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (category, user_input[:2000], ai_result[:5000], json.dumps(scores or {}, ensure_ascii=False), json.dumps(extra_data or {}, ensure_ascii=False), json.dumps(chat_history or [], ensure_ascii=False), datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()
    conn.close()


def get_recent_records(limit: int = 10):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM history_records ORDER BY id DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_record_by_id(record_id: int):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM history_records WHERE id = ?",
        (record_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None
