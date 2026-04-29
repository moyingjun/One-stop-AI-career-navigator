import os
import base64
import cv2
import numpy as np
from rapidocr_onnxruntime import RapidOCR

engine = RapidOCR()


def recognize_image_text(image_base64: str) -> str:
    try:
        if "," in image_base64:
            image_base64 = image_base64.split(",")[1]

        img_bytes = base64.b64decode(image_base64)
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            return "图片解析失败，请确保图片清晰或重试。"

        result, _ = engine(img)

        if not result:
            return ""

        text_lines = [line[1] for line in result]
        return "\n".join(text_lines)

    except Exception as e:
        print(f"[OCR ERROR] {e}")
        return "图片解析失败，请确保图片清晰或重试。"
