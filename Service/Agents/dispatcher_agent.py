"""
Service/Agents/dispatcher_agent.py — Agent Dispatcher（多专家路由 Agent）

负责：
  1. 根据用户输入关键词路由到对应专家 Agent
  2. 异步调用 RAG 知识库，注入 Top-K=3 的 <context> 块（严格限制防 Token 爆炸）
  3. 流式输出并写入历史记录

RAG 注入原则：
  - Top-K 严格限制为 3，防止 Token 爆炸
  - <context> 块注入 System Prompt，附带防御提示词
  - 游客模式（user_id=None）跳过 RAG 检索
"""

from enum import Enum
from typing import AsyncGenerator, List, Optional

from Service.Agents.prompts.agent_prompts import (
    AGENT_LABELS,
    AGENT_SYSTEM_PROMPTS,
    build_agent_user_prompt,
)
from Service.Utils.llm_client import LLMClientError, stream_chat
from Service.Utils.sse_utils import sse_done, sse_error, sse_event, sse_meta, sse_warning


class AgentType(str, Enum):
    """专家 Agent 类型枚举。"""
    P8_INTERVIEWER = "p8_interviewer"
    RESUME_MENTOR = "resume_mentor"
    GAOKAO_ADVISOR = "gaokao_advisor"
    GENERAL_ASSISTANT = "general_assistant"


# 高考/升学相关关键词
_GAOKAO_KEYWORDS = [
    "高考", "志愿", "填报", "专业", "院校", "大学", "本科", "专科",
    "考研", "升学", "录取", "分数线", "位次", "张雪峰",
]
# 简历相关关键词
_RESUME_KEYWORDS = [
    "简历", "resume", "jd", "岗位描述", "润色", "优化经历",
    "star", "项目经历怎么写", "自我评价", "求职材料",
]
# 面试相关关键词
_INTERVIEW_KEYWORDS = [
    "面试", "interview", "八股", "追问", "拷打", "p8",
    "高压", "技术问题", "模拟面", "项目难点", "手撕",
]


def route_agent(user_input: str) -> AgentType:
    """
    轻量 Router：基于关键词规则将用户输入路由到对应专家 Agent。
    优先级：高考/升学 > 简历 > 面试 > 通用助理
    """
    text = user_input.lower()
    if any(kw in text for kw in _GAOKAO_KEYWORDS):
        return AgentType.GAOKAO_ADVISOR
    if any(kw in text for kw in _RESUME_KEYWORDS):
        return AgentType.RESUME_MENTOR
    if any(kw in text for kw in _INTERVIEW_KEYWORDS):
        return AgentType.P8_INTERVIEWER
    return AgentType.GENERAL_ASSISTANT


