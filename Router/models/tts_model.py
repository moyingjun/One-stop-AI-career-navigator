"""
Router/models/tts_model.py — TTS 请求/响应 Pydantic 模型

只放 schema,不含业务逻辑。
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class TTSRequest(BaseModel):
    """
    POST /api/tts/synthesize 请求体。

    字段:
        text   — 待朗读文本(必填,长度由 Service 层根据 Settings.TTS_MAX_TEXT_LEN 校验)
        voice  — 预置音色名,缺省走 Settings.TTS_VOICE
                 mimo-v2.5-tts 可选:mimo_default / 冰糖 / 茉莉 / 苏打 / 白桦 /
                                   Mia / Chloe / Milo / Dean
        style  — 自然语言风格指令(可选);若提供则会以 user 消息形式注入到 chat-completions
        format — 输出格式,缺省走 Settings.TTS_FORMAT;只允许 mp3 / wav
                 (Beta 版不开放 pcm/pcm16,需要的话另起任务)
    """

    text: str = Field(..., description="待朗读文本")
    voice: Optional[str] = Field(None, description="预置音色名,缺省 mimo_default")
    style: Optional[str] = Field(None, description="自然语言风格指令(可选)")
    format: Optional[Literal["mp3", "wav"]] = Field(None, description="输出格式,缺省 mp3")
