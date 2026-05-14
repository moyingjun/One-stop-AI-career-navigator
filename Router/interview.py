import os
import json
import httpx
import re
import time
import asyncio
from dotenv import load_dotenv
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from Router.dependencies import get_optional_user
from pydantic import BaseModel
from typing import Optional, List, AsyncGenerator
from database import insert_record

load_dotenv()

router = APIRouter(prefix="/api/interview", tags=["模拟面试"])

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://tokenrai.com/v1/chat/completions")
DEEPSEEK_MODEL_NAME = os.getenv("DEEPSEEK_MODEL_NAME", "deepseek-v4-flash")
if not DEEPSEEK_BASE_URL.endswith("chat/completions"):
    DEEPSEEK_BASE_URL = f"{DEEPSEEK_BASE_URL.rstrip('/')}/chat/completions"


class ChatRequest(BaseModel):
    user_query: str
    history: List[dict] = []
    resume_text: Optional[str] = ""
    jd_text: Optional[str] = ""
    difficulty: Optional[str] = "standard"
    target_job: Optional[str] = ""


class EvaluateRequest(BaseModel):
    user_query: str
    history: List[dict] = []
    resume_text: Optional[str] = ""
    jd_text: Optional[str] = ""
    difficulty: Optional[str] = "standard"
    user_id: Optional[int] = None


def _build_headers():
    return {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }


INTERVIEW_SYSTEM_PROMPT_BASE = """你是一名大厂顶级 HR 面试官，阅人无数，一眼就能看穿简历的虚假和包装。你正在进行一场模拟面试，基于候选人提供的【真实简历】和【目标岗位（JD）】，像真正的面试官一样逐轮提问、追问和质疑。

【无效输入检测 - 最高指令】：
如果候选人的回答是脸滚键盘的乱码（如"asdasd"、"qwer"、纯英文字母乱敲）、极端敷衍无意义的内容（如"不知道"、"随便"）、或者完全偏离面试主题，你的回复必须以 [WARNING] 这9个字符开头，然后严厉斥责对方的面试态度。例如："[WARNING] 你的回答完全是无效输入！这是对面试的严重不尊重，请认真回答问题！"这是强制要求！

【实时评分机制 - 必须遵守】：
在每次回复的末尾（情绪前缀和面试内容之后），你必须附加一段实时评分标签，格式为：[SCORE_UPDATE]{"professional":数字,"logic":数字,"communication":数字,"problemSolving":数字,"potential":数字,"resilience":数字}[/SCORE_UPDATE]
其中数字为0-100的整数，代表根据候选人到目前为止的所有回答给出的暂定评分。每次回复都必须更新这个评分。这段标签会被前端自动提取并用于雷达图实时更新，不会显示给用户。"""

