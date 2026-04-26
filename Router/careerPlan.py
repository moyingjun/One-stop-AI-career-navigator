from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import httpx
import os
import json
import uuid

router = APIRouter(tags=["careerPlan"], prefix="/api")

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


async def call_career_agent(prompt: str) -> str:
    api_url = os.getenv("TENCENT_ADP_API_URL", "https://wss.lke.cloud.tencent.com/v1/qbot/chat/sse")
    app_key = os.getenv("TENCENT_CAREER_APPKEY", "").strip()

    if not app_key:
        raise ValueError("TENCENT_CAREER_APPKEY 未配置")

    test_key = app_key.replace("|", "").strip()
    unique_id = str(uuid.uuid4())

    payload = {
        "session_id": unique_id,
        "bot_app_key": test_key,
        "visitor_biz_id": unique_id,
        "content": prompt,
        "incremental": True,
        "streaming_throttle": 5,
        "stream": "enable"
    }

    headers = {"Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(api_url, json=payload, headers=headers)

        if resp.status_code != 200:
            raise Exception(f"腾讯云返回错误 [{resp.status_code}]")

        full_text = ""
        current_event = ""

        for line in resp.iter_lines():
            if not line:
                continue
            if line.startswith("event:"):
                current_event = line[6:].strip()
            elif line.startswith("data:"):
                if current_event == "reply":
                    data_str = line[5:].strip()
                    if data_str and data_str != "[DONE]":
                        try:
                            data_json = json.loads(data_str)
                            if "payload" in data_json:
                                content = data_json["payload"].get("content", "")
                                if content:
                                    full_text += content
                        except json.JSONDecodeError:
                            pass

        return full_text


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

async def tencent_career_stream(resume_text: str, user_confusion: str):
    print("\n========== [🔵 职业规划 SSE 流式隧道开启] ==========")
    api_url = os.getenv("TENCENT_ADP_API_URL", "https://wss.lke.cloud.tencent.com/v1/qbot/chat/sse")
    app_key = os.getenv("TENCENT_CAREER_APPKEY", "").strip()

    if not app_key:
        print("❌ 致命错误: TENCENT_CAREER_APPKEY 未配置！")
        yield "data: {\"error\": \"API Key 未配置\"}\n\n"
        return

    test_key = app_key.replace("|", "").strip()
    unique_id = str(uuid.uuid4())

    # 组装发送给大模型的内容
    prompt = f"【候选人简历】：\n{resume_text}\n\n【职业困惑/期望】：\n{user_confusion}"
    print(f"👉 准备向腾讯云发送请求，载荷总字数: {len(prompt)} 字")

    payload = {
        "session_id": unique_id,
        "bot_app_key": test_key,
        "visitor_biz_id": unique_id,
        "content": prompt,
        "incremental": True,
        "streaming_throttle": 5,
        "stream": "enable"
    }

    headers = {"Content-Type": "application/json"}

    try:
        # 【核心修复】：必须使用 client.stream 建立长连接隧道！不能用 post！
        async with httpx.AsyncClient(timeout=60.0) as client:
            print("⏳ 正在建立腾讯云 SSE 长连接...")
            async with client.stream("POST", api_url, json=payload, headers=headers) as resp:
                print(f"📡 腾讯云已响应，状态码: {resp.status_code}")
                
                if resp.status_code != 200:
                    error_text = await resp.aread()
                    print(f"❌ 腾讯云接口报错: {error_text.decode('utf-8')}")
                    yield f"data: {{\"error\": \"云端接口异常 {resp.status_code}\"}}\n\n"
                    return

                # 原封不动地将腾讯云的流式碎片转发给 Vue 前端
                chunk_count = 0
                async for chunk in resp.aiter_text():
                    if chunk:
                        chunk_count += 1
                        # 每收到 10 个碎片打印一次日志，避免终端刷屏，但能让你知道在动
                        if chunk_count % 10 == 0:
                            print(f"⚡ 正在持续转发数据流... (已转发 {chunk_count} 个数据包)")
                        yield chunk
                        
                print(f"✅ 数据流转发完毕，共转发 {chunk_count} 个数据包！")
                
    except httpx.ReadTimeout:
        print("❌ 网络读取超时 (ReadTimeout)")
        yield "data: {\"error\": \"大模型思考超时，请稍后重试\"}\n\n"
    except Exception as e:
        print(f"❌ 发生了致命的流中断异常: {str(e)}")
        yield f"data: {{\"error\": \"系统异常: {str(e)}\"}}\n\n"
    finally:
        print("========== [🏁 职业规划 SSE 流式隧道关闭] ==========\n")


@router.post("/career/plan")
async def career_plan(request: CareerPlanRequest):
    print("\n" + "="*50)
    print("📥 收到前端 [职业规划] 生成请求！")
    print(f"👤 用户困惑: {request.user_confusion}")
    print("="*50)
    
    return StreamingResponse(
        tencent_career_stream(request.resume_text, request.user_confusion),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no" # 确保 Nginx 不会阻拦流式输出
        }
    )


@router.post("/career/suggestions")
async def career_suggestions(request: CareerSuggestionsRequest):
    print("📥 收到前端 [职业推荐问题] 请求")
    prompt = (
        "请根据以下简历，推测该候选人目前最可能面临的4个职业发展困惑或面试痛点。"
        "必须且只能返回一个合法的 JSON 数组，如 "
        '[\\"简历缺乏亮点怎么补救？\\", \\"非科班如何进大厂？\\", \\"项目经验太简单怎么办？\\", \\"技术栈太旧如何转型？\\"]。'
        "单句不超过15个字。绝对不要输出其他废话！简历内容：\n" + request.resume_text
    )

    try:
        raw = await call_career_agent(prompt)
        suggestions = parse_suggestions(raw)
        print(f"✅ 动态推荐问题: {suggestions}")
        return {"suggestions": suggestions}
    except Exception as e:
        print(f"❌ 推荐问题生成失败，使用兜底: {e}")
        return {"suggestions": DEFAULT_SUGGESTIONS}