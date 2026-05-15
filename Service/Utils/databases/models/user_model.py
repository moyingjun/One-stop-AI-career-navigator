"""
Service/Utils/databases/models/user_model.py — 用户与邮件日志 ORM 模型

严格使用 SQLAlchemy 2.0 的 Mapped + mapped_column 类型注解语法。
禁止使用旧式 Column() 写法。
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from Service.Utils.databases.db.base import Base


# ─────────────────────────────────────────────
# User 表
# ─────────────────────────────────────────────
class User(Base):
    """用户账户表。"""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 邮箱作为唯一登录凭证
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)

    # bcrypt 哈希后的密码
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # 邮箱验证状态，默认未验证
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # 最近一次发送验证邮件的时间（用于限流，未发送时为 NULL）
    last_email_sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # 账户创建时间，由数据库自动填充
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # 反向关联：该用户的所有邮件日志
    email_logs: Mapped[list["EmailLog"]] = relationship(
        "EmailLog", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r} is_verified={self.is_verified}>"


# ─────────────────────────────────────────────
# EmailLog 表
# ─────────────────────────────────────────────
class EmailLog(Base):
    """邮件发送日志表，记录验证码发送记录及状态。"""

    __tablename__ = "email_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 关联用户（级联删除：用户删除时日志一并清除）
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # 邮件类型，例如 "verify_email" / "reset_password"
    email_type: Mapped[str] = mapped_column(String(64), nullable=False)

    # 验证码明文（存储前应由业务层决定是否加密）
    code: Mapped[str] = mapped_column(String(64), nullable=False)

    # 状态：pending / sent / used / expired
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")

    # 验证码过期时间
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # 正向关联
    user: Mapped["User"] = relationship("User", back_populates="email_logs")

    def __repr__(self) -> str:
        return (
            f"<EmailLog id={self.id} user_id={self.user_id} "
            f"type={self.email_type!r} status={self.status!r}>"
        )
