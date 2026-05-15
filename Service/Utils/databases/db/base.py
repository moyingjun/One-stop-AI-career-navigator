"""
Service/Utils/databases/db/base.py — 声明式基类（独立地基）

此文件只做一件事：定义 Base。
其他任何模块（ORM 模型、db/__init__.py）都从这里导入 Base，
从而彻底切断 ORM 模型 → db/__init__.py → history_db 的循环引用链。
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
