from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from Service.Utils.ocr_sdk import recognize_image_text

router = APIRouter()


class OCRRequest(BaseModel):
    image_base64: str


@router.post("/recognize")
async def ocr_recognize(request: OCRRequest):
    result = recognize_image_text(request.image_base64)

    if not result or "图片解析失败" in result:
        raise HTTPException(status_code=500, detail=result or "图片解析失败")

    return {"extracted_text": result}
