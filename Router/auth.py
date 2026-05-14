"""
Router/auth.py — JWT 鉴权路由模块

负责处理用户注册和登录请求，签发 JWT access token。
对应 Requirements 1.x（注册）和 2.x（登录）。
"""

import os
import re
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException
from jose import jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from database import create_user, get_user_by_username

# ─────────────────────────────────────────────
# 安全配置（Requirements 16.2, 16.3）
# ─────────────────────────────────────────────

# bcrypt 哈希上下文，cost factor = 12（Requirements 16.2）
_pwd_context = CryptContext(schemes=["bcrypt"], bcrypt__rounds=12)

# JWT 配置：从环境变量读取密钥，启动时校验长度（Requirements 16.3）
_JWT_SECRET_KEY: str = os.environ.get("JWT_SECRET_KEY", "")
_JWT_ALGORITHM: str = "HS256"
_JWT_EXPIRE_DAYS: int = 7

if len(_JWT_SECRET_KEY) < 32:
    raise RuntimeError(
        "配置错误：JWT_SECRET_KEY 未设置或长度不足 32 字符。"
        "请在 .env 文件中设置 JWT_SECRET_KEY（至少 32 字符）。"
    )

# ─────────────────────────────────────────────
# 路由器
# ─────────────────────────────────────────────

router = APIRouter(prefix="/api/auth", tags=["Auth"])

# ─────────────────────────────────────────────
# Pydantic 请求/响应模型（Pydantic v2）
# ─────────────────────────────────────────────

class RegisterRequest(BaseModel):
    """注册请求体：用户名、密码（明文，后端 hash）、可选邮箱"""
    username: str
    password: str
    email: Optional[str] = None


class LoginRequest(BaseModel):
    """登录请求体：用户名 + 明文密码"""
    username: str
    password: str


class AuthResponse(BaseModel):
    """鉴权成功响应体：JWT token + 用户基本信息"""
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str


# ─────────────────────────────────────────────
# 内部工具函数
# ─────────────────────────────────────────────

# 用户名合法格式：1-50 字符，仅允许字母、数字、下划线（Requirements 1.1, 1.4）
_USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9_]{1,50}$")


def _validate_register_input(username: str, password: str) -> None:
    """
    校验注册请求的用户名和密码格式。
    格式不合法时抛出 HTTP 422，不创建任何用户记录（Requirements 1.4）。

    参数：
        username — 待校验的用户名
        password — 待校验的明文密码

    抛出：
        HTTPException(422) — 用户名或密码格式不合法时
    """
    if not _USERNAME_PATTERN.match(username):
        raise HTTPException(
            status_code=422,
            detail="用户名格式不合法：仅允许字母、数字、下划线，长度 1-50 字符",
        )
    if len(password) < 8:
        raise HTTPException(
            status_code=422,
            detail="密码长度不足：密码至少需要 8 个字符",
        )


def _create_access_token(user_id: int, username: str) -> str:
    """
    签发 JWT access token（Requirements 2.3, 16.2）。

    Payload 包含：
        sub      — 用户名（标准 JWT subject claim）
        user_id  — 用户 ID（正整数）
        username — 用户名（便于前端直接读取）
        exp      — 过期时间（当前时间 + 7 天）

    参数：
        user_id  — 已创建/已登录用户的 ID
        username — 对应用户名

    返回：
        签名后的 JWT 字符串（HS256 算法）
    """
    expire = datetime.now(timezone.utc) + timedelta(days=_JWT_EXPIRE_DAYS)
    payload = {
        "sub": username,
        "user_id": user_id,
        "username": username,
        "exp": expire,
    }
    return jwt.encode(payload, _JWT_SECRET_KEY, algorithm=_JWT_ALGORITHM)


# ─────────────────────────────────────────────
# 端点：POST /api/auth/register
# ─────────────────────────────────────────────

