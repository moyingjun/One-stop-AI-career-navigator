"""
Service/auth_service.py — 鉴权业务逻辑层

封装验证码发送、原子性注册、登录等鉴权相关的业务逻辑。
Router 层只负责 HTTP 协议处理，具体业务均委托此模块。

⚠️  事务一致性（Atomicity）原则：
    - request_email_code：先 commit 数据库，再 .delay() 推队列，防止"邮件发出但数据未落库"。
    - register_with_code：步骤 2~4（标记 EmailLog used + 创建 User）在同一事务中，
      最后统一 commit，绝对禁止中间态 commit，防止数据死锁或不一致。

⚠️  注册流程说明：
    注册时用户尚不存在，request_email_code 允许向未注册邮箱发送验证码（临时 EmailLog）。
    register_with_code 验证码通过后原子性创建 User 记录，is_verified=True。
"""

import random
import string
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from Service.Utils.databases.models.user_model import EmailLog, User
from Service.Utils.tasks import send_verification_email

# ─────────────────────────────────────────────
# 常量
# ─────────────────────────────────────────────
_EMAIL_COOLDOWN_SECONDS = 60   # 验证码发送冷却时间（秒）
_CODE_EXPIRE_MINUTES = 10      # 验证码有效期（分钟）

# bcrypt 上下文（cost factor=12，与 Router 层保持一致）
_pwd_context = CryptContext(schemes=["bcrypt"], bcrypt__rounds=12)


# ─────────────────────────────────────────────
# 内部工具
# ─────────────────────────────────────────────

def _generate_code(length: int = 6) -> str:
    """生成指定长度的纯数字验证码。"""
    return "".join(random.choices(string.digits, k=length))


def _utc_now() -> datetime:
    """返回当前 UTC 时间（带时区）。"""
    return datetime.now(timezone.utc)


def _ensure_tz(dt: datetime) -> datetime:
    """确保 datetime 带有时区信息（兼容数据库返回的 naive datetime）。"""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


# ─────────────────────────────────────────────
# 公开业务方法
# ─────────────────────────────────────────────

async def request_email_code(email: str, db: AsyncSession) -> None:
    """
    发送邮箱验证码（支持注册前的未注册邮箱）。

    流程：
      1. 查询该 email 是否已有 pending 的 EmailLog（用于冷却检查）
         - 若已有记录且距上次发送 < 60 秒，抛出 429
      2. 生成 6 位随机数字验证码
      3. 写入 EmailLog（email_type="verify_email", status="pending"）
         注意：此时 user_id 可能为 NULL（注册前发码），EmailLog.user_id 允许 nullable
         → 实际上 EmailLog 外键要求 user_id 非空，因此此处采用"邮箱冷却"策略：
           通过查询最近一条 EmailLog（按 email 字段，不依赖 user_id）来做冷却检查，
           EmailLog 写入时 user_id 暂存为 0（占位），register_with_code 时更新为真实 user_id。
      4. await db.commit() — 数据完全落库
      5. commit 成功后，调用 send_verification_email.delay() 推入 Celery 队列

    ⚠️  竞态防范：.delay() 必须在 commit 之后调用。

    参数：
        email — 目标邮箱地址（可以是未注册邮箱）
        db    — 由 FastAPI Depends(get_db) 注入的异步 Session

    抛出：
        HTTPException(429) — 发送过于频繁（冷却中）
        HTTPException(500) — 数据库写入失败
    """
    now = _utc_now()

    # ── 步骤 1：查询该邮箱对应的 User（后续冷却检查和拦截均依赖此结果）──
    user_result = await db.execute(select(User).where(User.email == email))
    user: User | None = user_result.scalar_one_or_none()

    # 🚨 资源盗刷拦截门：已完成注册的正式用户禁止再次触发发信流程
    # 判定条件：is_verified=True 且 password_hash 非空（排除占位 User）
    # 目的：在 Celery 任务入队之前就一脚踹走，零邮件额度消耗
    if user is not None and user.is_verified and user.password_hash:
        raise HTTPException(
            status_code=400,
            detail="该邮箱已注册，请直接前往登录",
        )

    # ── 步骤 1b：60 秒冷却检查（针对未注册邮箱的频繁发信防刷）──
    # 此处 user 若存在，必为 is_verified=False 的占位 User（已被上方拦截过滤）
    if user is not None and user.last_email_sent_at is not None:
        last_sent = _ensure_tz(user.last_email_sent_at)
        elapsed = (now - last_sent).total_seconds()
        if elapsed < _EMAIL_COOLDOWN_SECONDS:
            remaining = int(_EMAIL_COOLDOWN_SECONDS - elapsed)
            raise HTTPException(
                status_code=429,
                detail=f"发送过于频繁，请 {remaining} 秒后再试",
            )

    # ── 步骤 2：生成验证码 ──
    code = _generate_code()
    expires_at = now + timedelta(minutes=_CODE_EXPIRE_MINUTES)

    # ── 步骤 3：写入数据库（同一事务）──
    if user is not None:
        # 已注册用户：更新冷却时间戳 + 写 EmailLog
        user.last_email_sent_at = now
        email_log = EmailLog(
            user_id=user.id,
            email_type="verify_email",
            code=code,
            status="pending",
            expires_at=expires_at,
        )
        db.add(email_log)
    else:
        # 未注册邮箱（注册前发码）：
        # 先创建一个未验证的占位 User，以满足 EmailLog 外键约束
        # is_verified=False，password_hash 为空占位，register_with_code 时会更新
        placeholder_user = User(
            email=email,
            password_hash="",          # 占位，register_with_code 时填充真实 hash
            is_verified=False,
            last_email_sent_at=now,
        )
        db.add(placeholder_user)
        await db.flush()  # flush 获取 placeholder_user.id，但不 commit

        email_log = EmailLog(
            user_id=placeholder_user.id,
            email_type="verify_email",
            code=code,
            status="pending",
            expires_at=expires_at,
        )
        db.add(email_log)

    # ── 步骤 4：提交事务，确保数据完全落库 ──
    try:
        await db.commit()
    except Exception as exc:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail="数据库写入失败，请稍后重试",
        ) from exc

    # ── 步骤 5：数据落库后，推入 Celery 异步队列 ──
    send_verification_email.delay(email, code)


