"""
Service/resume_service.py — 简历诊断业务层

Router 层调用此模块，不直接操作 Agent 或数据库。
"""

from typing import AsyncGenerator, Optional

from Service.Agents.resume_agent import ResumeDiagnosisAgent

# 模块级单例，避免每次请求重复实例化
_resume_agent = ResumeDiagnosisAgent()


async def diagnose_resume_stream(
    resume_text: str,
    target_role: str = "",
    jd_text: str = "",
    user_id: Optional[int] = None,
) -> AsyncGenerator[str, None]:
    """
    简历诊断流式生成器。

    参数：
        resume_text — 候选人简历文本
        target_role — 目标岗位名称
        jd_text     — 岗位描述（可为空）
        user_id     — 当前用户 ID（游客为 None）

    Yields:
        str — SSE 格式字符串（reply / error / done 事件）
    """
    async for chunk in _resume_agent.stream(
        resume_text=resume_text,
        target_role=target_role,
        jd_text=jd_text,
        user_id=user_id,
    ):
        yield chunk
