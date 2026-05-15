"""鉴权路由的 Pydantic 请求/响应模型。"""

from pydantic import BaseModel, EmailStr, field_validator


class SendCodeRequest(BaseModel):
    """发送验证码请求体。"""
    email: EmailStr
    captcha_token: str  # Cloudflare Turnstile 前端生成的验证 token


class RegisterRequest(BaseModel):
    """注册请求体（邮箱验证码注册）。"""
    email: EmailStr
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


class LoginRequest(BaseModel):
    """登录请求体（邮箱 + 密码）。"""
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    """鉴权成功响应体。"""
    access_token: str
    token_type: str = "bearer"
    user_id: int
    email: str
