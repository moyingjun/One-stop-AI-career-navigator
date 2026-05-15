"""
Service/Utils/sse_utils.py — SSE 事件格式化工具

统一全项目的 SSE 输出格式，消除各 Router/Agent 中重复的格式化代码。

SSE 事件规范（全项目统一）：
  event: meta    — 元信息（agent 类型、知识库状态等）
  event: reply   — 正常内容片段（流式输出）
  event: warning — 非致命警告（如 RAG 降级）
  event: error   — 错误信息
  event: done    — 流结束标志（始终发送）
"""

import json
from typing import Any, Optional


def sse_event(event: str, payload: dict) -> str:
    """
    生成标准 SSE 事件字符串。

    格式：
        event: {event}
        data: {json}

    参数：
        event   — 事件名称（reply / meta / warning / error / done）
        payload — 事件数据字典

    返回：
        符合 SSE 规范的字符串（以双换行结尾）
    """
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def sse_reply(content: str) -> str:
    """生成 reply 事件（正常内容片段）。"""
    return sse_event("reply", {"payload": {"content": content}})


def sse_error(message: str) -> str:
    """生成 error 事件。"""
    return sse_event("error", {"payload": {"content": message}})


def sse_warning(message: str, **extra: Any) -> str:
    """生成 warning 事件，支持附加额外字段。"""
    payload: dict = {"payload": {"content": message, **extra}}
    return sse_event("warning", payload)


def sse_done(record_id: Optional[int] = None, **extra: Any) -> str:
    """
    生成 done 事件（流结束标志）。

    参数：
        record_id — 本次对话写入数据库后的记录 ID（可选）
        **extra   — 其他附加字段
    """
    payload: dict = {"payload": {**extra}}
    if record_id is not None:
        payload["payload"]["record_id"] = record_id
    return sse_event("done", payload)


def sse_meta(**fields: Any) -> str:
    """生成 meta 事件（元信息，如 agent 类型、知识库状态）。"""
    return sse_event("meta", {"payload": fields})
