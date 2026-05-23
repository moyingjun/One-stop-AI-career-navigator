"""
Service/interview_service.py — 模拟面试业务层

Router 层调用此模块，不直接操作 Agent 或数据库。
"""

from typing import AsyncGenerator, List, Optional

from Service.Agents.interview_agent import InterviewChatAgent, InterviewEvalAgent

# 模块级单例
_chat_agent = InterviewChatAgent()
_eval_agent = InterviewEvalAgent()


async def interview_chat_stream(
    user_query: str,
    history: List[dict] = None,
    resume_text: str = "",
    jd_text: str = "",
    target_job: str = "",
    difficulty: str = "standard",
    provider_id: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    """面试对话流式生成器。"""
    async for chunk in _chat_agent.stream(
        user_query=user_query,
        history=history or [],
        resume_text=resume_text,
        jd_text=jd_text,
        target_job=target_job,
        difficulty=difficulty,
        provider_id=provider_id,
    ):
        yield chunk


async def evaluate_interview(
    history: List[dict],
    resume_text: str = "",
    jd_text: str = "",
    difficulty: str = "standard",
    user_id: Optional[int] = None,
    provider_id: Optional[str] = None,
) -> Optional[dict]:
    """面试评估（非流式），返回六维评分字典。"""
    return await _eval_agent.evaluate(
        history=history,
        resume_text=resume_text,
        jd_text=jd_text,
        difficulty=difficulty,
        user_id=user_id,
        provider_id=provider_id,
    )
