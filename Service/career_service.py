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
    provider_id: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    """职业规划流式生成器。"""
    async for chunk in _plan_agent.stream(
        resume_text=resume_text,
        user_confusion=user_confusion,
        user_id=user_id,
        provider_id=provider_id,
    ):
        yield chunk


async def get_career_suggestions(
    resume_text: str,
    provider_id: Optional[str] = None,
) -> List[str]:
    """生成职业推荐问题列表（非流式）。"""
    return await _suggest_agent.get_suggestions(resume_text, provider_id=provider_id)
