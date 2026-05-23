"""
Router/agent_dispatcher.py — Agent Dispatcher 路由层

职责：HTTP 请求处理、参数校验、调用 Service 层。
不包含任何 LLM 调用逻辑、Prompt 字符串或路由规则。
"""

from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from Router.dependencies import get_optional_user
from Router.models.agent_model import AgentChatRequest
from Service.Agents.dispatcher_agent import stream_dispatcher_response
from Service.Utils.databases.db import get_db

router = APIRouter(prefix="/api/agent", tags=["Agent Dispatcher"])


@router.post("/chat")
async def agent_chat(
    request: AgentChatRequest,
    current_user_id: Optional[int] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Multi-Agent 统一聊天入口，面向 Dashboard LUI。

    支持游客访问（user_id 为 None）和已登录用户（user_id 为正整数）。
    自动路由到对应专家 Agent，已登录用户支持 RAG 知识库注入（Top-K=3）。
    """
    return StreamingResponse(
        stream_dispatcher_response(
            user_input=request.user_input,
            history=request.history,
            resume_text=request.resume_text or "",
            target_job=request.target_job or "",
            jd_text=request.jd_text or "",
            user_id=current_user_id,
            db=db if current_user_id is not None else None,
            persist=request.persist if request.persist else False,
            provider_id=request.provider_id,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