DIFFICULTY_PROMPTS = {
    "beginner": """
【难度设定 - 温和鼓励】：
你是一名友好的初级面试官 / HR，专门帮助应届生和新人建立信心。你的风格是温和鼓励型的。
- 提问应聚焦基础概念和行为问题（如"请介绍一下你做过的项目"），避免过于专业的技术深度追问。
- 当候选人回答困难时，主动提供引导性提示和鼓励，例如"你可以从XX方面来思考"。
- 每次回复必须以情绪前缀开头：
  - 回答正确/有亮点：[点头] 开头，如 "[点头] 回答得很好！我们继续下一个问题..."
  - 回答不完整/有改进空间：[提示] 开头，如 "[提示] 不错的尝试，你可以从...方面补充..."
  - 完全错误/偏离：[鼓励] 开头，如 "[鼓励] 没关系，这个概念确实有点复杂，正确的理解是..."
- 限制深度技术追问，最多追问一层。
- 整体语气亲切、耐心，像学长学姐在帮忙模拟面试。""",

    "standard": """
【难度设定 - 标准专业】：
你是一名标准的资深工程师面试官，注重实用性和逻辑性。
- 提问应覆盖基础到中等难度的技术点，要求清晰的思路和具体案例。
- 适度追问，当候选人回答模糊时会要求补充细节，但不会刻意刁难。
- 每次回复必须以情绪前缀开头：
  - 回答优秀/有深度/有数据支撑：[点头] 开头，如 "[点头] 逻辑很清晰，但我还想深挖一下..."
  - 回答一般/有改进空间：[思考] 开头，如 "[思考] 这个回答还可以，但缺少具体案例..."
  - 回答敷衍/太短/避重就轻：[皱眉] 开头，如 "[皱眉] 这段经历描述太虚了，请说具体数据..."
  - 发现明显漏洞/虚假：[质疑] 开头，如 "[质疑] 你确定这个项目是你主导的吗？我发现了矛盾点..."
- 整体语气专业、客观，像真正的技术面试。""",

    "p8": """
【难度设定 - 压力刁难】：
你是一名P8级资深技术专家，以严厉著称，面试风格极具压迫感。
- 提问应极具挑战性，包含大量技术陷阱和压力测试，频繁打断并质疑候选人的回答。
- 制造紧张氛围，让候选人感受到真正的压力。
- 每次回复必须以情绪前缀开头：
  - 回答优秀/无可挑剔：[冷哼] 开头，如 "[冷哼] 这是基本常识，下一个问题..."
  - 回答一般/有瑕疵：[挑眉] 开头，如 "[挑眉] 这种水平也敢来面试？重新组织语言..."
  - 回答错误/敷衍：[嘲讽] 开头，如 "[嘲讽] 你确定你简历上的项目是自己做的？连这个都不知道？"
- 追问要层层递进，不给候选人喘息的机会。
- 整体语气严厉、犀利，像真正的P8大佬在审视候选人。"""
}


def get_interview_system_prompt(difficulty: str = "standard") -> str:
    difficulty = difficulty if difficulty in DIFFICULTY_PROMPTS else "standard"
    return INTERVIEW_SYSTEM_PROMPT_BASE + DIFFICULTY_PROMPTS[difficulty]


def build_messages(request: ChatRequest) -> list[dict]:
    """
    构建发送给 LLM 的消息列表（纯函数，无副作用）。

    消息结构：
    - index 0: system 消息，包含面试官角色设定、简历/JD 上下文（可选）、难度提示词
    - index 1..N: 历史对话（最近 20 条，仅保留 user/assistant 角色，每条内容截断至 2000 字符）
    - index N+1: 当前用户提问

    盲模式支持：当 resume_text 或 jd_text 为空时，自动省略对应段落。
    """
    # 构建简历和 JD 段落（盲模式：字段为空时省略）
    resume_section = ""
    jd_section = ""
    if request.resume_text and request.resume_text.strip():
        resume_section = f"这是候选人的简历：{request.resume_text.strip()[:4000]}"
    if request.jd_text and request.jd_text.strip():
        jd_section = f"这是目标岗位 JD：{request.jd_text.strip()[:3000]}"

    # 构建目标岗位段落（字段为空时省略）
    target_job_section = ""
    if request.target_job and request.target_job.strip():
        target_job_section = f"候选人的目标岗位是：{request.target_job.strip()}"

    # 拼接 system 消息前缀：角色设定 + 简历/JD 上下文 + 禁止索要材料指令
    context_prefix = (
        "你是一个专业面试官。"
        + resume_section
        + target_job_section
        + jd_section
        + "请根据这些背景严格进行追问，绝对不要在对话中要求候选人重新提供简历或JD！"
    )

    # 获取难度提示词（fallback 到 standard）
    difficulty_prompt = DIFFICULTY_PROMPTS.get(request.difficulty, DIFFICULTY_PROMPTS["standard"])
    system_content = context_prefix + "\n\n" + difficulty_prompt

    messages: list[dict] = [{"role": "system", "content": system_content}]

    # 追加历史消息：取最近 20 条，过滤非 user/assistant 角色，内容截断至 2000 字符
    for msg in request.history[-20:]:
        if msg.get("role") in ("user", "assistant"):
            messages.append({
                "role": msg["role"],
                "content": msg["content"][:2000]
            })

    # 追加当前用户提问作为最后一条消息
    messages.append({"role": "user", "content": request.user_query})

    return messages

