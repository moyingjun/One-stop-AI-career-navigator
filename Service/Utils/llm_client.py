"""
Service/Utils/llm_client.py — LLM 调用封装（唯一入口）

所有 Agent 和 Service 通过此模块调用 LLM API。

支持多 Provider 切换：
  - 通过 provider_id 参数指定使用哪个 Provider（mimo / deepseek / default）
  - provider_id 为 None / 不存在 / 未配置 → 静默回退默认 Provider
  - 配置详见 Service/Utils/llm_provider_config.py

错误边界设计：
  - 单条 chunk 解析失败 → continue 跳过，绝不 yield 到正文
  - HTTP 非 200 → raise LLMClientError（不 yield 文本）
  - 网络超时 / 连接失败 → raise LLMClientError
  - 调用方（Agent / Service）捕获 LLMClientError 并转换为 SSE error 事件
"""

import json
import traceback
from typing import AsyncGenerator, List, Optional

import httpx

from Service.Utils.llm_provider_config import LLMProvider, get_provider


# ─────────────────────────────────────────────
# 统一异常类
# ─────────────────────────────────────────────

class LLMClientError(Exception):
    """LLM 调用层统一异常。调用方需转换为 SSE event:error，绝不拼入 AI 正文。"""


# ─────────────────────────────────────────────
# 内部构建函数
# ─────────────────────────────────────────────

def _build_headers(provider: LLMProvider) -> dict:
    return {
        "Authorization": f"Bearer {provider.api_key}",
        "Content-Type": "application/json",
    }


