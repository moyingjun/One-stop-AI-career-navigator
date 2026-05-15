"""
Router/resumeDiagnosis.py — 简历诊断路由层

职责：HTTP 请求处理、参数校验、调用 Service 层。
不包含任何 LLM 调用逻辑或 Prompt 字符串。
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from Router.dependencies import get_optional_user
from Router.models.resume_model import ResumeDiagnoseRequest
from Service.resume_service import diagnose_resume_stream

router = APIRouter(tags=["resumeDiagnosis"], prefix="/api")


@router.post("/resume/diagnose")
async def diagnose_resume(
    request: ResumeDiagnoseRequest,
    current_user_id: Optional[int] = Depends(get_optional_user),
):
    """
    简历诊断端点 — 返回 SSE StreamingResponse。

    接收简历文本、目标岗位和 JD，调用 Service 层流式生成诊断报告。
    支持游客访问（user_id 为 None）和已登录用户。
    """
    try:
        return StreamingResponse(
            diagnose_resume_stream(
                resume_text=request.resume_text,
                target_role=request.target_role or "",
                jd_text=request.jd_text or "",
                user_id=current_user_id,
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"服务异常: {exc}")
