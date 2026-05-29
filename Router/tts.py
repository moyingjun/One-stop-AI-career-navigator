"""
Router/tts.py — TTS 路由层

仅暴露 POST /api/tts/synthesize,复用 Service/tts_service 的业务编排。
不读写任何数据库,不接 RAG,不接 ChatDock 状态。
返回 audio/mpeg 或 audio/wav 字节流(不返回 base64 JSON)。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response

from Router.dependencies import get_current_user
from Router.models.tts_model import TTSRequest
from Service.tts_service import TTSServiceError, synthesize_speech

router = APIRouter(prefix="/api/tts", tags=["TTS"])


@router.post("/synthesize")
async def synthesize_endpoint(
    request: TTSRequest,
    _user_id: int = Depends(get_current_user),
) -> Response:
    """
    将文本合成为语音字节,直接以 audio/mpeg 或 audio/wav 返回。

    错误码:
      400 — 入参非法(空文本 / 超长 / 不支持的 format)
      503 — TTS 上游不可用 / 网络超时 / 上游响应字段缺失
    """
    try:
        audio_bytes, mime = await synthesize_speech(
            text=request.text,
            voice=request.voice,
            style=request.style,
            fmt=request.format,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except TTSServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc) or "TTS 服务暂时不可用")

    return Response(
        content=audio_bytes,
        media_type=mime,
        headers={
            # 同一文本同一参数,客户端可在私有缓存里复用 1 小时;TTSButton 也有进程内 Map
            "Cache-Control": "private, max-age=3600",
        },
    )