async def stream_dispatcher_response(
    user_input: str,
    history: List,
    resume_text: str = "",
    target_job: str = "",
    jd_text: str = "",
    user_id: Optional[int] = None,
    db=None,  # AsyncSession，游客模式时为 None
    persist: bool = False,  # 是否自动保存到历史（Dashboard ChatDock 默认不保存）
    provider_id: Optional[str] = None,  # LLM Provider 切换
) -> AsyncGenerator[str, None]:
    """
    Agent Dispatcher 流式响应生成器。

    流程：
      1. 路由到对应专家 Agent
      2. 发送 meta 事件（告知前端当前 Agent 类型）
      3. 异步调用 RAG 知识库（Top-K=3，游客模式跳过）
      4. 将 <context> 块注入 System Prompt
      5. 流式调用 LLM
      6. 写入历史记录，发送 done 事件

    参数：
        user_input  — 用户当前输入
        history     — 历史消息列表
        resume_text — 用户简历（可为空）
        target_job  — 目标岗位（可为空）
        jd_text     — 岗位描述（可为空）
        user_id     — 当前用户 ID（None = 游客模式，跳过 RAG）
        db          — 异步 SQLAlchemy Session（游客模式时为 None）

    Yields:
        str — SSE 格式字符串
    """
    agent_type = route_agent(user_input)

    # 发送 meta 事件：告知前端当前 Agent 类型
    yield sse_meta(
        agent=agent_type.value,
        agent_label=AGENT_LABELS[agent_type.value],
        rag_enabled=False,
    )

    full_text = ""
    context_block = ""

    try:
        # ── RAG 检索（Top-K=3，严格限制防 Token 爆炸）──
        # 游客模式（user_id=None）或无 db session 时跳过
        if user_id is not None and db is not None:
            try:
                from Service.Services.rag_service import build_context_block

                context_block = await build_context_block(
                    query=user_input,
                    user_id=user_id,
                    top_k=3,  # 🚨 严格限制 k=3，防 Token 爆炸
                    db=db,
                )

                if context_block:
                    yield sse_meta(
                        agent=agent_type.value,
                        agent_label=AGENT_LABELS[agent_type.value],
                        rag_enabled=True,
                    )
            except Exception as rag_exc:
                print(f"[DispatcherAgent] RAG 检索失败，继续无知识库回答: {rag_exc}")
                yield sse_warning(
                    f"知识库检索失败，已切换为普通回答：{rag_exc}",
                    rag_enabled=False,
                )

        # ── 构建消息列表 ──
        # context_block 已是 <context>...</context> 格式，注入 System Prompt
        base_system_prompt = AGENT_SYSTEM_PROMPTS.get(
            agent_type.value, AGENT_SYSTEM_PROMPTS["general_assistant"]
        )

        # 将 <context> 块追加到 System Prompt（而非 User Prompt），
        # 确保 LLM 在角色定义层面就感知到知识库内容
        if context_block:
            system_prompt = (
                f"{base_system_prompt}\n\n"
                "【知识库上下文防御指令】\n"
                "请优先依据下方 <context> 内的信息回答；若 <context> 内容与问题无关，依靠通用知识作答，不要编造。\n\n"
                f"{context_block}"
            )
        else:
            system_prompt = base_system_prompt

        user_prompt = build_agent_user_prompt(
            user_input=user_input,
            agent_type=agent_type.value,
            context_block="",  # context 已注入 system_prompt，此处不重复
            resume_text=resume_text,
            target_job=target_job,
            jd_text=jd_text,
            history=history,
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        # 高考顾问使用稍高温度以增加表达多样性
        temperature = 0.8 if agent_type == AgentType.GAOKAO_ADVISOR else 0.7

        async for content_chunk in stream_chat(messages, temperature=temperature, provider_id=provider_id):
            full_text += content_chunk
            yield sse_event("reply", {"payload": {"content": content_chunk}})

    except LLMClientError as exc:
        yield sse_error(str(exc))
    except Exception as exc:
        import httpx
        if isinstance(exc, httpx.ReadTimeout):
            yield sse_error("模型思考超时，请稍后重试")
        elif isinstance(exc, httpx.ConnectError):
            yield sse_error("无法连接模型服务，请检查网络或 LLM 配置")
        else:
            print(f"[DispatcherAgent] 流式对话未预期异常: {type(exc).__name__}: {exc}")
            yield sse_error("模型服务暂时不可用，请稍后重试")

    # ── 写入历史记录（仅当 persist=True 时自动保存）──
    record_id = None
    if full_text and persist and user_id is not None and db is not None:
        try:
            from Service.Utils.databases.db import insert_record

            record_id = await insert_record(
                db=db,
                category=f"agent_{agent_type.value}",
                user_input=user_input[:200],
                ai_result=full_text[:5000],
                extra_data={
                    "agent": agent_type.value,
                    "agent_label": AGENT_LABELS[agent_type.value],
                    "rag_enabled": bool(context_block),
                    "has_resume": bool(resume_text),
                    "has_jd": bool(jd_text),
                },
                chat_history=[msg.model_dump() for msg in history],
                user_id=user_id,
            )
        except Exception as db_exc:
            print(f"[DispatcherAgent] 历史记录写入失败: {db_exc}")

    yield sse_done(record_id=record_id, agent=agent_type.value, length=len(full_text))
