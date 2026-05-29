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

# ─────────────────────────────────────────────
# 调试取证开关(Resume Builder 取证 — 仅开发环境启用)
# ─────────────────────────────────────────────
# 开启后 /api/document/extract-resume 会把每次请求的 raw_first / raw_retry / parsed /
# normalized / response / error 写到 debug/resume_extract/{request_id}_*.* 文件,
# 同时在响应中附带 debug_request_id 给前端打日志。
# 生产环境必须保持 false。
DEBUG_MODE: bool = (os.getenv("DEBUG_MODE", "false").strip().lower() in ("1", "true", "yes", "on"))


# ─────────────────────────────────────────────
# TTS 配置(Mimo TTS · MiMo-V2.5-TTS 系列)
# ─────────────────────────────────────────────
# 设计要点:
#   1. 复用同一 Mimo Open Platform 的 API Key,fallback 链:TTS_API_KEY → MIMO_API_KEY → LLM_API_KEY
#   2. base_url 不硬编码 api.xiaomimimo.com,优先读 TTS_BASE_URL,其次 MIMO_BASE_URL,
#      二者都缺再走最后一道兜底 https://api.xiaomimimo.com/v1。
#   3. TTS 走 chat-completions 协议,与 LLM 同源端点,所以 base_url 末尾不带 /chat/completions,
#      由 Service/tts_service.py 自行拼接。
#   4. TTS_TIMEOUT_SEC 是整体合成超时(整段一次返回,文本越长合成越久)。
#   5. TTS_MAX_TEXT_LEN 是应用层防护上限,前端、后端各拦一次。
TTS_API_KEY: str       = os.getenv("TTS_API_KEY") or os.getenv("MIMO_API_KEY") or os.getenv("LLM_API_KEY") or ""
TTS_BASE_URL: str      = os.getenv("TTS_BASE_URL") or os.getenv("MIMO_BASE_URL") or "https://api.xiaomimimo.com/v1"
TTS_BASE_URL = TTS_BASE_URL.rstrip("/")  # 末尾不含斜杠,Service 端拼接 /chat/completions
TTS_MODEL_NAME: str    = os.getenv("TTS_MODEL_NAME", "mimo-v2.5-tts")
TTS_VOICE: str         = os.getenv("TTS_VOICE", "mimo_default")
TTS_FORMAT: str        = (os.getenv("TTS_FORMAT", "mp3") or "mp3").strip().lower()
TTS_TIMEOUT_SEC: float = float(os.getenv("TTS_TIMEOUT_SEC", "60"))
TTS_MAX_TEXT_LEN: int  = int(os.getenv("TTS_MAX_TEXT_LEN", "3000"))
