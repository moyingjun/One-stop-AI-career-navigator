"""
Service/Utils/llm_client.py — LLM 调用封装（唯一入口）

所有 Agent 和 Service 通过此模块调用 LLM API，
不再各自维护 httpx 调用逻辑、header 构建和超时配置。

支持通过 .env 切换不同 AI 模型（MIMO / DeepSeek / Claude 等），
只需修改 LLM_API_KEY / LLM_BASE_URL / LLM_MODEL_NAME。

提供公开函数：
  - stream_chat()     — 流式调用，返回 AsyncGenerator[str, None]，每次 yield 一个 content 片段
  - complete_chat()   — 非流式调用，返回完整回复字符串

错误边界设计：
  - 单条 chunk 解析失败 → continue 跳过，绝不 yield 到正文
  - HTTP 非 200 → raise LLMClientError（不 yield 文本）
  - 网络超时 / 连接失败 → raise LLMClientError（不 yield 文本）
  - 由调用方（Agent / Service）捕获 LLMClientError 并转换为 SSE error 事件
"""

import json
import traceback
from typing import AsyncGenerator, List, Optional

import httpx

from Settings.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL_NAME


# ─────────────────────────────────────────────
# 统一异常类
# ─────────────────────────────────────────────

class LLMClientError(Exception):
    """
    LLM 调用层统一异常。

    由 stream_chat / complete_chat 在以下情况抛出：
      - LLM_API_KEY 未配置
      - HTTP 非 200 响应
      - 网络超时 / 连接失败
      - 响应格式严重异常（非流式）

    调用方捕获后应转换为 SSE event:error 事件发送给前端，
    绝不允许将 LLMClientError 的 message 拼入 AI 正文内容。
    """


# ─────────────────────────────────────────────
# 内部构建函数
# ─────────────────────────────────────────────

def _build_headers() -> dict:
    return {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
    }


def _build_payload(
    messages: List[dict],
    stream: bool,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> dict:
    return {
        "model": LLM_MODEL_NAME,
        "messages": messages,
        "stream": stream,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }


def _safe_extract_content(parsed: dict) -> Optional[str]:
    """
    安全提取 OpenAI / DeepSeek / MIMO 兼容格式中的 delta.content。

    严格校验顺序：
      1. parsed 是 dict
      2. choices 存在且为非空列表
      3. choices[0] 是 dict
      4. delta 存在且为 dict
      5. content 是非空字符串

    任意校验失败均返回 None，调用方应 continue 跳过。

    以下 chunk 类型均返回 None（安全跳过）：
      - tool_calls / function_call / annotations
      - reasoning_content（忽略，不作为最终 content）
      - 空 delta
      - finish_reason chunk（标志结束，无 content）
    """
    if not isinstance(parsed, dict):
        return None

    choices = parsed.get("choices")
    if not isinstance(choices, list) or len(choices) == 0:
        return None

    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        return None

    # finish_reason chunk：choices[0].finish_reason 非空时表示流已完成，无内容
    if first_choice.get("finish_reason"):
        return None

    # 标准流式格式：choices[0].delta.content
    delta = first_choice.get("delta")
    if isinstance(delta, dict):
        content = delta.get("content")
        if isinstance(content, str) and content:
            return content
        # reasoning_content / tool_calls / annotations / 空 delta → 全部忽略
        return None

    # 兼容某些供应商在流中混入 message 字段（非标准，仅做最佳努力）
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
) -> AsyncGenerator[str, None]:
    """
    流式调用 LLM，逐块 yield content 字符串片段。

    只 yield 模型真实 content，绝不 yield 错误文本。

    错误处理：
      - 单条 chunk 解析失败 → 记录日志，continue 跳过，不中断流
      - HTTP 非 200 → raise LLMClientError（调用方负责发送 SSE error）
      - 网络超时 / 连接失败 → raise LLMClientError
      - LLM_API_KEY 未配置 → raise LLMClientError

    Raises:
        LLMClientError — 不可恢复的 LLM 调用失败
    """
    if not LLM_API_KEY:
        raise LLMClientError("LLM_API_KEY 未配置，请在 .env 中设置后重启服务")

    payload = _build_payload(messages, stream=True, temperature=temperature, max_tokens=max_tokens)

    try:
        async with httpx.AsyncClient(timeout=timeout, proxy=None) as client:
            async with client.stream(
                "POST",
                LLM_BASE_URL,
                json=payload,
                headers=_build_headers(),
            ) as response:
                if response.status_code != 200:
                    error_body = (await response.aread()).decode("utf-8", errors="ignore")
                    print(f"[llm_client] HTTP {response.status_code}: {error_body[:300]}")
                    raise LLMClientError(f"模型服务返回 {response.status_code}")

                async for line in response.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue

                    data_str = line[5:].strip()
                    if not data_str:
                        continue
                    if data_str == "[DONE]":
                        break

                    # ── 单条 chunk 解析防波堤：任何异常都只 continue ──
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
                    # None → tool_calls / empty delta / reasoning_content / finish_reason，跳过

    except LLMClientError:
        # 直接向上传播，调用方负责处理
        raise
    except httpx.ReadTimeout:
        print("[llm_client] 流式读取超时")
        raise LLMClientError("模型思考超时，请稍后重试")
    except httpx.ConnectError as exc:
        print(f"[llm_client] 连接失败: {exc}")
        raise LLMClientError("无法连接模型服务，请检查网络或 LLM 配置")
    except Exception as exc:
        print(f"[llm_client] stream_chat 未预期异常: {type(exc).__name__}: {exc}")
        traceback.print_exc()
        raise LLMClientError(f"LLM 调用异常: {type(exc).__name__}")


