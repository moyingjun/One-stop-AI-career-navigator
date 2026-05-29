"""
Service/tts_service.py — Mimo TTS 调用业务封装

只暴露一个入口:synthesize_speech(text, voice, style, fmt) → (bytes, mime)

调用流程:
  1. 入参校验(空文本 / 长度上限)
  2. 组装 chat-completions 请求(messages + audio.format/voice)
  3. POST {TTS_BASE_URL}/chat/completions,header 用 api-key
  4. 解析 choices[0].message.audio.data(Base64)→ bytes
  5. 返回 (bytes, mime),mime 由 fmt 决定:audio/mpeg or audio/wav

错误边界:
  - 入参 → ValueError(由 Router 转 4xx)
  - 上游 4xx/5xx → TTSServiceError(由 Router 转 503)
  - 上游异常字段 → TTSServiceError("AI 未返回有效音频")

安全:
  - 不打印 API Key
  - 不把 text 完整写入日志(只打印长度)
  - 不把 base64 音频写入日志
"""

from __future__ import annotations

import base64
import binascii
from typing import Tuple

import httpx

from Settings.config import (
    TTS_API_KEY,
    TTS_BASE_URL,
    TTS_FORMAT,
    TTS_MAX_TEXT_LEN,
    TTS_MODEL_NAME,
    TTS_TIMEOUT_SEC,
    TTS_VOICE,
)


# ─────────────────────────────────────────────
# 错误类
# ─────────────────────────────────────────────


class TTSServiceError(Exception):
    """TTS 上游 / 解析 / 网络层异常,Router 转 503。"""


# ─────────────────────────────────────────────
# 常量
# ─────────────────────────────────────────────

_FMT_TO_MIME = {
    "mp3": "audio/mpeg",
    "wav": "audio/wav",
}

# Mimo Open Platform 兼容两种 header,本项目统一用 api-key(简短 + 与现有 Mimo provider 风格一致)
_AUTH_HEADER_NAME = "api-key"


# ─────────────────────────────────────────────
# 公共入口
# ─────────────────────────────────────────────


async def synthesize_speech(
    text: str,
    voice: str | None = None,
    style: str | None = None,
    fmt: str | None = None,
) -> Tuple[bytes, str]:
    """
    将文本合成为语音字节。

    参数:
        text   — 待朗读文本(空白会被 strip;空 / 超长抛 ValueError)
        voice  — 预置音色;缺省走 Settings.TTS_VOICE
        style  — 自然语言风格指令(可选);非空时会以 user 消息形式注入
        fmt    — 输出格式,只允许 'mp3' | 'wav';缺省走 Settings.TTS_FORMAT

    返回:
        (audio_bytes, mime_type)

    抛出:
        ValueError       — 入参校验失败(空文本 / 文本过长 / 非法 fmt)
        TTSServiceError  — API Key 缺失 / 上游 4xx/5xx / 上游响应缺字段 / Base64 解码失败 / 网络超时
    """
    # ── 1. 入参清洗 ──
    txt = (text or "").strip()
    if not txt:
        raise ValueError("文本不能为空")
    if len(txt) > TTS_MAX_TEXT_LEN:
        raise ValueError(f"文本长度不得超过 {TTS_MAX_TEXT_LEN} 字符")

    final_voice = (voice or TTS_VOICE).strip() or TTS_VOICE
    final_fmt = (fmt or TTS_FORMAT).strip().lower() or TTS_FORMAT
    if final_fmt not in _FMT_TO_MIME:
        raise ValueError(f"不支持的输出格式:{final_fmt}")

    if not TTS_API_KEY:
        # 不打印 key,只提示运维
        raise TTSServiceError("TTS API Key 未配置")

    # ── 2. 组装请求体 ──
    messages = []
    if style and style.strip():
        # 风格指令必须放 user 角色
        messages.append({"role": "user", "content": style.strip()})
    # 待朗读文本必须放 assistant 角色(Mimo 强约束)
    messages.append({"role": "assistant", "content": txt})

    payload = {
        "model": TTS_MODEL_NAME,
        "messages": messages,
        "audio": {
            "format": final_fmt,
            "voice": final_voice,
        },
    }

    headers = {
        _AUTH_HEADER_NAME: TTS_API_KEY,
        "Content-Type": "application/json",
    }

    url = f"{TTS_BASE_URL}/chat/completions"

    # ── 3. 调上游 ──
    print(f"[tts] synthesize text_len={len(txt)} voice={final_voice} fmt={final_fmt} model={TTS_MODEL_NAME}")
    try:
        async with httpx.AsyncClient(timeout=TTS_TIMEOUT_SEC, proxy=None) as client:
            resp = await client.post(url, json=payload, headers=headers)
    except httpx.TimeoutException as exc:
        print(f"[tts] upstream timeout after {TTS_TIMEOUT_SEC}s")
        raise TTSServiceError("TTS 调用超时,请稍后重试") from exc
    except httpx.HTTPError as exc:
        # 网络层异常,屏蔽细节避免泄露 key 路径
        print(f"[tts] upstream network error: {type(exc).__name__}")
        raise TTSServiceError("TTS 调用失败,请稍后重试") from exc

    if resp.status_code != 200:
        # 上游业务错误 — 不回显原始 body,避免可能的 key 泄露
        snippet = ""
        try:
            data = resp.json()
            # 只摘 detail/message,不回显 headers
            snippet = str(data.get("detail") or data.get("message") or data.get("error") or "")[:200]
        except Exception:
            snippet = (resp.text or "")[:200]
        print(f"[tts] upstream non-200 status={resp.status_code}")
        raise TTSServiceError(f"TTS 上游错误({resp.status_code}):{snippet}".strip())

    # ── 4. 解析 audio.data(Base64)──
    try:
        body = resp.json()
        message = body["choices"][0]["message"]
        audio = message.get("audio") or {}
        audio_b64 = audio.get("data")
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        print(f"[tts] upstream response shape unexpected: {type(exc).__name__}")
        raise TTSServiceError("AI 未返回有效音频") from exc

    if not audio_b64 or not isinstance(audio_b64, str):
        print("[tts] upstream audio.data missing or not a string")
        raise TTSServiceError("AI 未返回有效音频")

    try:
        audio_bytes = base64.b64decode(audio_b64, validate=False)
    except (binascii.Error, ValueError) as exc:
        print(f"[tts] base64 decode failed: {type(exc).__name__}")
        raise TTSServiceError("音频数据解码失败") from exc

    if not audio_bytes:
        raise TTSServiceError("AI 返回的音频为空")

    mime = _FMT_TO_MIME[final_fmt]
    print(f"[tts] synthesize ok bytes={len(audio_bytes)} mime={mime}")
    return audio_bytes, mime
