"""职业规划路由的 Pydantic 请求模型。"""

from pydantic import BaseModel


class CareerPlanRequest(BaseModel):
    """职业规划生成请求体。"""
    resume_text: str
    user_confusion: str


class CareerSuggestionsRequest(BaseModel):
    """职业推荐问题请求体。"""
    resume_text: str
