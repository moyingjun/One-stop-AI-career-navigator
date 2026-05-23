"""
Router/document.py — 文档工作台路由层

仅暴露 /api/document/rewrite，复用 Service/document_service 的业务编排。
不读写历史 / 知识库 / 任何数据库。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from Router.dependencies import get_current_user
from Router.models.document_model import RewriteRequest, RewriteResponse
from Service.document_service import rewrite_text
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
