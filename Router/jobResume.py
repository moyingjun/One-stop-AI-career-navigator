"""
Router/jobResume.py — 简历文件上传路由（遗留端点）

此端点为早期版本遗留，当前前端已改为客户端解析（mammoth/pdfjs-dist）。
保留此路由以维持向后兼容，待后续评估是否正式废弃。
"""

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

router = APIRouter(tags=["jobResume"], prefix="/jobResume")


@router.post("/uploadJobResume")
async def upload_job_resume(
    userId: str = Form(..., description="用户的唯一ID"),
    ResumeFile: UploadFile = File(..., description="上传的简历文档或面试录音"),
):
    """
    简历文件上传端点（遗留）。

    当前返回占位响应，实际解析逻辑已迁移至前端（客户端解析）。
    后续可接入 Service/Utils/pdf_parser.py 实现服务端解析。
    """
    try:
        filename = ResumeFile.filename or ""
        return JSONResponse(content={
            "code": 200,
            "data": {
                "msg": "文件接收成功（服务端解析功能待实现）",
                "userId": userId,
                "filename": filename,
            }
        })
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
