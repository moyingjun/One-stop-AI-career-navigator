"""
Service/Agents/resume_extract_agent.py — 简历抽取 Agent

职责单一:
  - 构造 messages(委托 prompts/resume_extract_prompts.py)
  - 调用 Service/Utils/llm_client.complete_chat
  - 不做契约校验 / 不做反编造比对(归 Service 层)

满足:
  - Requirement 5.1(Prompt 与代码解耦)
  - Requirement 5.3(`is_retry=True` 时附加 RETRY_REMINDER)
  - Requirement 11.6(LLM 调用唯一入口)
  - Requirement 4.8(超时 30s,实际超时控制由 Service 层套 asyncio.wait_for)

注意:本 Agent 不直接 import httpx;LLM 调用全部走 llm_client。

Hotfix 5:
  - 启用 allow_reasoning_fallback=True 让 Mimo / DeepSeek thinking 模型只返回
    reasoning_content 时仍能拿到 JSON 文本(普通 chat 接口不会受影响)。
  - 对 Mimo provider 注入 extra_body={"thinking": {"type": "disabled"}} 直接关掉思维链,
    既减少 latency 又让模型直接产 content,绕开 reasoning_content 路径。
  - 其他 provider(DeepSeek 等)不传 extra_body,不破坏既有调用。
"""

from __future__ import annotations

from typing import Any, Optional

from Service.Agents.prompts.resume_extract_prompts import build_extract_messages
from Service.Utils.llm_client import LLMClientError, complete_chat
from Service.Utils.llm_provider_config import get_provider


# ─────────────────────────────────────────────
# 简历抽取专用超时 / 模型参数(Hotfix 4 — 真实 Mimo / DeepSeek 抽取经常 > 30s,
# 但其他普通 chat 接口不应受影响,仍用 llm_client 默认值)
# ─────────────────────────────────────────────

# 第一次 LLM 调用预算:90s。Mimo / DeepSeek thinking 模型 200 字简历抽取通常 30-60s 完成,留够安全冗余。
RESUME_EXTRACT_LLM_TIMEOUT_SECONDS_FIRST = 90.0
# 重试预算:45s。第一次成功大概率没必要再让用户等满 90s。
RESUME_EXTRACT_LLM_TIMEOUT_SECONDS_RETRY = 45.0
# httpx 客户端层 timeout 必须比 asyncio.wait_for 大,确保超时由 asyncio 抛出 TimeoutError(进入兜底分支)而不是 httpx ReadTimeout。
RESUME_EXTRACT_HTTP_TIMEOUT_SECONDS = 100.0
# 简历 JSON 通常 ≤ 2500 token;给到 3072 留余量。原来 4096 容易让 thinking 模型把推理也写进 max_tokens 然后耗时翻倍。
RESUME_EXTRACT_MAX_TOKENS = 3072
# 结构化抽取要稳定,绝不能 0.7;0.1 既保留少量 paraphrase 空间又不会幻觉。
RESUME_EXTRACT_TEMPERATURE = 0.1


def _build_extra_body_for_provider(provider_id: Optional[str]) -> Optional[dict]:
    """
    根据 provider 决定是否注入 extra_body。

    - Mimo:注入 {"thinking": {"type": "disabled"}} 关闭思维链,提速 + 强制走 content 字段。
    - 其他 provider:不注入(避免破坏 DeepSeek 等无关 provider)。
    """
    try:
        provider = get_provider(provider_id)
    except Exception:  # noqa: BLE001
        provider = None
    if provider is None:
        return None
    pid = (provider.id or "").lower()
    base = (provider.base_url or "").lower()
    is_mimo = pid == "mimo" or "mimo" in base
    if is_mimo:
        return {"thinking": {"type": "disabled"}}
    return None


class ResumeExtractAgent:
    """简历结构化抽取 Agent。"""

    def __init__(self, provider_id: Optional[str] = None) -> None:
        self.provider_id = provider_id

    async def extract(
        self,
        plain_text: str,
        content_json: Any,
        is_retry: bool = False,
    ) -> str:
        """
        调用 LLM 完成单次抽取。

        Returns:
            原始 LLM 响应字符串(由 Service 层负责后续解析与校验)。

        Raises:
            LLMClientError — LLM 返回为空或调用失败。
        """
        messages = build_extract_messages(
            plain_text=plain_text,
            content_json=content_json,
            is_retry=is_retry,
        )
        extra_body = _build_extra_body_for_provider(self.provider_id)
        if extra_body:
            print(f"[resume-extract-agent] extra_body 启用={list(extra_body.keys())}")
        raw = await complete_chat(
            messages=messages,
            temperature=RESUME_EXTRACT_TEMPERATURE,
            max_tokens=RESUME_EXTRACT_MAX_TOKENS,
            timeout=RESUME_EXTRACT_HTTP_TIMEOUT_SECONDS,
            provider_id=self.provider_id,
            extra_body=extra_body,
            # Hotfix 5:Mimo / DeepSeek thinking 模型可能只产 reasoning_content,
            # 简历抽取属于结构化后台任务,允许 fallback;普通 chat / 面试 / 职业规划保持 False。
            allow_reasoning_fallback=True,
        )
        if raw is None or not raw.strip():
            raise LLMClientError("AI 未返回有效内容")
        return raw
