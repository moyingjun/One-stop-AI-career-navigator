"""简历诊断路由的 Pydantic 请求模型。"""

from pydantic import BaseModel
from typing import Optional


class ResumeDiagnoseRequest(BaseModel):
    """简历诊断请求体。"""
    resume_text: str
    target_role: Optional[str] = ""
    jd_text: Optional[str] = ""
    user_id: Optional[int] = None
