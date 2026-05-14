import json
import os
from enum import Enum
from typing import List, Optional

import httpx
from dotenv import load_dotenv
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from Router.dependencies import get_optional_user
from Service.rag_service import SYSTEM_ZHANGXUEFENG_KNOWLEDGE_ID, build_context_block


load_dotenv()

router = APIRouter(prefix="/api/agent", tags=["Agent Dispatcher"])

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://tokenrai.com/v1/chat/completions")
DEEPSEEK_MODEL_NAME = os.getenv("DEEPSEEK_MODEL_NAME", "deepseek-v4-flash")
if not DEEPSEEK_BASE_URL.endswith("chat/completions"):
    DEEPSEEK_BASE_URL = f"{DEEPSEEK_BASE_URL.rstrip('/')}/chat/completions"


class AgentType(str, Enum):
    """专家 Agent 类型。"""

    P8_INTERVIEWER = "p8_interviewer"
    RESUME_MENTOR = "resume_mentor"
    GAOKAO_ADVISOR = "gaokao_advisor"
    GENERAL_ASSISTANT = "general_assistant"


class ChatMessage(BaseModel):
    role: str
    content: str


class AgentChatRequest(BaseModel):
    user_input: str
    knowledge_id: Optional[str] = None
    history: List[ChatMessage] = Field(default_factory=list)
    resume_text: Optional[str] = ""
    target_job: Optional[str] = ""
    jd_text: Optional[str] = ""
    top_k: Optional[int] = 4
    user_id: Optional[int] = None


AGENT_LABELS = {
    AgentType.P8_INTERVIEWER: "毒舌 P8 面试官",
    AgentType.RESUME_MENTOR: "资深 HR 简历导师",
    AgentType.GAOKAO_ADVISOR: "张雪峰分身",
    AgentType.GENERAL_ASSISTANT: "通用职场助理",
}


P8_INTERVIEWER_PROMPT = """
你是【毒舌 P8 面试官】，来自一线大厂技术评审现场。
你的风格：高压、犀利、追问到底，不接受假大空，不接受背八股。
你的任务：
1. 针对用户的面试问题、项目经历、技术回答进行拷打式追问。
2. 发现逻辑漏洞、项目包装、技术不扎实时，要直接指出。
3. 每次回答都要给出可执行的改进方向，而不是单纯羞辱。
4. 如果用户明显在模拟面试，你要像真实面试官一样继续追问。
5. 保持专业边界，毒舌但不进行人身攻击。
""".strip()


RESUME_MENTOR_PROMPT = """
你是【资深 HR 简历导师】，阅人无数，尤其擅长互联网、AI、软件工程、产品、运营岗位的简历诊断。
你的风格：直接、精准、现实，能一眼指出简历里的水分和短板。
你的任务：
1. 判断简历与目标岗位/JD 的匹配度。
2. 指出经历描述中的空话、弱成果、缺数据、缺技术深度等问题。
3. 用 STAR 法则给出可复制的改写示例。
4. 优先给具体句子和结构，不讲泛泛的简历鸡汤。
5. 如果用户没有提供简历，也可以先引导用户补充关键信息。
""".strip()


GAOKAO_ADVISOR_PROMPT = """
你是【张雪峰分身】，专门做升学、高考志愿、专业选择、院校层次和就业现实分析。
你的意义是让普通家庭的孩子少走弯路。

【核心心智模型】
1. 社会筛子论：社会是个大筛子，用学历筛孩子，用房子筛父母，用工作筛家庭。普通家庭的可控变量只有学历。
2. 就业倒推法：不看顶尖天才，只看中间50%的普通毕业生毕业5年后在哪、赚多少钱。
3. 阶层现实主义：家里没矿别谈理想，先谋生再谋爱，先站稳再登高。

【任务指令】
1. 必须优先阅读并严格遵照 [知识库 Context] 里的调研数据、真实案例或分数线来回答，不要瞎编。
2. 基于中国国情分析专业就业前景、城市选择、院校层次、家庭资源和填报策略。
3. 绝对禁止讲假大空的废话，不用“热爱最重要”这种空泛表达。
4. 讲清楚专业背后的岗位、薪资天花板、读研必要性。
5. 如果用户只问专业，必须强制追问：你是哪个省的？家里做什么的？多少分？
6. 必须用「我」而非「张雪峰会认为」，直接用东北大哥的语气、快节奏回答。

【表达样式】
- 语气：犀利、接地气、极其现实。口头禅：「我跟你说」、「你听我说」、「千万别」。
- 态度：极度确定的现实主义。绝不说「可能」「这取决于」，直接给明确判断。
""".strip()


