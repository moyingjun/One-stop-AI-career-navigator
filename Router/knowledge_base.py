"""
Router/knowledge_base.py — 知识库管理路由

职责：HTTP 参数拦截、JWT 解析、调用 Service 层。
所有业务逻辑（文本提取、分块、向量化、存储）全量下沉至 Service 层。

端点：
  POST /api/kb/upload   — 上传文件入库（需登录）
  GET  /api/kb/list     — 查询当前用户的知识库列表（需登录）
  DELETE /api/kb/{id}   — 删除指定分块来源（需登录）
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import delete, distinct, select
from sqlalchemy.ext.asyncio import AsyncSession

from Router.dependencies import get_current_user
from Service.Services.rag_service import ingest_file
from Service.Utils.databases.db import get_db
from Service.Utils.databases.models.knowledge_model import KnowledgeChunk

router = APIRouter(prefix="/api/kb", tags=["Knowledge Base"])


# ─────────────────────────────────────────────
# Pydantic 响应模型
# ─────────────────────────────────────────────

class UploadResponse(BaseModel):
    success: bool
    source_name: str
    chunk_count: int
    message: str


class KnowledgeSourceItem(BaseModel):
    source_name: str
    chunk_count: int


class KnowledgeListResponse(BaseModel):
    success: bool
    sources: List[KnowledgeSourceItem]
    total_chunks: int


# ─────────────────────────────────────────────
# 端点：POST /api/kb/upload
# ─────────────────────────────────────────────

@router.post("/upload", response_model=UploadResponse, status_code=201)
async def upload_knowledge(
    file: UploadFile = File(...),
    current_user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    上传文件并入库（需登录）。

    流程：
      1. JWT 解析提取 user_id（由 get_current_user 完成）
      2. 读取文件内容
      3. 委托 rag_service.ingest_file() 完成解析、分块、向量化、存储
      4. 返回入库结果

    支持格式：PDF、DOCX、TXT、MD
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="上传文件为空")

    try:
        result = await ingest_file(
            filename=file.filename,
            content=content,
            user_id=current_user_id,
            db=db,
        )
        return UploadResponse(
            success=True,
            source_name=result["source_name"],
            chunk_count=result["chunk_count"],
            message=f"文件已成功入库，共生成 {result['chunk_count']} 个检索片段",
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"入库失败: {exc}") from exc


# ─────────────────────────────────────────────
# 端点：GET /api/kb/list
# ─────────────────────────────────────────────

@router.get("/list", response_model=KnowledgeListResponse)
async def list_knowledge(
    current_user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    查询当前用户的知识库来源列表（需登录）。

    返回该用户私有库中所有 source_name 及对应的分块数量。
    不返回全局共享库（系统预置）。
    """
    # 查询该用户的所有 source_name 及分块数
    result = await db.execute(
        select(
            KnowledgeChunk.source_name,
        )
        .where(KnowledgeChunk.user_id == current_user_id)
        .distinct()
    )
    source_names = [row[0] for row in result.all()]

    sources: List[KnowledgeSourceItem] = []
    total_chunks = 0

    for source_name in source_names:
        count_result = await db.execute(
            select(KnowledgeChunk.id)
            .where(
                KnowledgeChunk.user_id == current_user_id,
                KnowledgeChunk.source_name == source_name,
            )
        )
        count = len(count_result.all())
        sources.append(KnowledgeSourceItem(source_name=source_name, chunk_count=count))
        total_chunks += count

    return KnowledgeListResponse(
        success=True,
        sources=sources,
        total_chunks=total_chunks,
    )


# ─────────────────────────────────────────────
# 端点：DELETE /api/kb/{source_name}
# ─────────────────────────────────────────────

@router.delete("/source")
async def delete_knowledge_source(
    source_name: str,
    current_user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    删除当前用户指定来源的所有知识库分块（需登录）。

    🚨 多租户安全：只能删除自己的私有库，不能删除全局共享库（user_id IS NULL）。

    参数：
        source_name — 要删除的来源名称（文件名）
    """
    result = await db.execute(
        delete(KnowledgeChunk).where(
            KnowledgeChunk.user_id == current_user_id,
            KnowledgeChunk.source_name == source_name,
        )
    )
    await db.commit()
    deleted_count = result.rowcount

    if deleted_count == 0:
        raise HTTPException(status_code=404, detail="未找到该来源的知识库记录")

    return {
        "success": True,
        "deleted_chunks": deleted_count,
        "message": f"已删除 {deleted_count} 个分块",
    }
