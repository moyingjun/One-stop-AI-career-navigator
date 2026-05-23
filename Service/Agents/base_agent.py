"""
Service/Agents/base_agent.py — Agent 基类

封装流式和非流式 LLM 调用的通用逻辑，所有具体 Agent 继承此类。
子类只需实现 build_messages() 方法，专注于 Prompt 构建。
"""

import time
from typing import AsyncGenerator, List, Optional

from Service.Utils.llm_client import LLMClientError, complete_chat, stream_chat
from Service.Utils.sse_utils import sse_done, sse_error, sse_reply


class BaseAgent:
    """
    Agent 基类。

    子类必须实现：
        build_messages() — 根据业务参数构建 OpenAI 格式的消息列表

    子类可覆盖：
        temperature  — 采样温度（默认 0.7）
        max_tokens   — 最大生成 token 数（默认 4096）
        stream_timeout — 流式请求超时秒数（默认 120.0）
    """

    temperature: float = 0.7
    max_tokens: int = 4096
    stream_timeout: float = 120.0

    def build_messages(self, **kwargs) -> List[dict]:
        """
        构建发送给 LLM 的消息列表。子类必须实现此方法。

        返回：
            OpenAI 格式的消息列表 [{"role": "...", "content": "..."}]
        """
        raise NotImplementedError("子类必须实现 build_messages()")

    async def stream(self, **kwargs) -> AsyncGenerator[str, None]:
        """
        流式调用 LLM，yield SSE 格式的字符串。

        调用 build_messages() 构建消息，通过 llm_client.stream_chat() 获取增量片段，
        将每个片段包装为 SSE reply 事件后 yield 给调用方。

        流结束时发送 done 事件；发生异常时发送 error 事件。

        Yields:
            str — SSE 格式字符串（reply / error / done 事件）
        """
        messages = self.build_messages(**kwargs)
        full_text = ""

        try:
            async for content_chunk in stream_chat(
                messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                timeout=self.stream_timeout,
            ):
                full_text += content_chunk
                yield sse_reply(content_chunk)

        except LLMClientError as exc:
            yield sse_error(str(exc))
        except Exception as exc:
            import httpx
            if isinstance(exc, httpx.ReadTimeout):
                yield sse_error("大模型思考超时，请稍后重试")
            elif isinstance(exc, httpx.ConnectError):
                yield sse_error("无法连接模型服务，请检查网络或 LLM 配置")
            else:
                print(f"[{self.__class__.__name__}] stream 未预期异常: {type(exc).__name__}: {exc}")
                yield sse_error("模型服务暂时不可用，请稍后重试")

        # 将完整文本和 done 事件通过 on_stream_complete 回调处理
        record_id = await self.on_stream_complete(full_text, **kwargs)
        yield sse_done(record_id=record_id)

    async def on_stream_complete(self, full_text: str, **kwargs) -> Optional[int]:
        """
        流式输出完成后的回调钩子（可选实现）。

        子类可覆盖此方法来执行数据库写入、分数提取等后处理逻辑。

        参数：
            full_text — 完整的 AI 回复文本
            **kwargs  — 与 stream() 相同的业务参数

        返回：
            record_id — 写入数据库后的记录 ID（可选）
        """
        return None

    async def complete(self, **kwargs) -> Optional[str]:
        """
        非流式调用 LLM，返回完整回复字符串。

        参数：
            **kwargs — 传递给 build_messages() 的业务参数

        返回：
            str  — 模型完整回复
            None — 调用失败时
        """
        messages = self.build_messages(**kwargs)
        try:
            return await complete_chat(
                messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
        except LLMClientError as exc:
            print(f"[{self.__class__.__name__}] 非流式调用失败: {exc}")
            return None
        except Exception as exc:
            print(f"[{self.__class__.__name__}] 非流式调用未预期异常: {type(exc).__name__}: {exc}")
            return None
