"""Agent Dispatcher 路由的 Pydantic 请求模型。"""

from pydantic import BaseModel, Field
from typing import Optional, List


class ChatMessage(BaseModel):
    role: str
    content: str


class AgentChatRequest(BaseModel):
    """通用 Agent 聊天请求体。"""
    user_input: str
    knowledge_id: Optional[str] = None
    history: List[ChatMessage] = Field(default_factory=list)
    resume_text: Optional[str] = ""
    target_job: Optional[str] = ""
    jd_text: Optional[str] = ""
    top_k: Optional[int] = 4
    user_id: Optional[int] = None
    persist: Optional[bool] = False  # 是否自动保存到历史（Dashboard ChatDock 默认不保存）
    provider_id: Optional[str] = None  # LLM Provider 切换（mimo / deepseek / None=默认）