def _build_payload(
    messages: List[dict],
    stream: bool,
    provider: LLMProvider,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> dict:
    return {
        "model": provider.model_name,
        "messages": messages,
        "stream": stream,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }


def _resolve_provider(provider_id: Optional[str]) -> LLMProvider:
    """根据 provider_id 解析 Provider；解析失败抛 LLMClientError。"""
    provider = get_provider(provider_id)
    if provider is None:
        raise LLMClientError("没有可用的 LLM Provider，请检查 .env 配置")
    if not provider.is_configured:
        raise LLMClientError(f"Provider {provider.id} 未配置 API Key")
    return provider


def _safe_extract_content(parsed: dict) -> Optional[str]:
    """
    安全提取 OpenAI / DeepSeek / MIMO 兼容格式中的 delta.content。

    严格校验：parsed 是 dict、choices 非空列表、choices[0] 是 dict、
    delta 是 dict、content 是非空字符串。任意失败均返回 None。

    跳过：tool_calls / function_call / annotations / reasoning_content /
          空 delta / finish_reason chunk。
    """
    if not isinstance(parsed, dict):
        return None

    choices = parsed.get("choices")
    if not isinstance(choices, list) or len(choices) == 0:
        return None

    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        return None

    if first_choice.get("finish_reason"):
        return None

    delta = first_choice.get("delta")
    if isinstance(delta, dict):
        content = delta.get("content")
        if isinstance(content, str) and content:
            return content
        return None

    message = first_choice.get("message")
    if isinstance(message, dict):
        content = message.get("content")
        if isinstance(content, str) and content:
            return content

    return None


# ─────────────────────────────────────────────
# 公开 API
# ─────────────────────────────────────────────

async def stream_chat(
    messages: List[dict],
    temperature: float = 0.7,
    max_tokens: int = 4096,
    timeout: float = 120.0,
    provider_id: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    """
    流式调用 LLM，逐块 yield content 字符串片段。

    Args:
        provider_id — 可选，指定 Provider；为 None 时使用默认 Provider。
                      不存在或未配置时静默回退默认 Provider。

    Raises:
        LLMClientError — 不可恢复的 LLM 调用失败
    """
    provider = _resolve_provider(provider_id)

    payload = _build_payload(
        messages, stream=True, provider=provider,
        temperature=temperature, max_tokens=max_tokens,
    )

    try:
        async with httpx.AsyncClient(timeout=timeout, proxy=None) as client:
            async with client.stream(
                "POST",
                provider.base_url,
                json=payload,
                headers=_build_headers(provider),
            ) as response:
                if response.status_code != 200:
                    error_body = (await response.aread()).decode("utf-8", errors="ignore")
                    print(f"[llm_client] {provider.id} HTTP {response.status_code}: {error_body[:300]}")
                    raise LLMClientError(f"模型服务返回 {response.status_code}")

                async for line in response.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue

                    data_str = line[5:].strip()
                    if not data_str:
                        continue
                    if data_str == "[DONE]":
                        break

                    try:
                        parsed = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
                    except Exception:
                        print(f"[llm_client] chunk 解析异常 data_str={data_str[:300]}")
                        traceback.print_exc()
                        continue

                    try:
                        content = _safe_extract_content(parsed)
                    except Exception:
                        print(f"[llm_client] _safe_extract_content 异常 chunk={data_str[:300]}")
                        traceback.print_exc()
                        continue

                    if content:
                        yield content

    except LLMClientError:
        raise
    except httpx.ReadTimeout:
        print(f"[llm_client] {provider.id} 流式读取超时")
        raise LLMClientError("模型思考超时，请稍后重试")
    except httpx.ConnectError as exc:
        print(f"[llm_client] {provider.id} 连接失败: {exc}")
        raise LLMClientError("无法连接模型服务，请检查网络或 LLM 配置")
    except Exception as exc:
        print(f"[llm_client] {provider.id} stream_chat 未预期异常: {type(exc).__name__}: {exc}")
        traceback.print_exc()
        raise LLMClientError(f"LLM 调用异常: {type(exc).__name__}")


async def complete_chat(
    messages: List[dict],
    temperature: float = 0.7,
    max_tokens: int = 4096,
    timeout: float = 60.0,
    provider_id: Optional[str] = None,
    extra_body: Optional[dict] = None,
    allow_reasoning_fallback: bool = False,
) -> Optional[str]:
    """
    非流式调用 LLM，返回完整回复字符串。

    Args:
        provider_id — 可选，指定 Provider；不传或不存在时使用默认 Provider。
        extra_body — 可选，附加到 request payload 顶层的字段（如 Mimo 的
                     {"thinking": {"type": "disabled"}}）。无关 provider 会忽略未识别字段，
                     失败概率极低；调用方可按 provider 决定是否传入。
        allow_reasoning_fallback — 默认 False。仅结构化抽取这种后台任务可设为 True，
                     普通 chat / 面试 / 职业规划绝不能开启，避免把模型思维链当作正文返回给用户。

    Raises:
        LLMClientError — 不可恢复的 LLM 调用失败
    """
    provider = _resolve_provider(provider_id)

    payload = _build_payload(
        messages, stream=False, provider=provider,
        temperature=temperature, max_tokens=max_tokens,
    )
    # 注入 extra_body(如 Mimo thinking disabled);保留原 payload 字段不被覆盖
    if isinstance(extra_body, dict):
        for k, v in extra_body.items():
            if k in payload:
                # 已存在的核心字段(messages / model / stream / temperature / max_tokens)不被外部覆盖
                continue
            payload[k] = v

    try:
        async with httpx.AsyncClient(timeout=timeout, proxy=None) as client:
            response = await client.post(
                provider.base_url,
                json=payload,
                headers=_build_headers(provider),
            )
    except httpx.ReadTimeout:
        raise LLMClientError("非流式调用超时")
    except httpx.ConnectError as exc:
        raise LLMClientError(f"无法连接模型服务: {exc}")
    except Exception as exc:
        raise LLMClientError(f"HTTP 请求异常: {type(exc).__name__}: {exc}")

    if response.status_code != 200:
        snippet = response.text[:200] if response.text else "(empty)"
        print(f"[llm_client] {provider.id} complete_chat HTTP {response.status_code}: {snippet}")
        raise LLMClientError(f"模型服务返回 {response.status_code}")

    try:
        data = response.json()
    except Exception as exc:
        raise LLMClientError(f"响应 JSON 解析失败: {exc}")

    choices = data.get("choices")
    if not isinstance(choices, list) or len(choices) == 0:
        keys = list(data.keys()) if isinstance(data, dict) else type(data).__name__
        print(f"[llm_client] complete_chat 响应缺少 choices,顶层 keys={keys}")
        raise LLMClientError("模型响应缺少 choices 字段")

    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        raise LLMClientError("choices[0] 不是 dict")

    message = first_choice.get("message")
    if not isinstance(message, dict):
        raise LLMClientError("choices[0].message 字段缺失或格式错误")

    content = message.get("content")
    reasoning_content = message.get("reasoning_content")

    has_content = isinstance(content, str) and content.strip()
    has_reasoning = isinstance(reasoning_content, str) and reasoning_content.strip()

    # 主路径:正常 content 字段。打印长度,不打印原文,避免泄露用户数据。
    if has_content:
        print(f"[llm_client] complete_chat content_len={len(content)}")
        return content

    # fallback 路径:仅结构化抽取等后台任务允许;普通聊天必须保持 None。
    if has_reasoning:
        if allow_reasoning_fallback:
            print(
                f"[llm_client] complete_chat content_empty reasoning_len={len(reasoning_content)}"
                f" 使用 reasoning_content fallback"
            )
            return reasoning_content
        print(
            f"[llm_client] complete_chat content_empty reasoning_len={len(reasoning_content)}"
            " allow_reasoning_fallback=False 不回退"
        )
        return None

    # 既无 content 也无 reasoning_content
    print(
        f"[llm_client] complete_chat 响应无 content,message keys={list(message.keys())}"
    )
    return None
