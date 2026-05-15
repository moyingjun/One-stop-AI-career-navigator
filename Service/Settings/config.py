"""
Service/Settings/config.py — 全局配置管理

集中管理环境变量读取和应用配置，供各层调用。
所有模块必须从此文件 import 常量，禁止直接调用 os.getenv()。
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────
# LLM 配置
# ─────────────────────────────────────────────
DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL: str = os.getenv("DEEPSEEK_BASE_URL", "https://tokenrai.com/v1/chat/completions")
DEEPSEEK_MODEL_NAME: str = os.getenv("DEEPSEEK_MODEL_NAME", "deepseek-v4-flash")

if not DEEPSEEK_BASE_URL.endswith("chat/completions"):
    DEEPSEEK_BASE_URL = f"{DEEPSEEK_BASE_URL.rstrip('/')}/chat/completions"

# ─────────────────────────────────────────────
# JWT 配置
# ─────────────────────────────────────────────
JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "")
JWT_ALGORITHM: str = "HS256"
JWT_EXPIRE_DAYS: int = 7

# ─────────────────────────────────────────────
# 数据库配置（PostgreSQL 异步）
# ─────────────────────────────────────────────
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:123456@localhost:5432/career_nav",
)

# ─────────────────────────────────────────────
# 邮件服务配置（Resend）
# ─────────────────────────────────────────────
RESEND_API_KEY: str = os.getenv("RESEND_API_KEY", "")

# ─────────────────────────────────────────────
# Redis / Celery 配置
# ─────────────────────────────────────────────
REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# ─────────────────────────────────────────────
# Cloudflare Turnstile 人机验证配置
# ─────────────────────────────────────────────
# 开发环境填 'mock_secret' 可跳过真实验证；生产环境替换为 Cloudflare 后台的 Secret Key
TURNSTILE_SECRET_KEY: str = os.getenv("TURNSTILE_SECRET_KEY", "mock_secret")

# ─────────────────────────────────────────────
# Embedding API 配置（云端向量化，禁止本地加载重型 ML 库）
# ─────────────────────────────────────────────
# 兼容 OpenAI /v1/embeddings 接口规范的外部 Embedding 服务
# 例如：https://api.openai.com/v1  或  https://tokenrai.com/v1
EMBEDDING_API_URL: str = os.getenv("EMBEDDING_API_URL", "https://tokenrai.com/v1")
EMBEDDING_API_KEY: str = os.getenv("EMBEDDING_API_KEY", "")
# 使用的 Embedding 模型名称（BAAI/bge-m3 或 text-embedding-3-small 等）
EMBEDDING_MODEL_NAME: str = os.getenv("EMBEDDING_MODEL_NAME", "BAAI/bge-m3")
