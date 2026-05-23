"""职业规划路由的 Pydantic 请求模型。"""

from typing import Optional
from pydantic import BaseModel


class CareerPlanRequest(BaseModel):
    """职业规划生成请求体。"""
    resume_text: str
    user_confusion: str
    provider_id: Optional[str] = None  # LLM Provider 切换


class CareerSuggestionsRequest(BaseModel):
    """职业推荐问题请求体。"""
    resume_text: str
    provider_id: Optional[str] = None
