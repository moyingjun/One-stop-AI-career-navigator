import os
import json
import httpx
import re
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List
from database import insert_record

router = APIRouter(prefix="/api/interview", tags=["模拟面试"])

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1/chat/completions")
DEEPSEEK_MODEL_NAME = os.getenv("DEEPSEEK_MODEL_NAME", "deepseek-chat")


class ChatRequest(BaseModel):
    user_query: str
    history: List[dict] = []
    resume_text: Optional[str] = ""
    jd_text: Optional[str] = ""
    difficulty: Optional[str] = "standard"


class EvaluateRequest(BaseModel):
    user_query: str
    history: List[dict] = []
    resume_text: Optional[str] = ""
    jd_text: Optional[str] = ""
    difficulty: Optional[str] = "standard"


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

EVALUATE_SYSTEM_PROMPT = """你是一个绝对客观、中立、没有感情的"AI 面试评估分析师"。你的唯一任务是阅读面试官与候选人的【完整对话历史】，并对候选人的表现进行六维打分（0-100分）。【打分标准】：professional(专业技能分) logic(逻辑分析分) communication(沟通表达分) problemSolving(问题解决分) potential(综合潜力分) resilience(抗压韧性分)。【强制输出纪律】：1. 必须且只能输出一个合法的 JSON 对象，绝对不要输出任何 markdown 标记、分析过程、问候语或其他文字。2. JSON 必须包含且仅包含以下 7 个键：{"professional": 数字, "logic": 数字, "communication": 数字, "problemSolving": 数字, "potential": 数字, "resilience": 数字, "comment": "总体评价50字以内"}。【极度严厉红线】：如果检测到候选人的输入是脸滚键盘的乱码（如"asdasd"、"hhh"、无意义字符拼凑）、严重偏离主题、或者明显敷衍了事，请毫不留情地在所有维度给出 0 分或最低分（1分），并在 comment 中明确指出这是无效输入！绝对不允许给无效输入任何同情分！【WARNING警告扣分规则】：分析聊天记录时，如果发现有 [WARNING] 警告标记，每出现一次 [WARNING]，所有维度得分必须额外扣减20分！如果出现3次或以上 [WARNING] 警告，所有六个维度的得分必须全部为 0 或 1 分，并在 comment 中直接宣告"面试失败（Fail）- 多次无效输入"！"""


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


@router.post("/chat")
async def interview_chat(request: ChatRequest):
    enhanced_query = request.user_query

    if len(request.history) == 0:
        jd_section = f"\n【岗位JD】：\n{request.jd_text.strip()}" if request.jd_text and request.jd_text.strip() else ""
        resume_section = f"\n【候选人简历】：\n{request.resume_text.strip()}" if request.resume_text and request.resume_text.strip() else ""
        enhanced_query = f"{resume_section}{jd_section}\n\n【候选人发言】：\n{request.user_query}"

    system_prompt = get_interview_system_prompt(request.difficulty)
    merged = f"{system_prompt}\n\n====================\n\n【最高指令】：禁止复述我提供的材料，直接输出你的核心结论！\n\n{enhanced_query}"

    agent_reply = await call_deepseek(merged, temperature=0.7, max_tokens=4096)

    if agent_reply:
        agent_reply = re.sub(r'^(面试官[：:]\s*|HR[：:]\s*|根据你提供的简历[^，。]*[，。]\s*)', '', agent_reply).strip()
        return {"reply": agent_reply, "is_payment_required": False, "qr_code": ""}

    return {"reply": "导师正在开小差，请重新点击发送哦~", "is_payment_required": False, "qr_code": ""}


@router.post("/evaluate")
async def evaluate_interview(request: EvaluateRequest):
    history_text = "\n".join([f"{m.get('role', 'unknown')}: {m.get('content', '')}" for m in request.history])

    eval_user_prompt = f"请对以下面试对话记录进行五维打分，输出标准 JSON：\n{history_text}"

    print("\n========== [开始调用打分 Agent] ==========")

    merged = f"{EVALUATE_SYSTEM_PROMPT}\n\n====================\n\n【最高指令】：禁止复述我提供的材料，直接输出你的核心结论！\n\n{eval_user_prompt}"

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
                        chat_history=request.history
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