@router.post("/register", response_model=AuthResponse, status_code=201)
async def register(request: RegisterRequest):
    """
    用户注册端点（Requirements 1.1 ~ 1.6）。

    流程：
        1. 校验用户名（1-50 字符，字母数字下划线）和密码（≥8 字符）
           → 格式不合法时返回 HTTP 422，不创建任何用户记录
        2. 用 bcrypt（rounds=12）hash 明文密码
        3. 调用 create_user() 写入 users 表
           → 用户名重复（IntegrityError）时返回 HTTP 409
        4. 签发 JWT token（7 天有效期，payload 含 user_id + username）
        5. 返回 AuthResponse（access_token, token_type, user_id, username）

    可选字段：
        email — 若提供则一并存入 users 表（Requirements 1.5）
    """
    # 步骤 1：格式校验（不合法时抛出 422，不执行后续逻辑）
    _validate_register_input(request.username, request.password)

    # 步骤 2：bcrypt hash 密码（明文绝不写入数据库，Requirements 1.2, 16.2）
    try:
        password_hash = _pwd_context.hash(request.password)
    except Exception as exc:
        # bcrypt hash 失败时阻止用户记录创建（Requirements 1.2）
        raise HTTPException(
            status_code=500,
            detail="密码加密失败，注册中止",
        ) from exc

    # 步骤 3：写入数据库（用户名重复时 sqlite3 抛出 IntegrityError）
    try:
        new_user_id = create_user(
            username=request.username,
            password_hash=password_hash,
            email=request.email,
        )
    except sqlite3.IntegrityError:
        # 用户名唯一约束冲突 → HTTP 409（Requirements 1.3, 1.6）
        raise HTTPException(
            status_code=409,
            detail="用户名已被占用",
        )

    # 步骤 4：签发 JWT token
    access_token = _create_access_token(
        user_id=new_user_id,
        username=request.username,
    )

    # 步骤 5：返回鉴权响应
    return AuthResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=new_user_id,
        username=request.username,
    )


# ─────────────────────────────────────────────
# 端点：POST /api/auth/login
# ─────────────────────────────────────────────

@router.post("/login", response_model=AuthResponse, status_code=200)
async def login(request: LoginRequest):
    """
    用户登录端点（Requirements 2.1 ~ 2.4, 16.2, 16.3）。

    流程：
        1. 按用户名查询 users 表
           → 用户不存在时返回 HTTP 401（不泄露"用户名不存在"信息）
        2. 用 bcrypt 校验明文密码与存储的 password_hash
           → 密码不匹配时返回 HTTP 401
        3. 签发 JWT token（7 天有效期，payload 含 user_id + username）
        4. 返回 AuthResponse（access_token, token_type, user_id, username）

    安全原则：
        - 任何失败（用户不存在、密码错误、内部异常）均统一返回 HTTP 401
          并使用相同的 detail 消息，防止用户枚举攻击（Requirements 2.2）
        - 明文密码仅在内存中用于 bcrypt.verify，绝不持久化（Requirements 16.4）
    """
    # 统一的 401 异常，用于所有失败场景（防止信息泄露）
    _auth_failure = HTTPException(
        status_code=401,
        detail="用户名或密码错误",
    )

    try:
        # 步骤 1：按用户名查询用户记录
        user = get_user_by_username(request.username)
        if user is None:
            # 用户不存在 → 统一返回 401，不区分"用户名不存在"与"密码错误"
            raise _auth_failure

        # 步骤 2：bcrypt 校验密码（Requirements 16.2）
        password_matches = _pwd_context.verify(request.password, user["password_hash"])
        if not password_matches:
            raise _auth_failure

        # 步骤 3：签发 JWT token（Requirements 2.3）
        access_token = _create_access_token(
            user_id=user["id"],
            username=user["username"],
        )

    except HTTPException:
        # 重新抛出已构造的 HTTP 异常（401），不被下方 except 捕获
        raise
    except Exception:
        # 任何内部错误（数据库异常、bcrypt 异常等）均统一返回 401（Requirements 2.2）
        raise _auth_failure

    # 步骤 4：返回鉴权响应
    return AuthResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=user["id"],
        username=user["username"],
    )
