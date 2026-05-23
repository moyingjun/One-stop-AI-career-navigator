"""
Service/Utils/databases/models — SQLAlchemy 2.0 ORM 模型层

所有模型均继承 Service.Utils.databases.db.Base，
确保 Base.metadata 在 init_db() 调用前已收集到全部表定义。
"""

from .user_model import User, EmailLog       # noqa: F401
from .knowledge_model import KnowledgeChunk  # noqa: F401
from .history_model import HistoryRecord     # noqa: F401
