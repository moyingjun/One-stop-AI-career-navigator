"""
Service/document_service.py — 文档工作台业务编排（D1.2 升级）

职责：
  - 校验输入（text 长度 / style 白名单 / rewrite_mode 白名单 / strength 范围 / custom_instruction 长度）
  - 处理 rewrite_strength（主） + rewrite_level（旧字段降级映射）
  - 组装 system prompt + user prompt
  - 调用 Service/Utils/llm_client.complete_chat
  - 清洗输出（去除 LLM 习惯加上的引号 / 前导语）；suggest 模式保留结构
  - 不写历史 / 不写知识库 / 不写数据库

设计约束：
  - 不直接 import httpx，全部走 llm_client
  - Prompt 字符串放在 Service/Agents/prompts/document_prompts.py（不在本文件硬编码）
"""

from __future__ import annotations

from typing import Optional

from Service.Agents.prompts.document_prompts import (
    LEVEL_WHITELIST,
    MODE_WHITELIST,
    STRENGTH_MAX,
    STRENGTH_MIN,
    STYLE_WHITELIST,
    build_rewrite_messages,
    coerce_strength,
    level_to_strength,
)
from Service.Utils.llm_client import LLMClientError, complete_chat

MAX_REWRITE_TEXT_CHARS = 3000
MAX_CUSTOM_INSTRUCTION_CHARS = 300


def _temperature_for_strength(strength: int, mode: str) -> float:
    """
    根据 strength（0-100）+ mode 选择温度。
    - polish: 0.2 ~ 0.5
    - suggest: 0.3 ~ 0.5（建议清单不需要太发散）
    - draft: 0.4 ~ 0.7（草稿允许稍微发散，但仍受占位符约束）
    """
    if mode == "polish":
        if strength <= 30:
            return 0.2
        if strength <= 70:
            return 0.4
        return 0.5
    if mode == "suggest":
        if strength <= 30:
            return 0.3
        if strength <= 70:
            return 0.4
        return 0.5
    # draft
    if strength <= 30:
        return 0.4
    if strength <= 70:
        return 0.55
    return 0.7


def _sanitize_polish_or_draft_output(raw: str) -> str:
    """
    polish / draft 模式输出清洗：
      - 剥离 markdown 围栏
      - 剥离常见前导语
      - 剥离首尾对称引号
    suggest 模式不走此函数（保留结构化清单）。
    """
    text = raw.strip()
    if not text:
        raise ValueError("AI 未返回有效内容")

    if text.startswith("```"):
        first_newline = text.find("\n")
        if first_newline != -1:
            text = text[first_newline + 1 :]
        if text.endswith("```"):
            text = text[: -3]
        text = text.strip()

    for prefix in (
        "改写后:", "改写后：", "改写：", "改写:",
        "建议:", "建议：",
        "草稿:", "草稿：",
        "以下是改写后的文本:", "以下是改写后的文本：",
        "以下是改写后的文本",
        "Here is the rewritten text:",
    ):
        if text.startswith(prefix):
            text = text[len(prefix) :].lstrip()

    if (
        len(text) >= 2
        and text[0] in ("\"", "'", "“", "‘")
        and text[-1] in ("\"", "'", "”", "’")
    ):
        text = text[1:-1].strip()

    if not text:
        raise ValueError("AI 未返回有效内容")
    return text


def _sanitize_suggest_output(raw: str) -> str:
    """
    suggest 模式：保留结构化清单，仅做最浅清洗。
      - 剥离围栏 / 前导语
      - 不剥离引号（清单内可能包含引用）
    """
    text = raw.strip()
    if not text:
        raise ValueError("AI 未返回有效内容")

    if text.startswith("```"):
        first_newline = text.find("\n")
        if first_newline != -1:
            text = text[first_newline + 1 :]
        if text.endswith("```"):
            text = text[: -3]
        text = text.strip()

    for prefix in (
        "以下是建议:", "以下是建议：",
        "Here are the suggestions:",
    ):
        if text.startswith(prefix):
            text = text[len(prefix) :].lstrip()

    if not text:
        raise ValueError("AI 未返回有效内容")
    return text


