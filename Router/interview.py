import os
import json
import httpx
import uuid
import re
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List

router = APIRouter(prefix="/api/interview", tags=["模拟面试"])

class ChatRequest(BaseModel):
    user_query: str
    history: List[dict] = []
    resume_text: Optional[str] = ""
    jd_text: Optional[str] = ""
    session_id: str = ""

# 增加 timeout=60.0 防止大模型思考太久导致 Failed to fetch
# 增加 timeout=60.0 防止大模型思考太久导致 Failed to fetch
async def call_tencent_agent(query: str, resume: str = "", jd: str = "", session_id: str = "", key_env: str = "TENCENT_INTERVIEW_APPKEY"):
    api_url = os.getenv("TENCENT_ADP_API_URL", "https://wss.lke.cloud.tencent.com/v1/qbot/chat/sse")
    app_key = os.getenv(key_env, "").strip()

    if not app_key:
        print(f"❌ 找不到环境变量: {key_env}，请检查 .env 文件！")
        return None

    test_key = app_key.replace("|", "").strip()
    actual_session = session_id if session_id else str(uuid.uuid4())

    payload = {
        "session_id": actual_session,
        "bot_app_key": test_key,
        "visitor_biz_id": actual_session,
        "content": query,
        "incremental": True,
        "streaming_throttle": 5,
        "visitor_labels": [],
        "custom_variables": {
            "resume": resume.strip(),
            "jd": jd.strip()
        },
        "stream": "enable",
    }

    headers = {"Content-Type": "application/json"}

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(api_url, content=json.dumps(payload, ensure_ascii=False), headers=headers)
            if resp.status_code != 200:
                print(f"❌ 调用腾讯云失败, 状态码: {resp.status_code}")
                return None

            full_text = ""
            current_event = None

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

            # 🔪 【核心终极斩杀】：物理切除 API 的回声 Bug！
            if full_text:
                full_text = full_text.strip()
                query_str = query.strip()
                
                # 如果返回的文本是以我们发过去的话开头的，直接无情切掉！
                if full_text.startswith(query_str):
                    # 切掉前缀，并清除可能残留的标点符号（比如：，。！？）
                    full_text = full_text[len(query_str):].lstrip("，,。！？!? \n\t")
                    
                return full_text
                
            return None
    except Exception as e:
        print(f"❌ 网络调用发生异常: {e}")
        return None

# ==========================================
# 1. 面试专线（狂躁的 P8 大脑）
# ==========================================
@router.post("/chat")
async def interview_chat(request: ChatRequest):
    
    # 🌟 核心改动：拦截第一句话，强行注入 JD 灵魂！
    enhanced_query = request.user_query
    
    # 只有当这是第一句话（history为空），且确实有 JD 数据时才触发
    if len(request.history) == 0 and request.jd_text and request.jd_text.strip():
        enhanced_query = f"""{request.user_query}

(⚠️ 系统最高隐秘指令：本次面试的具体【岗位JD】如下。请你务必死死盯住这份JD的要求！如果发现候选人的简历和JD产生严重错位（比如拿研发简历面保洁），请立刻开启最高级别的嘲讽模式，并围绕这份JD的真实工作场景疯狂拷问他！绝不能放水！
岗位JD内容：
{request.jd_text.strip()})"""

    # 调用大模型时，发送加强版的 enhanced_query
    agent_reply = await call_tencent_agent(
        query=enhanced_query,
        resume=request.resume_text or "",
        jd=request.jd_text or "",
        session_id=request.session_id or "",
        key_env="TENCENT_INTERVIEW_APPKEY"
    )

    if agent_reply:
        return {"reply": agent_reply, "is_payment_required": False, "qr_code": ""}

    return {"reply": "抱歉，大模型调用失败，请稍后重试。", "is_payment_required": False, "qr_code": ""}
# ==========================================
# 2. 真实打分专线（听话的分析师大脑）
# ==========================================
@router.post("/evaluate")
async def evaluate_interview(request: ChatRequest):
    history_text = "\n".join([f"{m['role']}: {m['content']}" for m in request.history])
    
    # 终极修复：去掉了提示词里的 {} 示例，改为纯文本字段要求，防止正则误抓！
    eval_prompt = f"""【系统指令：强制JSON输出】
请你仔细阅读以下面试对话记录。候选人经常胡言乱语或回避问题。
请对他进行五维打分（0-100分）。
必须且只能返回合法的 JSON 字符串！绝对不要输出其他任何废话！
请确保返回的 JSON 包含以下 6 个键名(必须是英文)：
"professional" (专业技能分)
"logic" (逻辑分析分)
"communication" (沟通表达分)
"problemSolving" (问题解决分)
"potential" (综合潜力分)
"comment" (这里写犀利的总体评价)

【面试对话记录】：
{history_text}
"""
    print("\n========== [开始调用打分 Agent] ==========")
    eval_reply = await call_tencent_agent(
        query=eval_prompt, 
        session_id=str(uuid.uuid4()), 
        key_env="TENCENT_ADP_APPKEY" 
    )
    
    if eval_reply:
        print(f"【打分 Agent 原始返回全文】:\n{eval_reply}\n{'-'*40}")
        try:
            # 终极修复：非贪婪匹配 {.*?\}，并且只取最后一个结果（防止大模型复读干扰）
            matches = re.findall(r'\{.*?\}', eval_reply, re.DOTALL)
            
            if matches:
                clean_text = matches[-1] # 只取最后一个大括号结构
                print(f"【正则精准提取出的 JSON 片段】:\n{clean_text}\n{'-'*40}")
                
                result = json.loads(clean_text)
                print("✅ JSON 解析成功，完美返回前端！\n========================================\n")
                return {"success": True, "data": result}
            else:
                print("❌ 找不到 JSON 结构！正则提取失败。")
        except Exception as e:
            print(f"❌ 解析打分JSON失败: {e}\n提取的片段是: {clean_text}")
            
    return {"success": False, "msg": "打分失败，请重试"}

@router.post("/check-order")
async def check_order():
    return {"success": True, "status": "completed"}