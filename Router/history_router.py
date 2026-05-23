"""
Router/history_router.py — 历史记录 CRUD 路由（PostgreSQL async 版本）

所有端点均注入 get_current_user 依赖，强制要求有效 JWT。
端点列表：
  GET    /api/history              — 返回当前用户的最近记录
  GET    /api/history/saved        — 返回当前用户的已保存记录
  DELETE /api/history/clear        — 清空当前用户的所有记录
  GET    /api/history/{id}         — 获取指定记录（校验 user_id 归属）
  DELETE /api/history/{id}         — 删除指定记录（校验 user_id 归属）
  PATCH  /api/history/{id}/save    — 切换保存状态（校验 user_id 归属）
  PUT    /api/history/session/{session_id}  — 幂等归档会话（upsert）
  GET    /api/history/session/{session_id}  — 按 session_id 获取记录
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from Router.dependencies import get_current_user
from Router.models.history_model import SaveRecordRequest, SessionUpsertRequest
from Service.Utils.databases.db import (
    get_db,
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

router = APIRouter(prefix="/api/history", tags=["History"])

# 收藏夹上限：用户最多可同时收藏 10 条记录（按 user_id 隔离）
SAVED_CAP = 10


def _assert_record_ownership(record: dict, current_user_id: int) -> None:
    """
    校验历史记录的 user_id 是否与当前用户匹配。
    存量记录 user_id 为 NULL 时允许访问（向后兼容）。
    """
    record_user_id = record.get("user_id")
    if record_user_id is not None and record_user_id != current_user_id:
        raise HTTPException(status_code=403, detail="无权访问此资源")


@router.get("")
async def get_history(
    limit: int = 10,
    has_scores: bool = False,
    current_user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前用户的最近历史记录。"""
    records = await get_recent_records_by_user(
        db=db,
        user_id=current_user_id,
        limit=limit,
        has_scores=has_scores,
    )
    return {"success": True, "records": records}


@router.get("/saved")
async def get_saved_history(
    current_user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前用户的已保存历史记录。"""
    records = await get_recent_records_by_user(
        db=db,
        user_id=current_user_id,
        limit=200,
    )
    saved = [r for r in records if r.get("is_saved")]
    return {"success": True, "records": saved}


@router.delete("/clear")
async def clear_history(
    current_user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """清空当前用户的所有历史记录。"""
    deleted_count = await clear_records_by_user(db=db, user_id=current_user_id)
    return {"success": True, "deleted_count": deleted_count}


# ── session 端点必须在 /{record_id} 之前注册，否则 FastAPI 会把 "session" 当 int ──

@router.put("/session/{session_id}")
async def upsert_session(
    session_id: str,
    request: SessionUpsertRequest,
    current_user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    按 session_id 幂等写入/更新历史记录（ChatDock 归档专用）。
    """
    record = await upsert_session_record(
        db=db,
        user_id=current_user_id,
        session_id=session_id,
        record_type=request.record_type,
        user_input=request.user_input,
        ai_result=request.ai_result,
        scores=request.scores or None,
        extra_data=request.extra_data or None,
        chat_history=request.chat_history or None,
        category=request.record_type,
    )

    # 执行上限策略
    if request.record_type == "dashboard_chat":
        await enforce_unsaved_cap(db=db, user_id=current_user_id, record_group="chat", cap=10)
    elif request.record_type in ("resume_diagnosis", "career_plan", "interview_session"):
        await enforce_unsaved_cap(db=db, user_id=current_user_id, record_group="feature", cap=10)

    return {
        "success": True,
        "data": record,
        "record_id": record["id"] if record else None,
        "session_id": session_id,
        "updated_at": record.get("updated_at") if record else None,
    }


@router.get("/session/{session_id}")
async def get_session(
    session_id: str,
    current_user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """按 session_id 获取历史记录（用于 Dashboard 恢复 ChatDock 对话）。"""
    record = await get_record_by_session_id(
        db=db, user_id=current_user_id, session_id=session_id
    )
    if not record:
        raise HTTPException(status_code=404, detail="会话记录不存在")
    return {"success": True, "data": record}


@router.get("/{record_id}")
async def get_history_by_id(
    record_id: int,
    current_user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取指定 ID 的历史记录（校验归属）。"""
    record = await get_record_by_id(db=db, record_id=record_id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    _assert_record_ownership(record, current_user_id)
    return {"success": True, "data": record}


@router.delete("/{record_id}")
async def delete_history_record(
    record_id: int,
    current_user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除指定 ID 的历史记录（校验归属）。"""
    record = await get_record_by_id(db=db, record_id=record_id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    _assert_record_ownership(record, current_user_id)
    deleted = await delete_record(db=db, record_id=record_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="记录不存在")
    return {"success": True, "deleted_id": record_id}


@router.patch("/{record_id}/save")
async def save_history_record(
    record_id: int,
    request: SaveRecordRequest,
    current_user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    切换指定历史记录的保存状态（校验归属 + 收藏夹上限）。

    业务规则：
      - 取消收藏（is_saved=False）：不限制，直接执行
      - 收藏（is_saved=True）：
          1. 若该记录当前已经是收藏状态 → 幂等返回成功
          2. 若用户当前收藏数 >= SAVED_CAP（10）→ 返回 409 Conflict
          3. 否则正常收藏

      该限制严格按 user_id 隔离，不统计全站。
      不会自动删除/取消已有收藏，需要用户自行操作。
    """
    record = await get_record_by_id(db=db, record_id=record_id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    _assert_record_ownership(record, current_user_id)

    # 收藏夹上限检查（仅在"未收藏 → 收藏"路径生效）
    if request.is_saved and not record.get("is_saved"):
        saved_count = await count_saved_records_by_user(db=db, user_id=current_user_id)
        if saved_count >= SAVED_CAP:
            raise HTTPException(
                status_code=409,
                detail=f"收藏夹已满，最多可收藏 {SAVED_CAP} 条记录，请先取消收藏其他记录。",
            )

    updated = await toggle_save_record(db=db, record_id=record_id, is_saved=request.is_saved)
    if not updated:
        raise HTTPException(status_code=404, detail="记录不存在")
    return {"success": True, "data": updated}
