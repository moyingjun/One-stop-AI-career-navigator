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
) -> AsyncGenerator[str, None]:
    """
    面试对话流式生成器。

    参数：
        user_query  — 用户当前输入
        history     — 历史消息列表
        resume_text — 候选人简历（可为空）
        jd_text     — 岗位描述（可为空）
        target_job  — 目标岗位（可为空）
        difficulty  — 难度等级：beginner / standard / p8

    Yields:
        str — SSE 格式字符串
    """
    async for chunk in _chat_agent.stream(
        user_query=user_query,
        history=history or [],
        resume_text=resume_text,
        jd_text=jd_text,
        target_job=target_job,
        difficulty=difficulty,
    ):
        yield chunk


async def evaluate_interview(
    history: List[dict],
    resume_text: str = "",
    jd_text: str = "",
    difficulty: str = "standard",
    user_id: Optional[int] = None,
) -> Optional[dict]:
    """
    面试评估（非流式），返回六维评分字典。

    参数：
        history     — 完整面试对话历史
        resume_text — 候选人简历
        jd_text     — 岗位描述
        difficulty  — 面试难度（用于数据库分类存档）
        user_id     — 当前用户 ID

    返回：
        dict — 包含六维评分和 comment 的字典，失败时返回 None
    """
    return await _eval_agent.evaluate(
        history=history,
        resume_text=resume_text,
        jd_text=jd_text,
        difficulty=difficulty,
        user_id=user_id,
    )
