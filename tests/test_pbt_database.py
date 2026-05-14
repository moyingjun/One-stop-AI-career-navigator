"""
Property-based tests for get_recent_records_by_user() — Property 1: 用户数据隔离不变量.

**Validates: Requirements 4.3, 4.4**

Property: For any valid user_id, all records returned by get_recent_records_by_user()
must have a user_id field equal to the input value. Records belonging to other users
must never appear in the result set.
"""

import sys
import os
import sqlite3
import tempfile
import json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import patch
from hypothesis import given, settings
from hypothesis import strategies as st

import database


def _create_isolated_db(db_path: str):
    """在指定路径创建一个独立的测试数据库，初始化 schema。"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
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
            created_at TEXT NOT NULL,
            user_id INTEGER
        )
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_history_user_id ON history_records(user_id)"
    )
    conn.commit()
    conn.close()


def _insert_record_for_user(db_path: str, user_id: int, category: str = "resume_diagnosis"):
    """向测试数据库中为指定用户插入一条历史记录。"""
    conn = sqlite3.connect(db_path)
    conn.execute(
        """INSERT INTO history_records
           (category, user_input, ai_result, scores, extra_data, chat_history, is_saved, created_at, user_id)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            category,
            "test input",
            "test result",
            json.dumps({}),
            json.dumps({}),
            json.dumps([]),
            0,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            user_id,
        ),
    )
    conn.commit()
    conn.close()


@given(st.integers(min_value=1, max_value=10000))
@settings(max_examples=100, deadline=None)
def test_user_data_isolation_invariant(user_id: int):
    """
    Property 1: 用户数据隔离不变量

    对任意合法 user_id，get_recent_records_by_user() 返回的所有记录的
    user_id 字段均等于输入值。其他用户的记录绝不出现在结果集中。

    **Validates: Requirements 4.3, 4.4**
    """
    # 使用临时文件作为隔离的测试数据库，避免污染真实的 history.db
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        tmp_db_path = tmp_file.name

    try:
        # 初始化测试数据库 schema
        _create_isolated_db(tmp_db_path)

        # 构造"其他用户"的 ID，确保与目标 user_id 不同
        # 使用固定偏移量，并通过取模保证不与 user_id 碰撞
        other_user_id_a = user_id + 1 if user_id < 10000 else user_id - 1
        # 确保 other_user_id_b 与 user_id 和 other_user_id_a 均不同
        other_user_id_b = user_id + 2 if user_id <= 9998 else user_id - 2

        # 为目标用户插入 3 条记录
        for _ in range(3):
            _insert_record_for_user(tmp_db_path, user_id)

        # 为其他两个用户各插入 2 条记录（用于验证隔离性）
        for _ in range(2):
            _insert_record_for_user(tmp_db_path, other_user_id_a)
            _insert_record_for_user(tmp_db_path, other_user_id_b)

        # 将 database 模块的 DB_PATH 指向临时测试数据库
        with patch.object(database, "DB_PATH", tmp_db_path):
            records = database.get_recent_records_by_user(user_id, limit=50)

        # ── 核心断言：所有返回记录的 user_id 必须等于输入值 ──
        assert len(records) == 3, (
            f"Expected 3 records for user_id={user_id}, got {len(records)}"
        )

        for record in records:
            assert record["user_id"] == user_id, (
                f"Data isolation violated: expected user_id={user_id}, "
                f"but got user_id={record['user_id']} in returned record"
            )

    finally:
        # 清理临时数据库文件
        try:
            os.unlink(tmp_db_path)
        except OSError:
            pass


@given(st.integers(min_value=1, max_value=10000))
@settings(max_examples=50)
def test_empty_result_for_user_with_no_records(user_id: int):
    """
    补充测试：对于没有任何记录的用户，get_recent_records_by_user() 应返回空列表。

    **Validates: Requirements 4.3**
    """
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        tmp_db_path = tmp_file.name

    try:
        _create_isolated_db(tmp_db_path)

        # 为其他用户插入记录，但不为目标 user_id 插入任何记录
        other_user_id = (user_id % 10000) + 1 if user_id < 10000 else user_id - 1
        _insert_record_for_user(tmp_db_path, other_user_id)

        with patch.object(database, "DB_PATH", tmp_db_path):
            records = database.get_recent_records_by_user(user_id, limit=10)

        assert records == [], (
            f"Expected empty list for user_id={user_id} with no records, "
            f"but got {len(records)} records"
        )

    finally:
        try:
            os.unlink(tmp_db_path)
        except OSError:
            pass
