"""面试路由的 Pydantic 请求模型。"""

from pydantic import BaseModel
from typing import Optional, List


class ChatRequest(BaseModel):
    """面试聊天请求体。"""
    user_query: str
    history: List[dict] = []
    resume_text: Optional[str] = ""
    jd_text: Optional[str] = ""
    difficulty: Optional[str] = "standard"
    target_job: Optional[str] = ""


class EvaluateRequest(BaseModel):
    """面试评估请求体。"""
    user_query: str
    history: List[dict] = []
    resume_text: Optional[str] = ""
    jd_text: Optional[str] = ""
    difficulty: Optional[str] = "standard"
    user_id: Optional[int] = None