EVALUATE_SYSTEM_PROMPT = """你是一个绝对客观、中立、没有感情的"AI 面试评估分析师"。你的唯一任务是阅读面试官与候选人的【完整对话历史】，并对候选人的表现进行六维打分（0-100分）。【打分标准】：professional(专业技能分) logic(逻辑分析分) communication(沟通表达分) problemSolving(问题解决分) potential(综合潜力分) resilience(抗压韧性分)。【强制输出纪律】：1. 必须且只能输出一个合法的 JSON 对象，绝对不要输出任何 markdown 标记、分析过程、问候语或其他文字。2. JSON 必须包含且仅包含以下 7 个键：{"professional": 数字, "logic": 数字, "communication": 数字, "problemSolving": 数字, "potential": 数字, "resilience": 数字, "comment": "总体评价50字以内"}。【极度严厉红线】：如果检测到候选人的输入是脸滚键盘的乱码（如"asdasd"、"hhh"、无意义字符拼凑）、严重偏离主题、或者明显敷衍了事，请毫不留情地在所有维度给出 0 分或最低分（1分），并在 comment 中明确指出这是无效输入！绝对不允许给无效输入任何同情分！【WARNING警告扣分规则】：分析聊天记录时，如果发现有 [WARNING] 警告标记，每出现一次 [WARNING]，所有维度得分必须额外扣减20分！如果出现3次或以上 [WARNING] 警告，所有六个维度的得分必须全部为 0 或 1 分，并在 comment 中直接宣告"面试失败（Fail）- 多次无效输入"！"""

# V2 版本：移除 WARNING 计数惩罚逻辑，仅基于语义回答质量进行客观打分
EVALUATE_SYSTEM_PROMPT_V2 = """
你是一个绝对客观、中立的 AI 面试评估分析师。
这是该候选人完整的面试逐字稿。
请根据回答的技术深度、逻辑连贯性、以及与简历/JD的匹配度进行客观打分（0-100）。
不要受任何系统警告信息的干扰，只看用户真实的回答内容！

【强制输出纪律】：只输出合法 JSON，包含且仅包含以下 7 个键：
{"professional": 数字, "logic": 数字, "communication": 数字,
 "problemSolving": 数字, "potential": 数字, "resilience": 数字,
 "comment": "总体评价50字以内"}
"""


async def call_deepseek(merged_user_content: str, temperature: float = 0.7, max_tokens: int = 4096) -> str:
    if not DEEPSEEK_API_KEY:
        print("❌ DEEPSEEK_API_KEY 未配置！")
        return None

    messages = [{"role": "user", "content": merged_user_content}]

    payload = {
        "model": DEEPSEEK_MODEL_NAME,
        "messages": messages,
        "stream": False,
        "temperature": temperature,
        "max_tokens": max_tokens
    }

    try:
        async with httpx.AsyncClient(timeout=60.0, proxy=None) as client:
            resp = await client.post(DEEPSEEK_BASE_URL, json=payload, headers=_build_headers())
            if resp.status_code != 200:
                print(f"❌ DeepSeek 调用失败: {resp.text}")
                return None
            return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"❌ 网络调用异常: {e}")
        return None


