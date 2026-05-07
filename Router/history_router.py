from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from database import (
    clear_all_records,
    delete_record,
    get_recent_records,
    get_record_by_id,
    get_saved_records,
    toggle_save_record,
)


router = APIRouter(prefix="/api/history", tags=["History"])


class SaveRecordRequest(BaseModel):
    is_saved: bool


@router.get("")
async def get_history(limit: int = 10):
    records = get_recent_records(limit)
    return {"success": True, "records": records}


@router.get("/saved")
async def get_saved_history():
    records = get_saved_records()
    return {"success": True, "records": records}


@router.delete("/clear")
async def clear_history():
    deleted_count = clear_all_records()
    return {"success": True, "deleted_count": deleted_count}


@router.get("/{record_id}")
async def get_history_by_id(record_id: int):
    record = get_record_by_id(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    return {"success": True, "data": record}


@router.delete("/{record_id}")
async def delete_history_record(record_id: int):
    deleted = delete_record(record_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="记录不存在")
    return {"success": True, "deleted_id": record_id}


@router.patch("/{record_id}/save")
async def save_history_record(record_id: int, request: SaveRecordRequest):
    record = toggle_save_record(record_id, request.is_saved)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    return {"success": True, "data": record}
