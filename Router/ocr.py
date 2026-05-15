"""
Router/ocr.py — OCR 图片识别路由层

职责：HTTP 请求处理，调用 Service/Utils/ocr_sdk.py。
ocr_sdk 依赖 cv2 和 rapidocr，在函数内延迟导入以避免启动时报错。
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class OCRRequest(BaseModel):
    image_base64: str


@router.post("/recognize")
async def ocr_recognize(request: OCRRequest):
    """
    图片 OCR 识别端点。

    接收 base64 编码的图片，返回识别出的文字内容。
    """
    try:
        from Service.Utils.ocr_sdk import recognize_image_text
    except ImportError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"OCR 服务不可用，缺少依赖：{exc}。请安装 opencv-python 和 rapidocr-onnxruntime。",
        )

    result = recognize_image_text(request.image_base64)

    if not result or "图片解析失败" in result:
        raise HTTPException(status_code=500, detail=result or "图片解析失败")

    return {"extracted_text": result}