def _resolve_strength(
    rewrite_strength: Optional[int],
    rewrite_level: Optional[str],
) -> int:
    """
    解析最终使用的 strength：
      - 显式传入 rewrite_strength → 钳制到 [0, 100]
      - 否则 fallback 到 rewrite_level 的映射（D1.1 兼容）
      - 否则默认 50
    """
    if rewrite_strength is not None:
        return coerce_strength(rewrite_strength, default=50)
    mapped = level_to_strength(rewrite_level)
    if mapped is not None:
        return mapped
    return 50


async def rewrite_text(
    text: str,
    style: str,
    rewrite_mode: str = "polish",
    rewrite_strength: Optional[int] = None,
    rewrite_level: Optional[str] = None,
    custom_instruction: Optional[str] = None,
    provider_id: Optional[str] = None,
) -> str:
    """
    AI 润色 / 建议 / 草稿入口：返回纯文本结果。

    参数：
      - rewrite_mode：polish / suggest / draft
      - rewrite_strength：主字段，0-100
      - rewrite_level：兼容 D1.1 旧字段；仅在 rewrite_strength 缺省时降级使用

    Raises:
        ValueError — 输入校验失败
        LLMClientError — LLM 调用失败 / 空返回
    """
    if not isinstance(text, str):
        raise ValueError("text 必须是字符串")
    cleaned = text.strip()
    if not cleaned:
        raise ValueError("text 不能为空")
    if len(cleaned) > MAX_REWRITE_TEXT_CHARS:
        raise ValueError(f"text 超过 {MAX_REWRITE_TEXT_CHARS} 字上限")
    if style not in STYLE_WHITELIST:
        raise ValueError(f"style 不在白名单内: {STYLE_WHITELIST}")
    if rewrite_mode not in MODE_WHITELIST:
        raise ValueError(f"rewrite_mode 不在白名单内: {MODE_WHITELIST}")
    if rewrite_level is not None and rewrite_level not in LEVEL_WHITELIST:
        raise ValueError(f"rewrite_level 不在白名单内: {LEVEL_WHITELIST}")
    if rewrite_strength is not None:
        if not isinstance(rewrite_strength, int):
            raise ValueError("rewrite_strength 必须是整数")
        if rewrite_strength < STRENGTH_MIN or rewrite_strength > STRENGTH_MAX:
            raise ValueError(
                f"rewrite_strength 必须在 [{STRENGTH_MIN}, {STRENGTH_MAX}] 范围内"
            )
    if custom_instruction is not None:
        if not isinstance(custom_instruction, str):
            raise ValueError("custom_instruction 必须是字符串或 None")
        if len(custom_instruction) > MAX_CUSTOM_INSTRUCTION_CHARS:
            raise ValueError(
                f"custom_instruction 超过 {MAX_CUSTOM_INSTRUCTION_CHARS} 字上限"
            )

    final_strength = _resolve_strength(rewrite_strength, rewrite_level)

    messages = build_rewrite_messages(
        text=cleaned,
        style=style,
        rewrite_mode=rewrite_mode,
        rewrite_strength=final_strength,
        custom_instruction=custom_instruction,
    )

    raw = await complete_chat(
        messages=messages,
        temperature=_temperature_for_strength(final_strength, rewrite_mode),
        max_tokens=2048,
        timeout=60.0,
        provider_id=provider_id,
    )
    if raw is None or not raw.strip():
        raise LLMClientError("AI 未返回有效内容")

    try:
        if rewrite_mode == "suggest":
            return _sanitize_suggest_output(raw)
        return _sanitize_polish_or_draft_output(raw)
    except ValueError as exc:
        raise LLMClientError(str(exc))
