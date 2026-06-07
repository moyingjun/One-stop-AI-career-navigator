"""鉴权路由的 Pydantic 请求/响应模型。"""

import re

from pydantic import BaseModel, field_validator


EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class EmailRequestBase(BaseModel):
    """共享的轻量邮箱校验，避免运行时依赖 email-validator。"""
    email: str

    @field_validator("email")
    @classmethod
    def email_format(cls, v: str) -> str:
        email = v.strip()
        if not EMAIL_PATTERN.match(email):
            raise ValueError("邮箱格式错误")
        return email


class SendCodeRequest(EmailRequestBase):
    """发送验证码请求体。"""
    captcha_token: str  # Cloudflare Turnstile 前端生成的验证 token


class RegisterRequest(EmailRequestBase):
    """注册请求体（邮箱验证码注册）。"""
    password: str
    code: str  # 6 位数字验证码

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("密码长度不足：密码至少需要 8 个字符")
        return v

    @field_validator("code")
    @classmethod
    def code_format(cls, v: str) -> str:
        if not v.isdigit() or len(v) != 6:
            raise ValueError("验证码格式错误：必须为 6 位数字")
        return v


class LoginRequest(EmailRequestBase):
    """登录请求体（邮箱 + 密码）。"""
    password: str


class AuthResponse(BaseModel):
    """鉴权成功响应体。"""
    access_token: str
    token_type: str = "bearer"
    user_id: int
    email: str
