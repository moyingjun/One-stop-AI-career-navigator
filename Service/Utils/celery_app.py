"""
Service/Utils/celery_app.py — Celery 应用实例

配置 broker 和 result backend 均指向 Redis。
此模块是全项目唯一的 Celery 实例，所有 task 模块从此处 import celery_app。

⚠️  Celery worker 启动命令（在项目根目录执行）：
    celery -A Service.Utils.celery_app worker --loglevel=info
"""

from celery import Celery

from Service.Settings.config import REDIS_URL

# ─────────────────────────────────────────────
# Celery 实例（全局单例）
# ─────────────────────────────────────────────
celery_app = Celery(
    "career_nav",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

celery_app.conf.update(
    # 任务序列化格式
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # 时区
    timezone="Asia/Shanghai",
    enable_utc=True,
    # 任务结果过期时间（1 小时）
    result_expires=3600,
    # 自动发现 tasks 模块
    include=["Service.Utils.tasks"],
)
