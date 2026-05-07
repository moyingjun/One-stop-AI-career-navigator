from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import httpx
import os
import json
import re
from dotenv import load_dotenv
from database import insert_record

load_dotenv()

router = APIRouter(tags=["careerPlan"], prefix="/api")

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://tokenrai.com/v1/chat/completions")
DEEPSEEK_MODEL_NAME = os.getenv("DEEPSEEK_MODEL_NAME", "deepseek-v4-flash")
if not DEEPSEEK_BASE_URL.endswith("chat/completions"):
    DEEPSEEK_BASE_URL = f"{DEEPSEEK_BASE_URL.rstrip('/')}/chat/completions"


class CareerPlanRequest(BaseModel):
    resume_text: str
    user_confusion: str


class CareerSuggestionsRequest(BaseModel):
    resume_text: str


DEFAULT_SUGGESTIONS = [
    "简历缺乏亮点怎么补救？",
    "非科班如何进大厂？",
    "项目经验太简单怎么办？",
    "技术栈太旧如何转型？"
]


def _build_headers():
    return {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }


CAREER_SYSTEM_PROMPT = """你是一名拥有 10 年经验的"高校职业生涯规划导师"，特别擅长指导高职和本科学生的就业与升学规划。你的任务是根据学生的【简历】和【职业困惑】，为他们提供一份清晰、温暖、且极具实操性的职业发展规划。【核心约束】：1. 态度设定：温暖、专业、充满鼓励性，像一位知心大哥哥/大姐姐。2. 落地为王：不要给假大空的鸡汤。必须结合当前真实的行业趋势，给出非常具体的行动建议。3. 曲线救国：如果学生的期望过于好高骛远，请温柔地指出，并规划一条切合实际的备选方案。4. 格式要求：使用 Markdown 排版，必须包含固定版块：『现状与优势分析』、『核心突破点指引』、『分阶段行动计划（近3个月、近1年）』。"""

SUGGESTIONS_SYSTEM_PROMPT = """你是一个洞察力极强的数据分析组件。你的任务是根据候选人的【简历内容】，一针见血地推测出该候选人目前最可能面临的 4 个职业发展困惑或面试痛点，将其作为推荐提问。【强制输出纪律】：1. 必须且只能返回一个合法的 JSON 数组，包含 4 个字符串。2. 绝对不要输出任何其他废话、解释或 markdown 标记。3. 每个问题的字数严格控制在 15 个字以内，必须是疑问句。4. 输出示例格式：["我的项目经验太少怎么办？", "非科班如何进大厂？", "简历上的这段经历怎么优化？", "这个岗位需要什么硬技能？"]。"""


async def call_deepseek_non_stream(merged_user_content: str) -> str:
    if not DEEPSEEK_API_KEY:
        raise ValueError("DEEPSEEK_API_KEY 未配置")

    messages = [{"role": "user", "content": merged_user_content}]

    payload = {
        "model": DEEPSEEK_MODEL_NAME,
        "messages": messages,
        "stream": False,
        "temperature": 0.7,
        "max_tokens": 4096
    }

    async with httpx.AsyncClient(timeout=60.0, proxy=None) as client:
        resp = await client.post(DEEPSEEK_BASE_URL, json=payload, headers=_build_headers())
        if resp.status_code != 200:
            raise Exception(f"DeepSeek API 返回错误 [{resp.status_code}]: {resp.text}")
        return resp.json()["choices"][0]["message"]["content"]


def parse_suggestions(text: str) -> list:
    try:
        start = text.find("[")
        end = text.rfind("]") + 1
        if start != -1 and end > start:
            arr = json.loads(text[start:end])
            if isinstance(arr, list) and len(arr) > 0:
                return [str(item).strip() for item in arr if str(item).strip()]
    except (json.JSONDecodeError, ValueError):
        pass
    return DEFAULT_SUGGESTIONS


