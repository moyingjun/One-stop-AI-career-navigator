"""
Service/rag_service.py — 向后兼容的 re-export 入口

实际实现已迁移至 Service/Services/rag_service.py。
此文件保留是为了让所有现有的 `from Service.rag_service import ...` 语句无需修改。

新代码请直接从新路径导入：
    from Service.Services.rag_service import build_context_block, init_system_knowledge, ...
"""

from Service.Services.rag_service import (
    KNOWLEDGE_BASES,
    SYSTEM_ZHANGXUEFENG_KNOWLEDGE_ID,
    KnowledgeBase,
    build_context_block,
    create_knowledge_base,
    extract_text_from_file,
    init_system_knowledge,
    router,
    search_knowledge,
    split_text,
)

__all__ = [
    "router",
    "SYSTEM_ZHANGXUEFENG_KNOWLEDGE_ID",
    "KNOWLEDGE_BASES",
    "KnowledgeBase",
    "init_system_knowledge",
    "create_knowledge_base",
    "search_knowledge",
    "build_context_block",
    "extract_text_from_file",
    "split_text",
]
