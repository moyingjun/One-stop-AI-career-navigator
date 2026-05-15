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
# LLM 配置
# ─────────────────────────────────────────────
DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL: str = os.getenv("DEEPSEEK_BASE_URL", "https://tokenrai.com/v1/chat/completions")
DEEPSEEK_MODEL_NAME: str = os.getenv("DEEPSEEK_MODEL_NAME", "deepseek-v4-flash")

# 统一修正 URL 格式：确保以 /chat/completions 结尾
if not DEEPSEEK_BASE_URL.endswith("chat/completions"):
    DEEPSEEK_BASE_URL = f"{DEEPSEEK_BASE_URL.rstrip('/')}/chat/completions"

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
