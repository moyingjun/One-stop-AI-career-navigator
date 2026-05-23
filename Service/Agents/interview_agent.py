"""
Service/Agents/interview_agent.py — 模拟面试 Agent

包含两个 Agent：
  - InterviewChatAgent   — 面试对话流式 Agent（SSE 推送）
  - InterviewEvalAgent   — 面试结束后的六维评分 Agent（非流式）
"""

import json
import re
import time
from typing import AsyncGenerator, List, Optional

from Service.Agents.base_agent import BaseAgent
from Service.Agents.prompts.interview_prompts import (
    EVALUATE_SYSTEM_PROMPT,
    build_interview_messages,
)
from Service.Utils.llm_client import LLMClientError, stream_chat


class InterviewChatAgent(BaseAgent):
    """
    面试对话流式 Agent。

    使用自定义 stream() 实现以支持心跳保活（超过 15 秒无内容时发送 ping）。
    """

    temperature: float = 0.7
    max_tokens: int = 4096
    stream_timeout: float = 120.0

    def build_messages(
        self,
        user_query: str = "",
        history: List[dict] = None,
        resume_text: str = "",
        jd_text: str = "",
        target_job: str = "",
        difficulty: str = "standard",
        **kwargs,
    ) -> List[dict]:
        """构建面试对话消息列表。"""
        return build_interview_messages(
            user_query=user_query,
            history=history or [],
            resume_text=resume_text,
            jd_text=jd_text,
            target_job=target_job,
            difficulty=difficulty,
        )

    async def stream(self, **kwargs) -> AsyncGenerator[str, None]:
        """
        面试流式响应生成器（SSE 格式）。

        在基类 stream() 基础上增加心跳保活：
        超过 15 秒无内容时发送 ': ping' 保持连接。

        SSE 事件格式：
          event: message — 正常内容片段
          event: error   — 错误信息
          event: done    — 流结束标志
          ': ping'       — 心跳保活
        """
        messages = self.build_messages(**kwargs)
        last_yield_time = time.time()

        try:
            async for content_chunk in stream_chat(
                messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                timeout=self.stream_timeout,
            ):
                # 超过 15 秒无内容时发送心跳保活
                if time.time() - last_yield_time > 15:
                    yield ": ping\n\n"
                    last_yield_time = time.time()

                # 面试模块使用 event: message 格式（与前端 PremiumInterview.vue 保持一致）
                yield f'event: message\ndata: {json.dumps({"content": content_chunk}, ensure_ascii=False)}\n\n'
                last_yield_time = time.time()

        except LLMClientError as exc:
            yield f'event: error\ndata: {json.dumps({"content": str(exc)}, ensure_ascii=False)}\n\n'
        except Exception as exc:
            import httpx
            if isinstance(exc, httpx.ReadTimeout):
                yield 'event: error\ndata: {"content":"模型思考超时，请稍后重试"}\n\n'
            else:
                print(f"[InterviewChatAgent] 未预期异常: {type(exc).__name__}: {exc}")
                yield 'event: error\ndata: {"content":"模型服务暂时不可用，请稍后重试"}\n\n'
        finally:
            yield 'event: done\ndata: {}\n\n'


class InterviewEvalAgent(BaseAgent):
    """
    面试评估 Agent（非流式）。

    读取完整面试对话历史，输出六维评分 JSON。
    """

    temperature: float = 0.1
    max_tokens: int = 2048

    def build_messages(
        self,
        history: List[dict] = None,
        resume_text: str = "",
        jd_text: str = "",
        **kwargs,
    ) -> List[dict]:
        """
        构建评估消息列表。

        将完整对话历史、简历、JD 合并为单条 user 消息，
        System Prompt 要求模型只输出 JSON。
        """
        history_text = "\n".join([
            f"{m.get('role', 'unknown')}: {m.get('content', '')}"
            for m in (history or [])
        ])
        resume_section = f"\n\n【候选人简历】：\n{resume_text}" if resume_text else ""
        jd_section = f"\n\n【目标岗位 JD】：\n{jd_text}" if jd_text else ""
        eval_user_prompt = (
            f"请对以下面试对话记录进行六维打分，输出标准 JSON：\n"
            f"{history_text}{resume_section}{jd_section}"
        )
        merged = (
            f"{EVALUATE_SYSTEM_PROMPT}\n\n"
            "====================\n\n"
            "【最高指令】：禁止复述我提供的材料，直接输出你的核心结论！\n\n"
            f"{eval_user_prompt}"
        )
        return [{"role": "user", "content": merged}]

    @staticmethod
    def extract_scores(text: str) -> Optional[dict]:
        """
        从模型回复中提取六维评分 JSON。

        尝试多种提取策略：代码块 → 直接解析 → 正则提取 → 清理后解析。

        参数：
            text — 模型原始回复文本

        返回：
            dict — 包含六维评分的字典，提取失败时返回 None
        """
        # 策略 1：提取 ```json ... ``` 代码块
        code_block_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
        if code_block_match:
            text = code_block_match.group(1).strip()

        # 策略 2：直接解析
        try:
            result = json.loads(text.strip())
            if isinstance(result, dict):
                return result
        except (json.JSONDecodeError, ValueError):
            pass

        # 策略 3：正则提取最后一个 JSON 对象
        matches = re.findall(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
        for match in reversed(matches):
            try:
                result = json.loads(match)
                if isinstance(result, dict):
                    return result
            except (json.JSONDecodeError, ValueError):
                continue

        # 策略 4：清理后解析
        cleaned = re.sub(r'^[^{]*', '', text.strip())
        cleaned = re.sub(r'[^}]*$', '', cleaned)
        cleaned = re.sub(r',\s*}', '}', cleaned)
        cleaned = re.sub(r',\s*]', ']', cleaned)
        try:
            result = json.loads(cleaned)
            if isinstance(result, dict):
                return result
        except (json.JSONDecodeError, ValueError):
            pass

        return None

    async def evaluate(
        self,
        history: List[dict],
        resume_text: str = "",
        jd_text: str = "",
        difficulty: str = "standard",
        user_id: Optional[int] = None,
    ) -> Optional[dict]:
        """
        执行面试评估，返回六维评分字典。

        参数：
            history     — 完整面试对话历史
            resume_text — 候选人简历
            jd_text     — 岗位描述
            difficulty  — 面试难度（用于数据库分类存档）
            user_id     — 当前用户 ID

        返回：
            dict — 包含六维评分和 comment 的字典，失败时返回 None
        """
        raw_reply = await self.complete(
            history=history,
            resume_text=resume_text,
            jd_text=jd_text,
        )

        if not raw_reply:
            return None

        result = self.extract_scores(raw_reply)
        if not result:
            return None

        required_keys = ["professional", "logic", "communication", "problemSolving", "potential", "resilience"]
        if not all(k in result for k in required_keys):
            return None

        # 写入历史记录
        try:
            from Service.Utils.databases.db import insert_record

            insert_record(
                category=f"interview_{difficulty}",
                user_input=f"面试对话 {len(history)} 轮",
                ai_result=result.get("comment", ""),
                scores=result,
                extra_data={
                    "resume_text": resume_text[:2000] if resume_text else "",
                    "jd_text": jd_text[:1000] if jd_text else "",
                    "difficulty": difficulty,
                },
                chat_history=history,
                user_id=user_id,
            )
        except Exception as db_err:
            print(f"[InterviewEvalAgent] 数据库写入失败: {db_err}")

        return result
