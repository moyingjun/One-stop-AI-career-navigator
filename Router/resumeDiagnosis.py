from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import httpx
import os
import json
import re
from dotenv import load_dotenv
from database import insert_record

load_dotenv()

router = APIRouter(tags=["resumeDiagnosis"], prefix="/api")

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://tokenrai.com/v1/chat/completions")
DEEPSEEK_MODEL_NAME = os.getenv("DEEPSEEK_MODEL_NAME", "deepseek-v4-flash")
if not DEEPSEEK_BASE_URL.endswith("chat/completions"):
    DEEPSEEK_BASE_URL = f"{DEEPSEEK_BASE_URL.rstrip('/')}/chat/completions"


class ResumeDiagnoseRequest(BaseModel):
    resume_text: str
    target_role: Optional[str] = ""
    jd_text: Optional[str] = ""


def _build_headers():
    return {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }


RESUME_DIAGNOSIS_SYSTEM_PROMPT = """你是一名大厂顶级的"毒舌"资深 HR 面试官，阅人无数，一眼就能看穿简历的虚假和包装。你的任务是基于候选人提供的【真实简历】和【目标岗位（JD）】，出具一份极其犀利、一针见血的简历诊断报告。【核心约束】：1. 拒绝客套：不要说任何废话，直接开喷，指出简历与岗位要求之间的致命鸿沟。2. 精准找茬：挑出简历中假大空、缺乏数据支撑、与岗位无关的描述，并进行无情嘲讽。3. 建设性打击：在嘲讽之后，必须给出基于 STAR 法则（情境、任务、行动、结果）的高分重构示范。4. 格式要求：使用 Markdown 排版，必须包含三个固定版块：『致命问题诊断』、『简历排雷建议』、『高分重构示范』。5. 最终目的：语言犀利直接，但最终目的是为了帮助高职学生认清现实并快速改进。6. 六维评分：在报告的最末尾，必须输出一个独立的 JSON 对象（用 ```json ``` 包裹），包含以下六个维度的评分（0-100分）：{"keywordMatch": 数字, "experienceQuality": 数字, "dataDriven": 数字, "skillCompleteness": 数字, "layoutLogic": 数字, "coreCompetitiveness": 数字}。六个维度含义：keywordMatch(关键词匹配度)、experienceQuality(经历含金量)、dataDriven(数据化程度)、skillCompleteness(技能完整性)、layoutLogic(逻辑排版)、coreCompetitiveness(核心竞争力)。【极度严厉红线】：如果检测到用户输入的是脸滚键盘的乱码（如"asdasd"、"hhh"、无意义字符拼凑）、完全不是简历内容、或者严重敷衍了事，请毫不留情地在所有维度给出 0 分或最低分（1分），并在诊断报告中明确指出这是无效输入！绝对不允许给无效输入任何同情分！"""


async def deepseek_resume_stream(resume_text: str, target_role: str, jd_text: str):
    print("\n========== [🟣 简历诊断 DeepSeek SSE 流式隧道开启] ==========")

    if not DEEPSEEK_API_KEY:
        print("❌ 致命错误: DEEPSEEK_API_KEY 未配置！")
        yield f"event: reply\ndata: {json.dumps({'payload': {'content': '❌ API Key 未配置，请在 .env 中设置 DEEPSEEK_API_KEY'}})}\n\n"
        return

    resume_text = resume_text.replace("\r\n", "\n").strip()
    target_role = target_role.replace("\r\n", "\n").strip()
    jd_text = jd_text.replace("\r\n", "\n").strip()

    jd_section = f"【具体岗位描述(JD)】：\n{jd_text}\n" if jd_text.strip() else ""
    user_prompt = (
        f"【候选人目标岗位】：{target_role or '未指定'}\n"
        f"{jd_section}"
        f"【候选人简历内容】：\n{resume_text}\n\n"
        "请你作为大厂顶级 HR，基于上述真实简历和目标岗位（如果有具体JD，请务必逐条对照JD要求），"
        "出具一份极其犀利、毒舌的简历诊断报告。指出简历与岗位要求之间的致命鸿沟！"
    )
    print(f"👉 准备向 DeepSeek 发送请求，载荷总字数: {len(user_prompt)} 字")

    merged = f"{RESUME_DIAGNOSIS_SYSTEM_PROMPT}\n\n====================\n\n【最高指令】：禁止复述我提供的材料，直接输出你的核心结论！\n\n{user_prompt}"
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
            scores = None
            try:
                json_match = re.search(r'```json\s*([\s\S]*?)\s*```', full_text)
                if json_match:
                    scores = json.loads(json_match.group(1))
            except Exception:
                pass
            try:
                insert_record(
                    category="resume_diagnosis",
                    user_input=f"目标岗位: {target_role or '未指定'}",
                    ai_result=full_text[:5000],
                    scores=scores,
                    extra_data={"resume_text": resume_text[:2000], "target_role": target_role, "jd_text": jd_text[:1000]}
                )
            except Exception as db_err:
                print(f"⚠️ 数据库写入失败: {db_err}")
        print("========== [🏁 简历诊断 DeepSeek SSE 流式隧道关闭] ==========\n")


@router.post("/resume/diagnose")
async def diagnose_resume(request: ResumeDiagnoseRequest):
    try:
        return StreamingResponse(
            deepseek_resume_stream(request.resume_text, request.target_role, request.jd_text),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
    except ValueError as ve:
        raise HTTPException(status_code=500, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"代理请求失败: {str(e)}")
