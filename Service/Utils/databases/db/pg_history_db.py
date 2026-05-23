"""
Service/Utils/databases/db/pg_history_db.py — PostgreSQL 异步历史记录 CRUD

使用 SQLAlchemy 2.0 异步 ORM，替代旧 SQLite history_db.py 实现。

所有函数均接受 AsyncSession 作为参数（由 FastAPI Depends(get_db) 注入），
调用后 session commit 由 get_db() 依赖生成器自动处理。
但 upsert_session_record / enforce_unsaved_cap 等复杂写操作会在内部 flush/commit，
调用方无需额外处理。

返回值格式：
    所有函数返回 dict（与旧 SQLite 版本兼容），
    保证前端和 Router 层无需修改即可继续工作。
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from Service.Utils.databases.models.history_model import HistoryRecord


# ─────────────────────────────────────────────
# 内部工具
# ─────────────────────────────────────────────

def _utc_now_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _dump_json(v) -> str:
    if v is None:
        return "{}"
    if isinstance(v, str):
        return v
    return json.dumps(v, ensure_ascii=False)


def _dump_json_list(v) -> str:
    if v is None:
        return "[]"
    if isinstance(v, str):
        return v
    return json.dumps(v, ensure_ascii=False)


def _parse_json(v) -> Any:
    """安全解析 JSON 字符串，失败时返回 None。"""
    if not v:
        return None
    if isinstance(v, (dict, list)):
        return v
    try:
        return json.loads(v)
    except (json.JSONDecodeError, TypeError):
        return None


def _record_to_dict(record: HistoryRecord) -> dict:
    """将 ORM 模型转换为与旧 SQLite 版本兼容的 dict。"""
    created_str = (
        record.created_at.strftime("%Y-%m-%d %H:%M:%S")
        if isinstance(record.created_at, datetime)
        else str(record.created_at or "")
    )
    updated_str = (
        record.updated_at.strftime("%Y-%m-%d %H:%M:%S")
        if isinstance(record.updated_at, datetime)
        else str(record.updated_at or "")
    )
    return {
        "id": record.id,
        "user_id": record.user_id,
        "category": record.category or "",
        "record_type": record.record_type,
        "session_id": record.session_id,
        "user_input": record.user_input or "",
        "ai_result": record.ai_result or "",
        "chat_history": _parse_json(record.chat_history) or [],
        "scores": _parse_json(record.scores) or {},
        "extra_data": _parse_json(record.extra_data) or {},
        "is_saved": bool(record.is_saved),
        "created_at": created_str,
        "updated_at": updated_str,
    }


# ─────────────────────────────────────────────
# 历史记录 CRUD
# ─────────────────────────────────────────────

async def insert_record(
    db: AsyncSession,
    category: str,
    user_input: str,
    ai_result: str,
    scores: dict = None,
    extra_data: dict = None,
    chat_history: list = None,
    is_saved: bool = False,
    user_id: Optional[int] = None,
    record_type: Optional[str] = None,
    session_id: Optional[str] = None,
) -> int:
    """插入一条历史记录，返回新记录的 id。"""
    now = datetime.now(timezone.utc)
    record = HistoryRecord(
        category=category,
        user_input=(user_input or "")[:2000],
        ai_result=(ai_result or "")[:5000],
        scores=_dump_json(scores),
        extra_data=_dump_json(extra_data),
        chat_history=_dump_json_list(chat_history),
        is_saved=is_saved,
        user_id=user_id,
        record_type=record_type,
        session_id=session_id,
        created_at=now,
        updated_at=now,
    )
    db.add(record)
    await db.flush()  # flush to get the id without full commit
    record_id = record.id
    return record_id


async def get_recent_records_by_user(
    db: AsyncSession,
    user_id: int,
    limit: int = 10,
    category: Optional[str] = None,
    has_scores: bool = False,
) -> list[dict]:
    """按 user_id 隔离查询历史记录（多租户安全约束）。"""
    stmt = select(HistoryRecord).where(HistoryRecord.user_id == user_id)
    if category:
        stmt = stmt.where(HistoryRecord.category == category)
    if has_scores:
        stmt = stmt.where(
            HistoryRecord.scores.is_not(None),
            HistoryRecord.scores != "{}",
            HistoryRecord.scores != '"{}"',
        )
    stmt = stmt.order_by(HistoryRecord.id.desc()).limit(limit)
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return [_record_to_dict(r) for r in rows]


async def get_record_by_id(
    db: AsyncSession,
    record_id: int,
) -> Optional[dict]:
    """按 id 获取单条记录，不做 user_id 隔离（调用方自行校验归属）。"""
    result = await db.execute(
        select(HistoryRecord).where(HistoryRecord.id == record_id)
    )
    row = result.scalar_one_or_none()
    return _record_to_dict(row) if row else None


async def delete_record(
    db: AsyncSession,
    record_id: int,
) -> bool:
    """删除指定记录，返回是否成功。"""
    result = await db.execute(
        delete(HistoryRecord).where(HistoryRecord.id == record_id)
    )
    return result.rowcount > 0


async def clear_records_by_user(
    db: AsyncSession,
    user_id: int,
) -> int:
    """清空指定用户的所有历史记录（多租户安全版本）。"""
    result = await db.execute(
        delete(HistoryRecord).where(HistoryRecord.user_id == user_id)
    )
    return result.rowcount


async def toggle_save_record(
    db: AsyncSession,
    record_id: int,
    is_saved: bool,
) -> Optional[dict]:
    """切换指定记录的保存状态。"""
    await db.execute(
        update(HistoryRecord)
        .where(HistoryRecord.id == record_id)
        .values(is_saved=is_saved)
    )
    await db.flush()
    return await get_record_by_id(db, record_id)


async def count_saved_records_by_user(
    db: AsyncSession,
    user_id: int,
) -> int:
    """
    统计指定用户当前已收藏（is_saved=True）的记录数量。

    用于 PATCH /save 端点在收藏前判断是否超过上限（10 条）。
    严格按 user_id 隔离，不统计全站。
    """
    result = await db.execute(
        select(func.count()).where(
            HistoryRecord.user_id == user_id,
            HistoryRecord.is_saved == True,  # noqa: E712
        )
    )
    return result.scalar() or 0


# ─────────────────────────────────────────────
# 会话级 Upsert
# ─────────────────────────────────────────────

async def upsert_session_record(
    db: AsyncSession,
    user_id: int,
    session_id: str,
    record_type: str,
    user_input: str = "",
    ai_result: str = "",
    scores: dict = None,
    extra_data: dict = None,
    chat_history: list = None,
    category: str = None,
) -> dict:
    """
    按 session_id 幂等写入/更新历史记录。

    - 若 session_id 已存在且属于同一 user_id → UPDATE
    - 若不存在 → INSERT
    - 返回完整记录 dict
    """
    now = datetime.now(timezone.utc)

    # 检查是否已存在
    existing_result = await db.execute(
        select(HistoryRecord).where(
            HistoryRecord.session_id == session_id,
            HistoryRecord.user_id == user_id,
        )
    )
    existing = existing_result.scalar_one_or_none()

    if existing:
        existing.user_input = (user_input or "")[:2000]
        existing.ai_result = (ai_result or "")[:5000]
        existing.scores = _dump_json(scores)
        existing.extra_data = _dump_json(extra_data)
        existing.chat_history = _dump_json_list(chat_history)
        existing.record_type = record_type
        existing.category = category or record_type
        existing.updated_at = now
        await db.flush()
        return _record_to_dict(existing)
    else:
        record = HistoryRecord(
            user_id=user_id,
            session_id=session_id,
            record_type=record_type,
            category=category or record_type,
            user_input=(user_input or "")[:2000],
            ai_result=(ai_result or "")[:5000],
            scores=_dump_json(scores),
            extra_data=_dump_json(extra_data),
            chat_history=_dump_json_list(chat_history),
            is_saved=False,
            created_at=now,
            updated_at=now,
        )
        db.add(record)
        await db.flush()
        return _record_to_dict(record)


async def get_record_by_session_id(
    db: AsyncSession,
    user_id: int,
    session_id: str,
) -> Optional[dict]:
    """按 session_id + user_id 查询唯一记录。"""
    result = await db.execute(
        select(HistoryRecord).where(
            HistoryRecord.session_id == session_id,
            HistoryRecord.user_id == user_id,
        )
    )
    row = result.scalar_one_or_none()
    return _record_to_dict(row) if row else None


async def enforce_unsaved_cap(
    db: AsyncSession,
    user_id: int,
    record_group: str,
    cap: int = 10,
) -> int:
    """
    强制执行未收藏记录上限策略。

    record_group:
        'chat'    — dashboard_chat 类型
        'feature' — resume_diagnosis / career_plan / interview_session

    超出 cap 时删除最旧的未收藏记录（按 id ASC）。
    收藏记录（is_saved=True）永远保留。
    返回删除的记录数。
    """
    if record_group == "chat":
        type_values = ["dashboard_chat"]
    elif record_group == "feature":
        type_values = ["resume_diagnosis", "career_plan", "interview_session"]
    else:
        return 0

    # 统计未收藏记录数
    count_result = await db.execute(
        select(func.count()).where(
            HistoryRecord.user_id == user_id,
            HistoryRecord.is_saved == False,  # noqa: E712
            HistoryRecord.record_type.in_(type_values),
        )
    )
    count = count_result.scalar() or 0

    deleted = 0
    if count > cap:
        excess = count - cap
        # 找到最旧的 excess 条未收藏记录的 id
        oldest_result = await db.execute(
            select(HistoryRecord.id).where(
                HistoryRecord.user_id == user_id,
                HistoryRecord.is_saved == False,  # noqa: E712
                HistoryRecord.record_type.in_(type_values),
            ).order_by(HistoryRecord.id.asc()).limit(excess)
        )
        ids_to_delete = [row[0] for row in oldest_result.fetchall()]
        if ids_to_delete:
            del_result = await db.execute(
                delete(HistoryRecord).where(HistoryRecord.id.in_(ids_to_delete))
            )
            deleted = del_result.rowcount
            await db.flush()

    return deleted
