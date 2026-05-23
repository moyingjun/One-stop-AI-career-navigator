"""历史记录路由的 Pydantic 请求/响应模型。"""

from typing import List, Optional
from pydantic import BaseModel


class SaveRecordRequest(BaseModel):
    """切换保存状态请求体。"""
    is_saved: bool


class SessionUpsertRequest(BaseModel):
    """会话级归档请求体（ChatDock 归档 / 三功能页自动保存）。"""
    session_id: str
    record_type: str
    user_input: str = ""
    ai_result: str = ""
    chat_history: List[dict] = []
    scores: Optional[dict] = None
    extra_data: Optional[dict] = None
