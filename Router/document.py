"""
Router/document.py — 文档工作台路由层

仅暴露 /api/document/rewrite，复用 Service/document_service 的业务编排。
不读写历史 / 知识库 / 任何数据库。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from Router.dependencies import get_current_user
from Router.models.document_model import (
    ExtractResumeRequest,
    ExtractResumeResponse,
    RewriteRequest,
    RewriteResponse,
)
from Service.document_service import extract_resume_from_draft, rewrite_text
from Service.Utils.llm_client import LLMClientError

router = APIRouter(prefix="/api/document", tags=["文档工作台"])


@router.post("/rewrite", response_model=RewriteResponse)
async def rewrite_document(
    request: RewriteRequest,
    _user_id: int = Depends(get_current_user),
) -> RewriteResponse:
    """
    AI 润色 — 对选中文本按指定风格改写。

    强制要求：
      - 必须携带有效 JWT
      - 不会把 text / result 写入数据库
      - LLM 调用失败时返回 503，由前端 toast 处理
    """
    try:
        result = await rewrite_text(
            text=request.text,
            style=request.style,
            rewrite_mode=request.rewrite_mode,
            rewrite_strength=request.rewrite_strength,
            rewrite_level=request.rewrite_level,
            custom_instruction=request.custom_instruction,
            provider_id=request.provider_id,
        )
    except ValueError as exc:
        # 输入校验类错误 — 长度 / 空文本 / 非法风格
        raise HTTPException(status_code=400, detail=str(exc))
    except LLMClientError as exc:
        # 模型不可用 / 超时 / 模型空返回
        raise HTTPException(status_code=503, detail=str(exc) or "AI 润色失败，请稍后重试")
    except Exception as exc:  # noqa: BLE001
        # 兜底：避免未预期异常打到前端
        raise HTTPException(status_code=500, detail=f"AI 润色服务内部异常: {type(exc).__name__}")

    return RewriteResponse(success=True, result=result)



@router.post("/extract-resume", response_model=ExtractResumeResponse)
async def extract_resume(
    request: ExtractResumeRequest,
    _user_id: int = Depends(get_current_user),
) -> ExtractResumeResponse:
    """
    Extract_Resume_API:把 /files 的 Tiptap 草稿抽取为结构化 Resume_JSON。

    设计契约(Requirement 4.1 / 4.7 / 11.2 / 11.6):
      - 必须携带有效 JWT。
      - 业务级失败通过 success=false + warnings 表达,resume_json 永不为 null。
      - 不接 RAG / 历史 / 知识库,仅触达 LLM 一次抽取。
      - HTTP 始终返回 200(除 Pydantic 422 与本兜底 500)。

    取证(仅 DEBUG_MODE=true):
      - 每次请求生成 request_id 并贯穿日志 + 写入 debug/resume_extract/{rid}_* 产物。
      - 响应中携带 debug_request_id 以便前端 console 关联同一次请求。
    """
    from Service.Utils.resume_extract_debug import is_debug_enabled, new_request_id

    request_id = new_request_id() if is_debug_enabled() else ""
    if request_id:
        print(f"[extract-resume][rid:{request_id}] request received")

    try:
        return await extract_resume_from_draft(
            document_id=request.document_id,
            plain_text=request.plain_text,
            content_json=request.content_json,
            provider_id=request.provider_id,
            request_id=request_id,
        )
    except ValueError as exc:
        # 仅在 Pydantic 之后仍然出现的输入越界(理论不应发生)
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=500,
            detail=f"简历抽取服务异常: {type(exc).__name__}",
        )
