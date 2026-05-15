"""
Router/history_router.py — 历史记录 CRUD 路由（多租户隔离版）

所有端点均注入 get_current_user 依赖，强制要求有效 JWT。
- GET  /api/history          — 返回当前用户的最近记录（按 user_id 隔离）
- GET  /api/history/saved    — 返回当前用户的已保存记录
- DELETE /api/history/clear  — 清空当前用户的所有记录
- GET  /api/history/{id}     — 获取指定记录（校验 user_id 归属，不匹配返回 403）
- DELETE /api/history/{id}   — 删除指定记录（校验 user_id 归属，不匹配返回 403）
- PATCH /api/history/{id}/save — 切换保存状态（校验 user_id 归属，不匹配返回 403）

对应 Requirements 4.2, 4.3, 4.4, 4.5
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from database import (
    clear_records_by_user,
    delete_record,
    get_recent_records_by_user,
    get_record_by_id,
    get_saved_records,
    toggle_save_record,
)
from Router.dependencies import get_current_user


router = APIRouter(prefix="/api/history", tags=["History"])


class SaveRecordRequest(BaseModel):
    is_saved: bool


def _assert_record_ownership(record: dict, current_user_id: int) -> None:
    """
    校验历史记录的 user_id 是否与当前用户匹配。

    存量记录的 user_id 可能为 NULL（迁移前写入），此时允许访问以保持向后兼容。
    若 user_id 不为 NULL 且与当前用户不匹配，则抛出 HTTP 403。

    参数：
        record          — 从数据库取出的记录字典
        current_user_id — 由 get_current_user 依赖注入提供的当前用户 ID

    抛出：
        HTTPException(403) — 记录归属于其他用户时
    """
    record_user_id = record.get("user_id")
    # user_id 为 NULL 的存量记录允许任意已认证用户访问（向后兼容）
    if record_user_id is not None and record_user_id != current_user_id:
        raise HTTPException(status_code=403, detail="无权访问此资源")


@router.get("")
async def get_history(
    limit: int = 10,
    current_user_id: int = Depends(get_current_user),
):
    """
    获取当前用户的最近历史记录。

    使用 get_recent_records_by_user 强制附加 WHERE user_id = ? 隔离约束，
    确保不同用户之间的数据完全隔离（Requirements 4.3）。
    """
    records = get_recent_records_by_user(user_id=current_user_id, limit=limit)
    return {"success": True, "records": records}


@router.get("/saved")
async def get_saved_history(
    current_user_id: int = Depends(get_current_user),
):
    """
    获取当前用户的已保存历史记录。

    🚨 多租户铁律：从 JWT Token 中提取 user_id，只返回属于当前用户的记录。
    向后兼容：user_id 为 NULL 的存量记录也允许访问。
    """
    records = get_recent_records_by_user(
        user_id=current_user_id,
        limit=200,  # 已保存记录上限
    )
    # 进一步过滤：只返回 is_saved=True 的记录
    saved = [r for r in records if r.get("is_saved")]
    return {"success": True, "records": saved}


@router.delete("/clear")
async def clear_history(
    current_user_id: int = Depends(get_current_user),
):
    """
    清空当前用户的所有历史记录。

    🚨 多租户铁律：只清空当前用户（由 JWT 解析）的记录，绝不清空全表。
    """
    deleted_count = clear_records_by_user(user_id=current_user_id)
    return {"success": True, "deleted_count": deleted_count}


@router.get("/{record_id}")
async def get_history_by_id(
    record_id: int,
    current_user_id: int = Depends(get_current_user),
):
    """
    获取指定 ID 的历史记录。

    在返回数据前校验记录的 user_id 是否属于当前用户，
    不匹配时返回 HTTP 403（Requirements 4.4）。
    """
    record = get_record_by_id(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    _assert_record_ownership(record, current_user_id)
    return {"success": True, "data": record}


@router.delete("/{record_id}")
async def delete_history_record(
    record_id: int,
    current_user_id: int = Depends(get_current_user),
):
    """
    删除指定 ID 的历史记录。

    在执行删除前校验记录的 user_id 是否属于当前用户，
    不匹配时返回 HTTP 403（Requirements 4.4）。
    """
    record = get_record_by_id(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    _assert_record_ownership(record, current_user_id)
    deleted = delete_record(record_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="记录不存在")
    return {"success": True, "deleted_id": record_id}


@router.patch("/{record_id}/save")
async def save_history_record(
    record_id: int,
    request: SaveRecordRequest,
    current_user_id: int = Depends(get_current_user),
):
    """
    切换指定历史记录的保存状态。

    在修改前校验记录的 user_id 是否属于当前用户，
    不匹配时返回 HTTP 403（Requirements 4.4）。
    """
    record = get_record_by_id(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    _assert_record_ownership(record, current_user_id)
    updated = toggle_save_record(record_id, request.is_saved)
    if not updated:
        raise HTTPException(status_code=404, detail="记录不存在")
    return {"success": True, "data": updated}
