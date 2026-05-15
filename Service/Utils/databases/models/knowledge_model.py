"""
Service/Utils/databases/models/knowledge_model.py — 知识库 ORM 模型

使用 SQLAlchemy 2.0 Mapped + mapped_column 语法。
向量以 JSON 数组形式存储在 PostgreSQL TEXT 字段中，
未来可无缝迁移至 pgvector 扩展（只需替换列类型）。

多租户隔离设计：
  - user_id = None  → 全局共享库（系统预置，所有用户可检索）
  - user_id = <int> → 用户私有库（仅该用户可检索）
"""

import json
from datetime import datetime
from typing import List, Optional

from sqlalchemy import DateTime, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from Service.Utils.databases.db.base import Base


class KnowledgeChunk(Base):
    """
    知识库文本分块表。

    每行存储一个文本片段及其对应的 Embedding 向量（JSON 序列化）。
    检索时先按 user_id 过滤（多租户隔离），再做余弦相似度排序。
    """

    __tablename__ = "knowledge_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 多租户隔离：NULL = 全局共享库，非 NULL = 用户私有库
    user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)

    # 知识库来源标识（如文件名、系统知识库 ID 等）
    source_name: Mapped[str] = mapped_column(String(512), nullable=False)

    # 文本分块内容
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Embedding 向量（JSON 序列化的 float 列表）
    # 格式：[0.123, -0.456, ...]
    # 未来迁移 pgvector 时替换为 Vector(1024) 列类型
    embedding_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 创建时间
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # ── 复合索引：多租户检索加速 ──
    __table_args__ = (
        Index("ix_knowledge_chunks_user_source", "user_id", "source_name"),
    )

    def set_embedding(self, vector: List[float]) -> None:
        """将 float 列表序列化为 JSON 字符串存入 embedding_json。"""
        self.embedding_json = json.dumps(vector)

    def get_embedding(self) -> Optional[List[float]]:
        """从 embedding_json 反序列化为 float 列表，失败时返回 None。"""
        if not self.embedding_json:
            return None
        try:
            return json.loads(self.embedding_json)
        except (json.JSONDecodeError, TypeError):
            return None

    def __repr__(self) -> str:
        return (
            f"<KnowledgeChunk id={self.id} user_id={self.user_id!r} "
            f"source={self.source_name!r} len={len(self.content)}>"
        )
