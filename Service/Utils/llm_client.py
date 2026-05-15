"""
Service/Utils/llm_client.py — DeepSeek LLM 调用封装（唯一入口）

所有 Agent 和 Service 通过此模块调用 DeepSeek API，
不再各自维护 httpx 调用逻辑、header 构建和超时配置。

提供两个公开函数：
  - stream_chat()     — 流式调用，返回 AsyncGenerator[str, None]，每次 yield 一个 content 片段
  - complete_chat()   — 非流式调用，返回完整回复字符串
"""

import json
from typing import AsyncGenerator, List, Optional

import httpx

from Settings.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL_NAME


def _build_headers() -> dict:
    """构建 DeepSeek API 请求头。"""
    return {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }


def _build_payload(
    messages: List[dict],
    stream: bool,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> dict:
    """构建统一的请求 payload。"""
    return {
        "model": DEEPSEEK_MODEL_NAME,
        "messages": messages,
        "stream": stream,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }


async def stream_chat(
    messages: List[dict],
    temperature: float = 0.7,
    max_tokens: int = 4096,
    timeout: float = 120.0,
) -> AsyncGenerator[str, None]:
    """
    流式调用 DeepSeek，逐块 yield content 字符串片段。

    调用方负责将 yield 出的片段组装成 SSE 事件，
    此函数只负责网络通信和 JSON 解析，不关心 SSE 格式。

    参数：
        messages    — OpenAI 格式的消息列表
        temperature — 采样温度
        max_tokens  — 最大生成 token 数
        timeout     — 请求超时秒数

    Yields:
        str — 每个增量 content 片段

    Raises:
        httpx.ReadTimeout  — 读取超时
        httpx.ConnectError — 连接失败
        RuntimeError       — API Key 未配置或接口返回非 200
    """
    if not DEEPSEEK_API_KEY:
        raise RuntimeError("DEEPSEEK_API_KEY 未配置，请在 .env 中设置")

    payload = _build_payload(messages, stream=True, temperature=temperature, max_tokens=max_tokens)

    async with httpx.AsyncClient(timeout=timeout, proxy=None) as client:
        async with client.stream(
            "POST",
            DEEPSEEK_BASE_URL,
            json=payload,
            headers=_build_headers(),
        ) as response:
            if response.status_code != 200:
                error_body = (await response.aread()).decode("utf-8", errors="ignore")
                raise RuntimeError(f"DeepSeek API 返回 {response.status_code}: {error_body}")

            async for line in response.aiter_lines():
                if not line or not line.startswith("data:"):
                    continue

                data_str = line[5:].strip()
                if data_str == "[DONE]":
                    break

                try:
                    parsed = json.loads(data_str)
                    content = parsed.get("choices", [{}])[0].get("delta", {}).get("content", "")
                    if content:
                        yield content
                except json.JSONDecodeError:
                    # 跳过无法解析的行，不中断流
                    continue


async def complete_chat(
    messages: List[dict],
    temperature: float = 0.7,
    max_tokens: int = 4096,
    timeout: float = 60.0,
) -> Optional[str]:
    """
    非流式调用 DeepSeek，返回完整回复字符串。

    参数：
        messages    — OpenAI 格式的消息列表
        temperature — 采样温度
        max_tokens  — 最大生成 token 数
        timeout     — 请求超时秒数

    返回：
        str  — 模型完整回复
        None — API Key 未配置时

    Raises:
        RuntimeError — 接口返回非 200 时
    """
    if not DEEPSEEK_API_KEY:
        return None

    payload = _build_payload(messages, stream=False, temperature=temperature, max_tokens=max_tokens)

    async with httpx.AsyncClient(timeout=timeout, proxy=None) as client:
        response = await client.post(DEEPSEEK_BASE_URL, json=payload, headers=_build_headers())
        if response.status_code != 200:
            raise RuntimeError(f"DeepSeek API 返回 {response.status_code}: {response.text}")
        return response.json()["choices"][0]["message"]["content"]
