from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import httpx
import os
import json
import uuid

router = APIRouter(
    tags=["resumeDiagnosis"],
    prefix="/api"
)


class ResumeDiagnoseRequest(BaseModel):
    resume_text: str
    target_role: Optional[str] = ""
    jd_text: Optional[str] = ""


async def tencent_adp_stream(resume_text: str, target_role: str, jd_text: str):
    api_url = os.getenv("TENCENT_ADP_API_URL", "https://wss.lke.cloud.tencent.com/v1/qbot/chat/sse")
    app_key = os.getenv("TENCENT_ADP_APPKEY", "").strip()

    if not app_key or app_key == "your_app_key_here":
        raise ValueError("TENCENT_ADP_APPKEY 未配置，请在 .env 中填入真实的 API Key")

    test_key = app_key.replace("|", "").strip()
    print(f"FINAL_KEY_SENT: {test_key[:10]}...{test_key[-10:]} (Len: {len(test_key)})")

    resume_text = resume_text.replace("\r\n", "\n").strip()
    target_role = target_role.replace("\r\n", "\n").strip()
    jd_text = jd_text.replace("\r\n", "\n").strip()

    unique_id = str(uuid.uuid4())

    jd_section = f"【具体岗位描述(JD)】：\n{jd_text}\n" if jd_text.strip() else ""
    prompt = f"【候选人目标岗位】：{target_role or '未指定'}\n{jd_section}【候选人简历内容】：\n{resume_text}\n\n请你作为大厂顶级 HR，基于上述真实简历和目标岗位（如果有具体JD，请务必逐条对照JD要求），出具一份极其犀利、毒舌的简历诊断报告。指出简历与岗位要求之间的致命鸿沟！"

    payload = {
        "session_id": unique_id,
        "bot_app_key": test_key,
        "visitor_biz_id": unique_id,
        "content": prompt,
        "incremental": True,
        "streaming_throttle": 5,
        "visitor_labels": [],
        "custom_variables": {
            "resume": resume_text.strip(),
            "target_role": target_role.strip(),
            "desc": jd_text.strip()
        },
        "search_network": "disable",
        "stream": "enable",
        "workflow_status": "enable"
    }

    headers = {
        "Content-Type": "application/json"
    }

    payload_bytes = json.dumps(payload, ensure_ascii=False)
    print(f"DEBUG_PAYLOAD_LENGTH: {len(payload_bytes.encode('utf-8'))} bytes")

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            api_url,
            content=payload_bytes,
            headers=headers
        )

        print(f"DEBUG_RESPONSE_STATUS: {resp.status_code}")

        if resp.status_code != 200:
            error_text = resp.text
            print(f"CRITICAL_ERROR_RAW_BODY: {error_text}")
            raise Exception(
                f"腾讯云 ADP 返回错误 [{resp.status_code}]: {error_text}"
            )

        for chunk in resp.iter_text():
            yield chunk


@router.post("/resume/diagnose")
async def diagnose_resume(request: ResumeDiagnoseRequest):
    try:
        return StreamingResponse(
            tencent_adp_stream(request.resume_text, request.target_role, request.jd_text),
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
