"""
Router/careerPlan.py — 职业规划路由层

职责：HTTP 请求处理、参数校验、调用 Service 层。
不包含任何 LLM 调用逻辑或 Prompt 字符串。
"""

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from Router.models.career_model import CareerPlanRequest, CareerSuggestionsRequest
from Service.career_service import career_plan_stream, get_career_suggestions

router = APIRouter(tags=["careerPlan"], prefix="/api")


@router.post("/career/plan")
async def career_plan(request: CareerPlanRequest):
    """
    职业规划生成端点 — 返回 SSE StreamingResponse。

    接收简历文本和用户困惑，调用 Service 层流式生成职业规划报告。
    """
    return StreamingResponse(
        career_plan_stream(
            resume_text=request.resume_text,
            user_confusion=request.user_confusion,
            provider_id=request.provider_id,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/career/suggestions")
async def career_suggestions(request: CareerSuggestionsRequest):
    """
    职业推荐问题端点 — 非流式，返回 4 个推荐问题列表。

    根据简历内容动态生成最可能的职业困惑问题，失败时返回默认兜底列表。
    """
    suggestions = await get_career_suggestions(
        request.resume_text,
        provider_id=request.provider_id,
    )
    return {"suggestions": suggestions}
