from fastapi import APIRouter, Request, status, Cookie, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.encoders import jsonable_encoder
from typing import List, Dict, Any, Optional
import asyncio
from .models import uploadBody
from ..Service import service


router = APIRouter(
    tags=["jobResume"],
    prefix="/jobResume"
)


@router.post("/uploadJobResume")
async def uploadJobResume(
    # 彻底抛弃 body，直接独立接收字符串
    userId: str = Form(..., description="用户的唯一ID"), 
    ResumeFile: UploadFile = File(..., description="上传的简历文档或面试录音")
):
    try:
        # 直接把 userId 和文件扔给后厨处理
        result = await service.handle(userId, ResumeFile)
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))





