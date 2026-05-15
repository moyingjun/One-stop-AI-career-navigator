"""
Service/career_service.py — 职业规划业务层

Router 层调用此模块，不直接操作 Agent 或数据库。
"""

from typing import AsyncGenerator, List, Optional

from Service.Agents.career_agent import CareerPlanAgent, CareerSuggestAgent

# 模块级单例
_plan_agent = CareerPlanAgent()
_suggest_agent = CareerSuggestAgent()


async def career_plan_stream(
    resume_text: str,
    user_confusion: str,
    user_id: Optional[int] = None,
) -> AsyncGenerator[str, None]:
    """
    职业规划流式生成器。

    参数：
        resume_text    — 候选人简历文本
        user_confusion — 用户的职业困惑或期望
        user_id        — 当前用户 ID（游客为 None）

    Yields:
        str — SSE 格式字符串（reply / error / done 事件）
    """
    async for chunk in _plan_agent.stream(
        resume_text=resume_text,
        user_confusion=user_confusion,
        user_id=user_id,
    ):
        yield chunk


async def get_career_suggestions(resume_text: str) -> List[str]:
    """
    生成职业推荐问题列表（非流式）。

    参数：
        resume_text — 候选人简历文本

    返回：
        包含 4 个推荐问题的字符串列表；生成失败时返回默认兜底列表
    """
    return await _suggest_agent.get_suggestions(resume_text)