async def complete_chat(
    messages: List[dict],
    temperature: float = 0.7,
    max_tokens: int = 4096,
    timeout: float = 60.0,
) -> Optional[str]:
    """
    非流式调用 LLM，返回完整回复字符串。

    错误处理：
      - HTTP 非 200 → raise LLMClientError
      - choices 字段异常 → raise LLMClientError（含脱敏响应片段）
      - reasoning_content 不视为最终答案

    Raises:
        LLMClientError — 不可恢复的 LLM 调用失败
    """
    if not LLM_API_KEY:
        raise LLMClientError("LLM_API_KEY 未配置，请在 .env 中设置后重启服务")

    payload = _build_payload(messages, stream=False, temperature=temperature, max_tokens=max_tokens)

    try:
        async with httpx.AsyncClient(timeout=timeout, proxy=None) as client:
            response = await client.post(LLM_BASE_URL, json=payload, headers=_build_headers())
    except httpx.ReadTimeout:
        raise LLMClientError("非流式调用超时")
    except httpx.ConnectError as exc:
        raise LLMClientError(f"无法连接模型服务: {exc}")
    except Exception as exc:
        raise LLMClientError(f"HTTP 请求异常: {type(exc).__name__}: {exc}")

    if response.status_code != 200:
        # 打印脱敏片段（不含完整响应，避免泄露）
        snippet = response.text[:200] if response.text else "(empty)"
        print(f"[llm_client] complete_chat HTTP {response.status_code}: {snippet}")
        raise LLMClientError(f"模型服务返回 {response.status_code}")

    try:
        data = response.json()
    except Exception as exc:
        raise LLMClientError(f"响应 JSON 解析失败: {exc}")

    choices = data.get("choices")
    if not isinstance(choices, list) or len(choices) == 0:
        # 打印脱敏结构用于排错
        keys = list(data.keys()) if isinstance(data, dict) else type(data).__name__
        print(f"[llm_client] complete_chat 响应缺少 choices，顶层 keys={keys}")
        raise LLMClientError("模型响应缺少 choices 字段")

    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        raise LLMClientError("choices[0] 不是 dict")

    message = first_choice.get("message")
    if not isinstance(message, dict):
        raise LLMClientError("choices[0].message 字段缺失或格式错误")

    content = message.get("content")
    if isinstance(content, str) and content:
        return content

    # reasoning_content 不视为最终答案（Mimo 思维链字段）
    if message.get("reasoning_content") and not content:
        print("[llm_client] complete_chat 响应只含 reasoning_content，无 content，返回 None")
        return None

    if content is None:
        print(f"[llm_client] complete_chat message.content 为 None，message keys={list(message.keys())}")
        return None

    # content 是空字符串
    return content
