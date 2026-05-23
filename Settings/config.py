"""
Settings/config.py — 全局配置管理（唯一配置入口）

所有环境变量在此统一读取，其他模块直接 import 常量，
不再各自调用 os.getenv()。
"""

import os
from dotenv import load_dotenv

# main.py 已在最顶部调用 load_dotenv()，此处作为防御性兜底
load_dotenv()

# ─────────────────────────────────────────────
# LLM 配置（通用多 AI 支持）
# ─────────────────────────────────────────────
LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://api.xiaomimimo.com/v1/chat/completions")
LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME", "mimo-v2.5-pro")

if not LLM_BASE_URL.endswith("chat/completions"):
    LLM_BASE_URL = f"{LLM_BASE_URL.rstrip('/')}/chat/completions"

# 向后兼容：旧代码中 import DEEPSEEK_* 的地方不会立即报错
DEEPSEEK_API_KEY = LLM_API_KEY
DEEPSEEK_BASE_URL = LLM_BASE_URL
DEEPSEEK_MODEL_NAME = LLM_MODEL_NAME

# ─────────────────────────────────────────────
# JWT 配置
# ─────────────────────────────────────────────
JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "")
JWT_ALGORITHM: str = "HS256"
JWT_EXPIRE_DAYS: int = 7

# ─────────────────────────────────────────────
# RAG 配置
# ─────────────────────────────────────────────
RAG_EMBEDDING_MODEL: str = os.getenv(
    "RAG_EMBEDDING_MODEL",
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
)
RAG_EMBEDDING_DEVICE: str = os.getenv("RAG_EMBEDDING_DEVICE", "cpu")
RAG_CHUNK_SIZE: int = int(os.getenv("RAG_CHUNK_SIZE", "800"))
RAG_CHUNK_OVERLAP: int = int(os.getenv("RAG_CHUNK_OVERLAP", "120"))
RAG_MAX_UPLOAD_MB: int = int(os.getenv("RAG_MAX_UPLOAD_MB", "20"))
