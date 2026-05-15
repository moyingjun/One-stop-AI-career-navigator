"""
Router/auth.py — JWT 鉴权路由模块

负责处理验证码发送、用户注册、用户登录请求。
所有业务逻辑均委托 Service 层处理，此模块只负责 HTTP 协议层：
  - 接收请求、参数校验（Pydantic）
  - 调用 Service 层
  - 签发 JWT（JWT 签发属于协议层职责，保留在此）
  - 返回响应

执行铁律：Router 绝不包含验证码核对、密码哈希、数据库操作等底层业务逻辑。
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from Router.models.auth_model import AuthResponse, LoginRequest, RegisterRequest, SendCodeRequest
from Service import auth_service
from Service.Settings.config import JWT_ALGORITHM, JWT_EXPIRE_DAYS, JWT_SECRET_KEY
from Service.Utils.databases.db import get_db
from Service.Utils.captcha_utils import verify_turnstile

# ─────────────────────────────────────────────
# JWT 配置校验（启动时 fail-fast）
# ─────────────────────────────────────────────

if len(JWT_SECRET_KEY) < 32:
    raise RuntimeError(
        "配置错误：JWT_SECRET_KEY 未设置或长度不足 32 字符。"
        "请在 .env 文件中设置 JWT_SECRET_KEY（至少 32 字符）。"
    )

# ─────────────────────────────────────────────
# 路由器
# ─────────────────────────────────────────────

router = APIRouter(prefix="/api/auth", tags=["Auth"])


# ─────────────────────────────────────────────
# 内部工具：JWT 签发（协议层职责，保留在 Router）
# ─────────────────────────────────────────────

def _create_access_token(user_id: int, email: str) -> str:
    """
    签发 JWT access token。

    Payload：sub（email）、user_id、email、exp（7 天后过期）
    """
    expire = datetime.now(timezone.utc) + timedelta(days=JWT_EXPIRE_DAYS)
    payload = {
        "sub": email,
        "user_id": user_id,
        "email": email,
        "exp": expire,
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


# ─────────────────────────────────────────────
# 端点：POST /api/auth/send-code
# ─────────────────────────────────────────────

@router.post("/send-code", status_code=200)
async def send_code(
    request: SendCodeRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    发送邮箱验证码端点。

    流程：
      1. 验证 Turnstile captcha token（失败 → 403）
      2. 委托 auth_service.request_email_code() 处理业务逻辑
      3. 返回 200 {"msg": "验证码发送中"}
    """
    # 步骤 1：人机验证（Router 层职责：协议安全门控）
    captcha_ok = await verify_turnstile(request.captcha_token)
    if not captcha_ok:
        raise HTTPException(status_code=403, detail="人机验证失败，请刷新页面重试")

    # 步骤 2：委托 Service 层（冷却检查、验证码生成、数据库写入、Celery 推送）
    await auth_service.request_email_code(email=request.email, db=db)

    return {"msg": "验证码发送中"}


# ─────────────────────────────────────────────
# 端点：POST /api/auth/register
# ─────────────────────────────────────────────

@router.post("/register", response_model=AuthResponse, status_code=201)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    用户注册端点（邮箱验证码注册）。

    流程：
      1. 委托 auth_service.register_with_code() 完成原子性注册
         （验证码核对 + EmailLog 标记 used + User 激活，同一事务）
      2. 签发 JWT token
      3. 返回 AuthResponse
    """
    user = await auth_service.register_with_code(
        email=request.email,
        password=request.password,
        code=request.code,
        db=db,
    )

    access_token = _create_access_token(user_id=user.id, email=user.email)

    return AuthResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=user.id,
        email=user.email,
    )


# ─────────────────────────────────────────────
# 端点：POST /api/auth/login
# ─────────────────────────────────────────────

@router.post("/login", response_model=AuthResponse, status_code=200)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    用户登录端点（邮箱 + 密码）。

    流程：
      1. 委托 auth_service.login_with_password() 完成密码校验
         （任何失败均统一返回 401，防止用户枚举攻击）
      2. 签发 JWT token
      3. 返回 AuthResponse
    """
    user = await auth_service.login_with_password(
        email=request.email,
        password=request.password,
        db=db,
    )

    access_token = _create_access_token(user_id=user.id, email=user.email)

    return AuthResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=user.id,
        email=user.email,
    )
