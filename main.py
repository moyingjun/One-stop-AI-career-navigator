from fastapi import FastAPI
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from Router import jobResume, resumeDiagnosis, interview, careerPlan, ocr
from Router import careerPlan
from database import init_db
from pydantic import BaseModel
from typing import Optional

load_dotenv()

app = FastAPI(title="一站式AI职业生涯导航员")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobResume.router)
app.include_router(resumeDiagnosis.router)
app.include_router(interview.router)
app.include_router(careerPlan.router)
app.include_router(ocr.router, prefix="/api/ocr", tags=["OCR"])


@app.on_event("startup")
async def startup():
    init_db()


class GeneralChatRequest(BaseModel):
    user_query: str
    resume_text: Optional[str] = ""


@app.post("/api/chat/general")
async def general_chat(request: GeneralChatRequest):
    from router.interview import call_deepseek

    GENERAL_SYSTEM_PROMPT = """你是一名经验丰富的职业规划导师和技术顾问，专门为IT行业求职者提供专业建议。你的任务是基于用户的问题和提供的简历（如果有），给出清晰、实用且有深度的回答。回答应包含具体的行动建议、行业洞察或技术指导，避免空泛的理论。使用Markdown格式增强可读性，适当使用标题、列表和代码块。"""

    user_prompt = f"【用户问题】：{request.user_query}\n\n"
    if request.resume_text:
        user_prompt += f"【用户简历】：\n{request.resume_text[:3000]}\n\n"

    merged = f"{GENERAL_SYSTEM_PROMPT}\n\n====================\n\n【最高指令】：禁止复述我的问题，直接输出你的专业建议！\n\n{user_prompt}"
    reply = await call_deepseek(merged, temperature=0.8, max_tokens=2048)

    if reply:
        try:
            from database import insert_record
            insert_record(
                category="general_chat",
                user_input=request.user_query[:200],
                ai_result=reply[:5000],
                extra_data={"has_resume": bool(request.resume_text)}
            )
        except Exception as db_err:
            print(f"⚠️ 聊天记录数据库写入失败: {db_err}")
        return {"reply": reply}

    return {"reply": "抱歉，我暂时无法回答这个问题，请稍后重试。"}


@app.get("/api/history")
async def get_history(limit: int = 10):
    from database import get_recent_records
    records = get_recent_records(limit)
    return {"records": records}


@app.get("/api/history/{record_id}")
async def get_history_by_id(record_id: int):
    from database import get_record_by_id
    record = get_record_by_id(record_id)
    if record:
        return {"success": True, "data": record}
    return {"success": False, "msg": "记录不存在"}