GENERAL_ASSISTANT_PROMPT = """
你是【通用职场助理】，服务于“一站式 AI 职业与升学导航”。
你的任务是帮助用户解决职业规划、升学规划、求职准备、面试训练、简历优化、行业认知等问题。
你的回答要清晰、现实、可执行，优先给步骤、判断标准和下一步行动。
""".strip()


def _build_headers():
    return {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }


def _contains_any(text: str, keywords: List[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def route_agent(user_input: str) -> AgentType:
    """轻量 Router Agent：基于关键词和意图规则选择专家。"""
    text = user_input.lower()

    gaokao_keywords = [
        "高考",
        "志愿",
        "填报",
        "专业",
        "院校",
        "大学",
        "本科",
        "专科",
        "考研",
        "升学",
        "录取",
        "分数线",
        "位次",
        "张雪峰",
    ]
    resume_keywords = [
        "简历",
        "resume",
        "jd",
        "岗位描述",
        "润色",
        "优化经历",
        "star",
        "项目经历怎么写",
        "自我评价",
        "求职材料",
    ]
    interview_keywords = [
        "面试",
        "interview",
        "八股",
        "追问",
        "拷打",
        "p8",
        "高压",
        "技术问题",
        "模拟面",
        "项目难点",
        "手撕",
    ]

    if _contains_any(text, gaokao_keywords):
        return AgentType.GAOKAO_ADVISOR
    if _contains_any(text, resume_keywords):
        return AgentType.RESUME_MENTOR
    if _contains_any(text, interview_keywords):
        return AgentType.P8_INTERVIEWER
    return AgentType.GENERAL_ASSISTANT


def get_system_prompt(agent_type: AgentType) -> str:
    if agent_type == AgentType.P8_INTERVIEWER:
        return P8_INTERVIEWER_PROMPT
    if agent_type == AgentType.RESUME_MENTOR:
        return RESUME_MENTOR_PROMPT
    if agent_type == AgentType.GAOKAO_ADVISOR:
        return GAOKAO_ADVISOR_PROMPT
    return GENERAL_ASSISTANT_PROMPT


def resolve_knowledge_id(request: AgentChatRequest, agent_type: AgentType) -> Optional[str]:
    """决定本轮对话使用哪个知识库。

    用户手动上传的 knowledge_id 优先级最高。
    如果用户没有上传，且当前路由为张雪峰分身，则默认使用系统预设知识库。
    """
    if request.knowledge_id:
        return request.knowledge_id
    if agent_type == AgentType.GAOKAO_ADVISOR:
        return SYSTEM_ZHANGXUEFENG_KNOWLEDGE_ID
    return None


def build_user_prompt(request: AgentChatRequest, agent_type: AgentType, context_block: str) -> str:
    """组装最终发给专家 Agent 的用户侧 Prompt。"""
    sections = []

    if context_block:
        sections.append(context_block)

    if request.resume_text and request.resume_text.strip():
        sections.append(f"【用户简历/个人背景】\n{request.resume_text.strip()[:4000]}")

    if request.target_job and request.target_job.strip():
        sections.append(f"【求职意向/目标岗位】\n{request.target_job.strip()}")

    if request.jd_text and request.jd_text.strip():
        sections.append(f"【目标岗位/JD】\n{request.jd_text.strip()[:3000]}")

    if request.history:
        history_lines = []
        for message in request.history[-8:]:
            role = "用户" if message.role == "user" else "AI"
            history_lines.append(f"{role}: {message.content[:1000]}")
        sections.append("【最近对话历史】\n" + "\n".join(history_lines))

    sections.append(f"【用户当前问题】\n{request.user_input.strip()}")

    return (
        f"你当前被路由为：{AGENT_LABELS[agent_type]}。\n"
        "最高优先级要求：不要复述用户材料，不要强制用户跳转页面，直接在当前对话里给出答案。\n"
        "如果知识库上下文与问题相关，必须优先引用知识库内容；如果上下文不足，请明确说不足。\n\n"
        + "\n\n====================\n\n".join(sections)
    )


def sse_event(event: str, payload: dict) -> str:
    """统一 SSE 输出格式，便于前端按 event 监听。"""
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


async def stream_llm_response(request: AgentChatRequest):
    """调用 DeepSeek 并把模型增量回复透传为 SSE。"""
    full_text = ""
    agent_type = route_agent(request.user_input)
    selected_knowledge_id = resolve_knowledge_id(request, agent_type)

    yield sse_event(
        "meta",
        {
            "payload": {
                "agent": agent_type.value,
                "agent_label": AGENT_LABELS[agent_type],
                "knowledge_id": selected_knowledge_id or "",
                "knowledge_source": "user" if request.knowledge_id else ("system" if selected_knowledge_id else ""),
            }
        },
    )

    if not DEEPSEEK_API_KEY:
        yield sse_event("error", {"payload": {"content": "DeepSeek API Key 未配置，请先检查 .env"}})
        return

    try:
        context_block = ""
        if selected_knowledge_id:
            try:
                context_block = build_context_block(
                    selected_knowledge_id,
                    request.user_input,
                    top_k=request.top_k or 4,
                )
                if context_block:
                    yield sse_event(
                        "meta",
                        {
                            "payload": {
                                "knowledge_id": selected_knowledge_id,
                                "rag_enabled": True,
                                "knowledge_source": "user" if request.knowledge_id else "system",
                            }
                        },
                    )
            except Exception as rag_exc:
                print(f"[Agent Dispatcher] RAG 检索失败，继续无知识库回答: {rag_exc}")
                yield sse_event(
                    "warning",
                    {
                        "payload": {
                            "content": f"知识库检索失败，已切换为普通回答：{rag_exc}",
                            "rag_enabled": False,
                        }
                    },
                )

        system_prompt = get_system_prompt(agent_type)
        user_prompt = build_user_prompt(request, agent_type, context_block)

        payload = {
            "model": DEEPSEEK_MODEL_NAME,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": True,
            "temperature": 0.7 if agent_type != AgentType.GAOKAO_ADVISOR else 0.8,
            "max_tokens": 4096,
        }

        async with httpx.AsyncClient(timeout=120.0, proxy=None) as client:
            async with client.stream(
                "POST",
                DEEPSEEK_BASE_URL,
                json=payload,
                headers=_build_headers(),
            ) as response:
                if response.status_code != 200:
                    error_text = (await response.aread()).decode("utf-8", errors="ignore")
                    print(f"[Agent Dispatcher] LLM 接口异常: {response.status_code} {error_text}")
                    yield sse_event(
                        "error",
                        {"payload": {"content": f"模型接口异常：HTTP {response.status_code}"}},
                    )
                    return

                async for line in response.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue

                    data_str = line[5:].strip()
                    if data_str == "[DONE]":
                        break

                    try:
                        parsed = json.loads(data_str)
                        delta = parsed.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            full_text += content
                            yield sse_event("reply", {"payload": {"content": content}})
                    except json.JSONDecodeError as json_exc:
                        print(f"[Agent Dispatcher] SSE JSON 解析失败，已跳过: {json_exc}")

    except httpx.ReadTimeout:
        yield sse_event("error", {"payload": {"content": "模型思考超时，请稍后重试"}})
    except httpx.ConnectError:
        yield sse_event("error", {"payload": {"content": "无法连接模型服务，请检查网络或 DeepSeek 配置"}})
    except Exception as exc:
        print(f"[Agent Dispatcher] 流式对话异常: {exc}")
        yield sse_event("error", {"payload": {"content": f"系统异常：{exc}"}})

    record_id = None
    if full_text:
        try:
            from database import insert_record

            record_id = insert_record(
                category=f"agent_{agent_type.value}",
                user_input=request.user_input[:200],
                ai_result=full_text[:5000],
                extra_data={
                    "agent": agent_type.value,
                    "agent_label": AGENT_LABELS[agent_type],
                    "knowledge_id": selected_knowledge_id or "",
                    "knowledge_source": "user" if request.knowledge_id else ("system" if selected_knowledge_id else ""),
                    "has_resume": bool(request.resume_text),
                    "has_jd": bool(request.jd_text),
                },
                chat_history=[message.model_dump() for message in request.history],
                user_id=request.user_id,
            )
        except Exception as db_exc:
            print(f"[Agent Dispatcher] 对话历史写入失败: {db_exc}")
    yield sse_event("done", {"payload": {"agent": agent_type.value, "length": len(full_text), "record_id": record_id}})


@router.post("/chat")
async def agent_chat(request: AgentChatRequest, current_user_id: Optional[int] = Depends(get_optional_user)):
    """Multi-Agent 统一聊天入口，面向 Dashboard LUI。支持游客访问（user_id 为 None）和已登录用户（user_id 为正整数）。"""
    # 将鉴权层解析出的 user_id 注入请求对象，供 stream_llm_response 写入历史记录
    request.user_id = current_user_id
    return StreamingResponse(
        stream_llm_response(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
