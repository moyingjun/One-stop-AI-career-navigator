"""
Router/dependencies.py — FastAPI 依赖注入：JWT 鉴权中间件

提供两个可复用的依赖函数：
  - get_current_user:    受保护端点使用，token 缺失或无效时抛出 HTTP 401
  - get_optional_user:   支持游客访问的端点使用，token 缺失时返回 None

对应 Requirements 3.1, 3.2, 3.3, 3.5, 3.6
"""

from typing import Optional

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from jose.exceptions import ExpiredSignatureError

from Settings.config import JWT_ALGORITHM, JWT_SECRET_KEY

# ─────────────────────────────────────────────
# JWT 配置（从 Settings/config.py 统一读取）
# ─────────────────────────────────────────────
_JWT_SECRET_KEY: str = JWT_SECRET_KEY
_JWT_ALGORITHM: str = JWT_ALGORITHM

# ─────────────────────────────────────────────
# OAuth2 scheme 定义
# ─────────────────────────────────────────────

# 受保护端点 scheme：auto_error=False 让我们自行控制 token 缺失时的错误消息，
# 以便返回中文 "未提供认证凭据" 而非 FastAPI 默认的英文 "Not authenticated"
# tokenUrl 指向登录端点，供 OpenAPI 文档使用
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

# 可选 scheme：auto_error=False 使 token 缺失时返回 None 而非抛出异常
optional_oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/auth/login",
    auto_error=False,
)

# ─────────────────────────────────────────────
# 内部工具函数
# ─────────────────────────────────────────────

def _decode_token(token: str) -> int:
    """
    解码并校验 JWT token，返回 user_id（正整数）。

    校验项：
      1. 签名合法性（使用 JWT_SECRET_KEY + HS256）
      2. 有效期（exp claim 未过期）
      3. payload 中存在 user_id 字段且为正整数

    参数：
        token — 原始 JWT 字符串

    返回：
        user_id — 正整数

    抛出：
        HTTPException(401) — token 无效、过期、签名错误或 user_id 不合法时
    """
    # 统一的 token 失效异常，避免泄露具体失败原因（Requirements 3.3）
    _token_invalid = HTTPException(
        status_code=401,
        detail="Token 已失效，请重新登录",
    )

    try:
        payload = jwt.decode(token, _JWT_SECRET_KEY, algorithms=[_JWT_ALGORITHM])
    except ExpiredSignatureError:
        # token 已过期（Requirements 3.3）
        raise _token_invalid
    except JWTError:
        # 签名错误、结构损坏或其他 JWT 解析异常（Requirements 3.3）
        raise _token_invalid

    # 校验 user_id 存在且为正整数（Requirements 3.1, 3.3）
    user_id = payload.get("user_id")
    if not isinstance(user_id, int) or user_id <= 0:
        raise _token_invalid

    return user_id


# ─────────────────────────────────────────────
# 依赖函数：受保护端点（必须携带有效 token）
# ─────────────────────────────────────────────

def get_current_user(token: Optional[str] = Depends(oauth2_scheme)) -> int:
    """
    FastAPI 依赖注入函数，用于受保护端点（Requirements 3.1, 3.2, 3.3）。

    行为：
      - token 缺失（Authorization header 不存在）：HTTP 401 "未提供认证凭据"
      - token 无效/过期/签名错误/user_id 不合法：HTTP 401 "Token 已失效，请重新登录"
      - token 合法：返回 user_id（正整数）

    注意：
      使用 auto_error=False 的 oauth2_scheme，由本函数自行控制 token 缺失时的
      错误消息，以返回中文 "未提供认证凭据"（Requirements 3.2）。

    参数：
        token — 由 oauth2_scheme 从 Authorization: Bearer <token> 中提取，缺失时为 None

    返回：
        user_id — 正整数（已通过签名、有效期、正整数校验）

    抛出：
        HTTPException(401) — token 缺失或无效时
    """
    # token 为空字符串时视为缺失（防御性处理）
    if not token:
        raise HTTPException(
            status_code=401,
            detail="未提供认证凭据",
        )

    return _decode_token(token)


# ─────────────────────────────────────────────
# 依赖函数：支持游客访问的端点（token 可选）
# ─────────────────────────────────────────────

def get_optional_user(
    token: Optional[str] = Depends(optional_oauth2_scheme),
) -> Optional[int]:
    """
    FastAPI 依赖注入函数，用于支持游客访问的端点（Requirements 3.5, 3.6）。

    行为：
      - token 不存在：返回 None（不抛出异常，允许游客访问）
      - token 存在且合法：返回 user_id（正整数）
      - token 存在但无效/过期：返回 None（宽松处理，不阻断游客请求）

    参数：
        token — 由 optional_oauth2_scheme 提取，缺失时为 None

    返回：
        user_id（int）— token 合法时返回正整数
        None          — token 缺失或无效时返回 None
    """
    if not token:
        return None

    try:
        return _decode_token(token)
    except HTTPException:
        # token 存在但无效时，游客端点宽松处理，返回 None（Requirements 3.5）
        return None