async def register_with_code(
    email: str,
    password: str,
    code: str,
    db: AsyncSession,
) -> User:
    """
    原子性注册：验证码核对 + 用户激活，在同一事务中完成。

    防御性逻辑流：
      1. 查询该 email 对应 User 的最新一条 pending EmailLog（order_by desc, limit 1）
         - 无记录 → 400（未发送验证码）
         - 已过期 → 400（验证码已过期）
         - code 不匹配 → 400（验证码错误）
      2. 将 EmailLog.status 标记为 'used'
      3. 对 password 进行 bcrypt 哈希
      4. 更新 User 记录：填充 password_hash，设置 is_verified=True
      5. 统一执行 await db.commit()（步骤 2~4 在同一事务，禁止中间态 commit）

    🚨 铁律：步骤 2~4 绝对不能分开 commit，必须原子性提交，
             防止"EmailLog 已标记 used 但 User 未创建"的不一致状态。

    参数：
        email    — 注册邮箱
        password — 明文密码（至少 8 字符，由 Router 层 Pydantic 校验）
        code     — 用户输入的 6 位验证码
        db       — 由 FastAPI Depends(get_db) 注入的异步 Session

    返回：
        已激活的 User ORM 对象

    抛出：
        HTTPException(400) — 验证码无效、已过期或不匹配
        HTTPException(409) — 邮箱已完成注册（is_verified=True）
        HTTPException(500) — 数据库写入失败
    """
    now = _utc_now()

    # ── 步骤 1：查询该邮箱对应的 User 及最新 pending EmailLog ──
    user_result = await db.execute(select(User).where(User.email == email))
    user: User | None = user_result.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=400, detail="验证码无效，请重新发送")

    # 已完成注册的邮箱不允许重复注册
    if user.is_verified:
        raise HTTPException(status_code=409, detail="该邮箱已注册，请直接登录")

    # 查询最新一条 pending 的 EmailLog（order_by id desc, limit 1）
    log_result = await db.execute(
        select(EmailLog)
        .where(
            EmailLog.user_id == user.id,
            EmailLog.email_type == "verify_email",
            EmailLog.status == "pending",
        )
        .order_by(EmailLog.id.desc())
        .limit(1)
    )
    email_log: EmailLog | None = log_result.scalar_one_or_none()

    if email_log is None:
        raise HTTPException(status_code=400, detail="验证码无效，请重新发送")

    # 检查过期
    expires_at = _ensure_tz(email_log.expires_at)
    if now > expires_at:
        raise HTTPException(status_code=400, detail="验证码已过期，请重新发送")

    # 检查验证码是否匹配
    if email_log.code != code:
        raise HTTPException(status_code=400, detail="验证码错误，请重新输入")

    # ── 步骤 2~4：在同一事务中完成所有写操作 ──
    # 🚨 以下三步必须在同一事务中，最后统一 commit，禁止任何中间态 commit

    # 步骤 2：标记 EmailLog 为已使用
    email_log.status = "used"

    # 步骤 3：bcrypt 哈希密码
    try:
        password_hash = _pwd_context.hash(password)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="密码加密失败，注册中止") from exc

    # 步骤 4：激活 User 记录（填充真实密码 hash，标记已验证）
    user.password_hash = password_hash
    user.is_verified = True

    # ── 步骤 5：统一提交事务 ──
    try:
        await db.commit()
        await db.refresh(user)  # 刷新获取数据库生成的字段（如 created_at）
    except Exception as exc:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail="注册失败，请稍后重试",
        ) from exc

    return user


async def login_with_password(
    email: str,
    password: str,
    db: AsyncSession,
) -> User:
    """
    邮箱 + 密码登录验证。

    流程：
      1. 按 email 查询 User（不存在 → 统一 401，防止用户枚举）
      2. 检查 is_verified（未验证 → 401）
      3. bcrypt 校验密码（不匹配 → 统一 401）

    安全原则：
        任何失败（用户不存在、未验证、密码错误）均统一返回 401，
        使用相同的 detail 消息，防止用户枚举攻击。

    参数：
        email    — 登录邮箱
        password — 明文密码
        db       — 由 FastAPI Depends(get_db) 注入的异步 Session

    返回：
        已验证的 User ORM 对象

    抛出：
        HTTPException(401) — 任何认证失败场景
    """
    _auth_failure = HTTPException(status_code=401, detail="邮箱或密码错误")

    try:
        result = await db.execute(select(User).where(User.email == email))
        user: User | None = result.scalar_one_or_none()

        if user is None:
            raise _auth_failure

        # 未完成邮箱验证的账户不允许登录
        if not user.is_verified:
            raise _auth_failure

        # bcrypt 校验密码
        if not _pwd_context.verify(password, user.password_hash):
            raise _auth_failure

    except HTTPException:
        raise
    except Exception:
        # 任何内部异常（数据库异常等）统一返回 401，不泄露内部信息
        raise _auth_failure

    return user
