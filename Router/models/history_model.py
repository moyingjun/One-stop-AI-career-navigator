"""历史记录路由的 Pydantic 请求模型。"""

from pydantic import BaseModel


class SaveRecordRequest(BaseModel):
    """切换保存状态请求体。"""
    is_saved: bool
