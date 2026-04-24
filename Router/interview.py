from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import httpx
import os
import json
import uuid

router = APIRouter(prefix="/api/interview", tags=["模拟面试"])


class ChatRequest(BaseModel):
    user_query: str
    history: List[dict] = []
    is_first_message: bool = False
    resume_text: Optional[str] = ""
    payment_verified: Optional[bool] = False


async def call_tencent_agent(query: str, resume: str = ""):
    api_url = os.getenv("TENCENT_ADP_API_URL", "https://wss.lke.cloud.tencent.com/v1/qbot/chat/sse")
    app_key = os.getenv("TENCENT_ADP_APPKEY", "").strip()

    if not app_key or app_key == "your_app_key_here":
        return None

    test_key = app_key.replace("|", "").strip()

    unique_id = str(uuid.uuid4())

    payload = {
        "session_id": unique_id,
        "bot_app_key": test_key,
        "visitor_biz_id": unique_id,
        "content": query,
        "incremental": True,
        "streaming_throttle": 5,
        "visitor_labels": [],
        "custom_variables": {
            "resume": resume.strip(),
            "desc": ""
        },
        "search_network": "disable",
        "stream": "enable",
        "workflow_status": "enable"
    }

    headers = {
        "Content-Type": "application/json"
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                api_url,
                content=json.dumps(payload, ensure_ascii=False),
                headers=headers
            )

            if resp.status_code != 200:
                print(f"腾讯云 Agent 返回错误 [{resp.status_code}]: {resp.text[:200]}")
                return None

            full_text = ""
            for chunk in resp.iter_text():
                for line in chunk.split("\n"):
                    if line.startswith("data:"):
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

            return full_text if full_text else None
    except Exception as e:
        print(f"腾讯云 Agent 调用异常: {e}")
        return None


FALLBACK_QUESTIONS = [
    "高压测试开始。请告诉我，在高并发场景下如何防止缓存击穿？",
    "验证通过。第一题：在高并发抢购场景下，你是如何设计缓存架构避免击穿的？",
    "请详细说明：当 QPS 从 100 飙升到 10000 时，你的系统架构需要如何演进？",
    "你的简历中提到了微服务架构。请详细说明你们是如何处理服务雪崩问题的？",
    "在生产环境中，你是如何保证数据一致性的？请从 CAP 定理的角度分析。",
    "请解释一下分布式锁的实现方式，以及 Redlock 算法的优缺点。"
]

FALLBACK_FOLLOWUPS = [
    "你的回答中提到了这个技术点，但我注意到你并没有深入说明底层实现原理。假设系统在高并发场景下，你的方案会如何表现？",
    "很好，你提到了性能优化。那么我问你：当 QPS 从 100 飙升到 10000 时，你的系统架构需要如何演进？",
    "我注意到你的回答让我有些疑虑。如果面试官是 P9 级别，你觉得这个回答能通过吗？重新思考一下。",
    "从你的回答中，我看到你有实战经验。但我想追问：在生产环境中，你是如何保证数据一致性的？",
    "你刚才提到的方案在理论上可行，但在实际落地时，你有没有考虑过网络分区的情况？",
    "请深入说明：你的方案在极端情况下（如机房故障、网络分区）会如何表现？"
]


@router.post("/chat")
async def interview_chat(request: ChatRequest):
    if request.is_first_message:
        return {
            "reply": "面试官已就绪，请扫码支付意向金解锁高压面试。",
            "is_payment_required": True,
            "qr_code": "weixin://wxpay/bizpayurl?pr=yuGvvl_Real"
        }

    if request.payment_verified:
        agent_reply = await call_tencent_agent(
            "候选人已完成支付验证，请开始第一轮高压技术面试，直接出题。",
            request.resume_text or ""
        )
        if agent_reply:
            return {
                "reply": agent_reply,
                "is_payment_required": False,
                "qr_code": ""
            }
        import random
        return {
            "reply": random.choice(FALLBACK_QUESTIONS),
            "is_payment_required": False,
            "qr_code": ""
        }

    agent_reply = await call_tencent_agent(
        request.user_query,
        request.resume_text or ""
    )
    if agent_reply:
        return {
            "reply": agent_reply,
            "is_payment_required": False,
            "qr_code": ""
        }

    import random
    return {
        "reply": random.choice(FALLBACK_FOLLOWUPS),
        "is_payment_required": False,
        "qr_code": ""
    }


@router.post("/check-order")
async def check_order():
    return {"success": True, "status": "completed"}