def _extract_json_from_text(text: str) -> dict:
    code_block_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    if code_block_match:
        text = code_block_match.group(1).strip()

    try:
        result = json.loads(text.strip())
        if isinstance(result, dict):
            return result
    except (json.JSONDecodeError, ValueError):
        pass

    matches = re.findall(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
    for match in reversed(matches):
        try:
            result = json.loads(match)
            if isinstance(result, dict):
                return result
        except (json.JSONDecodeError, ValueError):
            continue

    cleaned = text.strip()
    cleaned = re.sub(r'^[^{]*', '', cleaned)
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


async def stream_interview_response(request: ChatRequest) -> AsyncGenerator[str, None]:
    """
    面试流式响应生成器（SSE 格式）。

    调用 build_messages 构建消息列表，通过 httpx 流式请求 DeepSeek API，
    逐行解析 SSE data 行并 yield 给调用方。

    SSE 事件格式：
    - event: message  — 正常内容片段
    - event: error    — 错误信息（超时或服务器异常）
    - event: done     — 流结束标志（始终在 finally 中发送）
    - ': ping'        — 心跳保活（超过 15 秒无内容时发送）
    """
    messages = build_messages(request)
    last_yield_time = time.time()

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(120.0)) as client:
            async with client.stream(
                'POST',
                DEEPSEEK_BASE_URL,
                json={
                    "model": DEEPSEEK_MODEL_NAME,
                    "messages": messages,
                    "stream": True,
                    "temperature": 0.7,
                    "max_tokens": 4096
                },
                headers=_build_headers()
            ) as response:
                async for line in response.aiter_lines():
                    # 超过 15 秒无内容时发送心跳保活
                    if time.time() - last_yield_time > 15:
                        yield ': ping\n\n'
                        last_yield_time = time.time()

                    # 跳过空行和非 data: 开头的行
                    if not line or not line.startswith('data:'):
                        continue

                    data_str = line[5:].strip()

                    # 流结束标志
                    if data_str == '[DONE]':
                        break

                    # 解析 JSON 并提取 delta content
                    try:
                        parsed = json.loads(data_str)
                        content = parsed['choices'][0]['delta'].get('content', '')
                        if content:
                            yield f'event: message\ndata: {json.dumps({"content": content}, ensure_ascii=False)}\n\n'
                            last_yield_time = time.time()
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue

    except httpx.ReadTimeout:
        yield 'event: error\ndata: {"content":"模型思考超时，请稍后重试"}\n\n'
    except Exception:
        yield 'event: error\ndata: {"content":"服务器内部错误，请稍后重试"}\n\n'
    finally:
        yield 'event: done\ndata: {}\n\n'


@router.post("/chat")
async def interview_chat(request: ChatRequest):
    """
    面试聊天端点 — 返回 SSE StreamingResponse。
    使用 stream_interview_response 生成器逐块推送 AI 回复，
    支持打字机效果和心跳保活。
    """
    return StreamingResponse(
        stream_interview_response(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.post("/evaluate")
async def evaluate_interview(request: EvaluateRequest, current_user_id: Optional[int] = Depends(get_optional_user)):
    request.user_id = current_user_id
    history_text = "\n".join([f"{m.get('role', 'unknown')}: {m.get('content', '')}" for m in request.history])

    # 构建简历和 JD 段落（无截断，完整传入以提升评分准确性）
    resume_section = f"\n\n【候选人简历】：\n{request.resume_text}" if request.resume_text else ""
    jd_section = f"\n\n【目标岗位 JD】：\n{request.jd_text}" if request.jd_text else ""
    eval_user_prompt = f"请对以下面试对话记录进行六维打分，输出标准 JSON：\n{history_text}{resume_section}{jd_section}"

    print("\n========== [开始调用打分 Agent] ==========")

    merged = f"{EVALUATE_SYSTEM_PROMPT_V2}\n\n====================\n\n【最高指令】：禁止复述我提供的材料，直接输出你的核心结论！\n\n{eval_user_prompt}"

    eval_reply = await call_deepseek(merged, temperature=0.1, max_tokens=2048)

    if eval_reply:
        print(f"【打分 Agent 原始返回全文】:\n{eval_reply}\n{'-' * 40}")
        result = _extract_json_from_text(eval_reply)

        if result:
            required_keys = ["professional", "logic", "communication", "problemSolving", "potential", "resilience"]
            if all(k in result for k in required_keys):
                print("✅ JSON 解析成功！\n========================================\n")
                try:
                    insert_record(
                        category=f"interview_{request.difficulty}",
                        user_input=f"面试对话 {len(request.history)} 轮",
                        ai_result=result.get("comment", ""),
                        scores=result,
                        extra_data={
                            "resume_text": request.resume_text[:2000] if request.resume_text else "",
                            "target_role": "",
                            "jd_text": request.jd_text[:1000] if request.jd_text else "",
                            "difficulty": request.difficulty
                        },
                        chat_history=request.history,
                        user_id=request.user_id
                    )
                except Exception as db_err:
                    print(f"⚠️ 数据库写入失败: {db_err}")
                return {"success": True, "data": result}
            else:
                print(f"❌ JSON 缺少必要字段: {list(result.keys())}")
        else:
            print("❌ 所有 JSON 提取策略均失败！")

    return {"success": False, "msg": "打分失败，请重试"}


@router.post("/check-order")
async def check_order():
    return {"success": True, "status": "completed"}
