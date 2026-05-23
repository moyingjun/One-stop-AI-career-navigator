"""
Service/Utils/databases/models/history_model.py — 历史记录 ORM 模型

使用 SQLAlchemy 2.0 Mapped + mapped_column 语法。
保留 category 字段兼容旧前端逻辑，新增 record_type / session_id / updated_at。
JSON 字段（chat_history / scores / extra_data）使用 PostgreSQL JSON 类型。
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from Service.Utils.databases.db.base import Base


class HistoryRecord(Base):
    """
    AI 职业导航历史记录表。

    多租户隔离：所有查询必须附加 WHERE user_id = ?
    """

    __tablename__ = "history_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # ── 多租户隔离 ──────────────────────────────────────────
    # user_id 为 NULL 时为旧存量数据（向后兼容，允许任意已登录用户访问）
    # index 由 __table_args__ 中的 ix_history_records_user_id 显式管理，不用 index=True
    user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # ── 类型标识（双字段，逐步过渡）──────────────────────────
    # category 保留旧前端字段（如 agent_general_assistant / resume_diagnosis）
    category: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    # record_type 是新语义字段（dashboard_chat / resume_diagnosis / career_plan / interview_session）
    # index 由 __table_args__ 中的 ix_history_records_record_type 显式管理，不用 index=True
    record_type: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    # ── 会话标识（ChatDock 归档用）───────────────────────────
    # index 由 __table_args__ 中的 ix_history_records_session_id 显式管理，不用 index=True
    session_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    # ── 内容字段 ────────────────────────────────────────────
    # 用户输入摘要 / 对话标题（最多 2000 字）
    user_input: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # AI 输出摘要（最多 5000 字）
    ai_result: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # ── JSON 字段（TEXT 存储序列化 JSON）────────────────────
    # 完整对话历史：[{"role": "user"|"ai", "content": "..."}, ...]
    chat_history: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    # 评分维度：{"technical": 85, ...}
    scores: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    # 附加数据：{"agent": "...", "rag_enabled": true, ...}
    extra_data: Mapped[str] = mapped_column(Text, nullable=False, default="{}")

    # ── 状态 ────────────────────────────────────────────────
    is_saved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # ── 时间戳 ──────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # updated_at：upsert session 时更新；普通 insert 时与 created_at 相同
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, server_default=func.now(), onupdate=func.now()
    )

    # ── 复合索引 ─────────────────────────────────────────────
    __table_args__ = (
        Index("ix_history_records_user_id", "user_id"),
        Index("ix_history_records_session_id", "session_id"),
        Index("ix_history_records_record_type", "record_type"),
        # 多租户 session 唯一性索引：同一用户+同一 session 只有一条记录
        Index("uix_history_user_session", "user_id", "session_id", unique=True),
    )

    def __repr__(self) -> str:
        return (
            f"<HistoryRecord id={self.id} user_id={self.user_id} "
            f"category={self.category!r} record_type={self.record_type!r}>"
        )
