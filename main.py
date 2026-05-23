"""
main.py — FastAPI 应用入口

负责：
  1. 加载环境变量（必须在所有业务 import 之前）
  2. 通过 lifespan 管理数据库引擎生命周期
  3. 注册所有路由
  4. 配置 CORS 中间件
"""

from dotenv import load_dotenv

# 必须在所有业务模块 import 之前加载 .env，
# 确保 JWT_SECRET_KEY 等环境变量在 auth.py 校验时已就绪
load_dotenv()

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ─────────────────────────────────────────────
# 路由层
# ─────────────────────────────────────────────
from Router import (
    agent_dispatcher,
    auth,
    careerPlan,
    history_router,
    interview,
    jobResume,
    llm_provider_router,
    ocr,
    resumeDiagnosis,
)
from Router import knowledge_base

# ─────────────────────────────────────────────
# 业务层（RAG 同时提供 FastAPI router 和业务函数）
# ─────────────────────────────────────────────
from Service.Services import rag_service

# ─────────────────────────────────────────────
# 数据库层（PostgreSQL 异步引擎）
# ─────────────────────────────────────────────
from Service.Utils.databases.db import AsyncSessionLocal, engine, init_db


# ─────────────────────────────────────────────
# 应用生命周期管理
# ─────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan 上下文管理器。
    yield 前：初始化数据库表结构、异步索引系统知识库。
    yield 后：安全释放数据库连接池。
    """
    # ── 启动阶段 ──
    await init_db()
    print("PostgreSQL 异步引擎已启动")

    # 异步初始化系统知识库（幂等，已存在则跳过）
    try:
        async with AsyncSessionLocal() as db:
            await rag_service.init_system_knowledge(db)
    except Exception as exc:
        # 知识库初始化失败不阻断服务启动
        print(f"[RAG] 系统知识库初始化失败，服务继续启动: {exc}")

    yield  # 应用正常运行期间

    # ── 关闭阶段 ──
    await engine.dispose()
    print("数据库连接已安全释放")


# ─────────────────────────────────────────────
# 应用初始化
# ─────────────────────────────────────────────
app = FastAPI(title="一站式AI职业生涯导航员", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────
# 路由注册
# ─────────────────────────────────────────────
app.include_router(jobResume.router)
app.include_router(resumeDiagnosis.router)
app.include_router(interview.router)
app.include_router(careerPlan.router)
app.include_router(ocr.router, prefix="/api/ocr", tags=["OCR"])
app.include_router(agent_dispatcher.router)
app.include_router(rag_service.router)          # 旧版 /api/knowledge/upload（兼容）
app.include_router(knowledge_base.router)       # 新版 /api/kb/*（带鉴权）
app.include_router(history_router.router)
app.include_router(auth.router)
app.include_router(llm_provider_router.router)