async def deepseek_career_stream(resume_text: str, user_confusion: str):
    print("\n========== [🔵 职业规划 DeepSeek SSE 流式隧道开启] ==========")

    if not DEEPSEEK_API_KEY:
        print("❌ 致命错误: DEEPSEEK_API_KEY 未配置！")
        yield f"event: reply\ndata: {json.dumps({'payload': {'content': '❌ API Key 未配置，请在 .env 中设置 DEEPSEEK_API_KEY'}})}\n\n"
        return

    user_prompt = f"【候选人简历】：\n{resume_text}\n\n【职业困惑/期望】：\n{user_confusion}"
    print(f"👉 准备向 DeepSeek 发送请求，载荷总字数: {len(user_prompt)} 字")

    merged = f"{CAREER_SYSTEM_PROMPT}\n\n====================\n\n【最高指令】：禁止复述我提供的材料，直接输出你的核心结论！\n\n{user_prompt}"
    messages = [{"role": "user", "content": merged}]

    payload = {
        "model": DEEPSEEK_MODEL_NAME,
        "messages": messages,
        "stream": True,
        "temperature": 0.7,
        "max_tokens": 4096
    }

    full_text = ""

    try:
        async with httpx.AsyncClient(timeout=120.0, proxy=None) as client:
            print("⏳ 正在建立 DeepSeek SSE 长连接...")
            async with client.stream("POST", DEEPSEEK_BASE_URL, json=payload, headers=_build_headers()) as resp:
                print(f"📡 DeepSeek 已响应，状态码: {resp.status_code}")

                if resp.status_code != 200:
                    error_text = await resp.aread()
                    print(f"❌ DeepSeek 接口报错: {error_text.decode('utf-8')}")
                    yield f"event: reply\ndata: {json.dumps({'payload': {'content': f'❌ DeepSeek 接口异常 {resp.status_code}'}})}\n\n"
                    return

                chunk_count = 0
                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue

                    data_str = line[5:].strip()
                    if data_str == "[DONE]":
                        print(f"✅ DeepSeek 数据流完毕，共转发 {chunk_count} 个增量包！")
                        break

                    try:
                        parsed = json.loads(data_str)
                        delta = parsed.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            chunk_count += 1
                            full_text += content
                            if chunk_count % 10 == 0:
                                print(f"⚡ 正在持续转发数据流... (已转发 {chunk_count} 个数据包)")
                            yield f"event: reply\ndata: {json.dumps({'payload': {'content': content}})}\n\n"
                    except json.JSONDecodeError:
                        pass

                print(f"✅ 数据流转发完毕，共转发 {chunk_count} 个数据包！")

    except httpx.ReadTimeout:
        print("❌ 网络读取超时 (ReadTimeout)")
        yield f"event: reply\ndata: {json.dumps({'payload': {'content': '❌ 大模型思考超时，请稍后重试'}})}\n\n"
    except Exception as e:
        print(f"❌ 发生了致命的流中断异常: {str(e)}")
        yield f"event: reply\ndata: {json.dumps({'payload': {'content': f'❌ 系统异常: {str(e)}'}})}\n\n"
    finally:
        if full_text:
            try:
                insert_record(
                    category="career_planning",
                    user_input=f"困惑: {user_confusion[:200]}",
                    ai_result=full_text[:5000],
                    scores=None,
                    extra_data={"resume_text": resume_text[:2000], "user_confusion": user_confusion[:500]}
                )
            except Exception as db_err:
                print(f"⚠️ 数据库写入失败: {db_err}")
        print("========== [🏁 职业规划 DeepSeek SSE 流式隧道关闭] ==========\n")


@router.post("/career/plan")
async def career_plan(request: CareerPlanRequest):
    print("\n" + "=" * 50)
    print("📥 收到前端 [职业规划] 生成请求！")
    print(f"👤 用户困惑: {request.user_confusion}")
    print("=" * 50)

    return StreamingResponse(
        deepseek_career_stream(request.resume_text, request.user_confusion),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/career/suggestions")
async def career_suggestions(request: CareerSuggestionsRequest):
    print("📥 收到前端 [职业推荐问题] 请求")
    user_prompt = (
        "请根据以下简历，推测该候选人目前最可能面临的4个职业发展困惑或面试痛点。"
        "必须且只能返回一个合法的 JSON 数组。单句不超过15个字。绝对不要输出其他废话！简历内容：\n" + request.resume_text
    )

    try:
        merged = f"{SUGGESTIONS_SYSTEM_PROMPT}\n\n====================\n\n【最高指令】：禁止复述我提供的材料，直接输出你的核心结论！\n\n{user_prompt}"
        raw = await call_deepseek_non_stream(merged)
        suggestions = parse_suggestions(raw)
        print(f"✅ 动态推荐问题: {suggestions}")
        return {"suggestions": suggestions}
    except Exception as e:
        print(f"❌ 推荐问题生成失败，使用兜底: {e}")
        return {"suggestions": DEFAULT_SUGGESTIONS}
