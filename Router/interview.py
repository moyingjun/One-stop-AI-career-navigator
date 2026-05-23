"""
Router/interview.py — 模拟面试路由层

职责：HTTP 请求处理、参数校验、调用 Service 层。
不包含任何 LLM 调用逻辑或 Prompt 字符串。
"""

from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from Router.dependencies import get_optional_user
from Router.models.interview_model import ChatRequest, EvaluateRequest
from Service.interview_service import evaluate_interview, interview_chat_stream

router = APIRouter(prefix="/api/interview", tags=["模拟面试"])


@router.post("/chat")
async def interview_chat(request: ChatRequest):
    """
    面试聊天端点 — 返回 SSE StreamingResponse。

    使用 interview_chat_stream 生成器逐块推送 AI 回复，
    支持打字机效果和心跳保活。
    """
    return StreamingResponse(
        interview_chat_stream(
            user_query=request.user_query,
            history=request.history,
            resume_text=request.resume_text or "",
            jd_text=request.jd_text or "",
            target_job=request.target_job or "",
            difficulty=request.difficulty or "standard",
            provider_id=request.provider_id,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/evaluate")
async def evaluate_interview_endpoint(
    request: EvaluateRequest,
    current_user_id: Optional[int] = Depends(get_optional_user),
):
    """面试评估端点 — 非流式，返回六维评分 JSON。"""
    result = await evaluate_interview(
        history=request.history,
        resume_text=request.resume_text or "",
        jd_text=request.jd_text or "",
        difficulty=request.difficulty or "standard",
        user_id=current_user_id,
        provider_id=request.provider_id,
    )

    if result:
        return {"success": True, "data": result}
    return {"success": False, "msg": "打分失败，请重试"}


@router.post("/check-order")
async def check_order():
    """订单状态检查端点（内测模式兜底）。"""
    return {"success": True, "status": "completed"}
