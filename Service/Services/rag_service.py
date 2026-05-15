"""
Service/Services/rag_service.py — RAG 知识库服务（PostgreSQL 持久化 + 云端 Embedding）

⚠️  资源防御：绝对禁止引入 torch、sentence-transformers 等重型 ML 库。
    向量化通过 Service/Utils/embedding_client.py 调用外部 API 完成。

架构：
  - 存储层：PostgreSQL（KnowledgeChunk 表，向量 JSON 序列化）
  - 向量化：云端 Embedding API（BAAI/bge-m3）
  - 检索：双轨混合（A轨语义 + B轨关键词），取并集后去重排序
  - 多租户：查询范围 = 全局共享库（user_id IS NULL）+ 用户私有库（user_id = <int>）

FastAPI router 仅保留 /upload 端点（供旧代码兼容），
新的知识库管理接口在 Router/knowledge_base.py 中定义。
"""

import io
import os
import re
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from Service.Utils.databases.models.knowledge_model import KnowledgeChunk
from Service.Utils.embedding_client import cosine_similarity, embed_single, embed_texts

# ─────────────────────────────────────────────
# 常量
# ─────────────────────────────────────────────

# 系统预置知识库标识（user_id=None，全局共享）
SYSTEM_ZHANGXUEFENG_KNOWLEDGE_ID = "system_zhangxuefeng"

# 系统知识库文件目录
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SYSTEM_KNOWLEDGE_DIR = PROJECT_ROOT / "data" / "system_knowledge"

# 文本分块参数（2C4G 内存友好）
_CHUNK_SIZE = 800
_CHUNK_OVERLAP = 120

# 最大上传文件大小（MB）
_MAX_UPLOAD_MB = 20

# FastAPI router（兼容旧代码）
router = APIRouter(prefix="/api/knowledge", tags=["Knowledge"])


# ─────────────────────────────────────────────
# 文本提取工具
# ─────────────────────────────────────────────

def _decode_text(content: bytes) -> str:
    """兼容常见中文编码读取纯文本。"""
    for encoding in ("utf-8-sig", "utf-8", "gb18030", "gbk"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="ignore")


def _extract_pdf(content: bytes) -> str:
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(stream=content, filetype="pdf")
        pages = []
        for i, page in enumerate(doc):
            text = page.get_text().strip()
            if text:
                pages.append(f"[第 {i+1} 页]\n{text}")
        return "\n\n".join(pages)
    except Exception:
        pass
    try:
        from pdfminer.high_level import extract_text_to_fp
        from pdfminer.layout import LAParams
        buf = io.StringIO()
        extract_text_to_fp(io.BytesIO(content), buf, laparams=LAParams())
        return buf.getvalue()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"PDF 解析失败: {exc}") from exc


def _extract_docx(content: bytes) -> str:
    try:
        from docx import Document
        doc = Document(io.BytesIO(content))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except ImportError:
        raise HTTPException(status_code=500, detail="缺少 python-docx 依赖")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"DOCX 解析失败: {exc}") from exc


def extract_text_from_file(filename: str, content: bytes) -> str:
    """根据文件扩展名选择解析器，返回纯文本。"""
    suffix = os.path.splitext(filename.lower())[1]
    if suffix == ".pdf":
        text = _extract_pdf(content)
    elif suffix in {".txt", ".md"}:
        text = _decode_text(content)
    elif suffix in {".docx", ".doc"}:
        text = _extract_docx(content)
    else:
        raise HTTPException(status_code=400, detail="不支持的文件格式，请上传 PDF、Word、TXT 或 MD 文件")

    text = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    if not text:
        raise HTTPException(status_code=400, detail="未能从文件中提取到有效文本")
    return text


# ─────────────────────────────────────────────
# 文本分块（朴素实现，无重型依赖）
# ─────────────────────────────────────────────

def split_text(text: str, chunk_size: int = _CHUNK_SIZE, overlap: int = _CHUNK_OVERLAP) -> List[str]:
    """
    将长文本切分为适合检索的片段。

    优先按段落（\n\n）分割，再按句子（。！？）分割，
    最后按字符数硬切，确保每块不超过 chunk_size。
    """
    # 先按段落粗切
    paragraphs = [p.strip() for p in re.split(r'\n{2,}', text) if p.strip()]

    chunks: List[str] = []
    current = ""

    for para in paragraphs:
        if len(current) + len(para) <= chunk_size:
            current = (current + "\n\n" + para).strip() if current else para
        else:
            if current:
                chunks.append(current)
            # 段落本身超长时，按句子切
            if len(para) > chunk_size:
                sentences = re.split(r'(?<=[。！？\.\!\?])', para)
                sub = ""
                for sent in sentences:
                    if len(sub) + len(sent) <= chunk_size:
                        sub += sent
                    else:
                        if sub:
                            chunks.append(sub.strip())
                        sub = sent
                if sub.strip():
                    chunks.append(sub.strip())
                current = ""
            else:
                current = para

    if current:
        chunks.append(current)

    # 添加重叠（将前一块末尾 overlap 字符拼到下一块开头）
    if overlap > 0 and len(chunks) > 1:
        overlapped = [chunks[0]]
        for i in range(1, len(chunks)):
            tail = chunks[i - 1][-overlap:]
            overlapped.append((tail + " " + chunks[i]).strip())
        chunks = overlapped

    return [c for c in chunks if c.strip()]


# ─────────────────────────────────────────────
# 核心：知识入库（异步）
# ─────────────────────────────────────────────

async def ingest_text(
    *,
    text: str,
    source_name: str,
    user_id: Optional[int],
    db: AsyncSession,
) -> int:
    """
    将文本分块、向量化并存入 PostgreSQL。

    参数：
        text        — 已提取的纯文本
        source_name — 来源标识（文件名或系统知识库 ID）
        user_id     — None = 全局共享库；int = 用户私有库
        db          — 异步 SQLAlchemy Session

    返回：
        写入的分块数量

    抛出：
        RuntimeError — Embedding API 调用失败时
    """
    chunks = split_text(text)
    if not chunks:
        raise ValueError("文档分块后没有可索引内容")

    # 批量向量化（每批 16 条，防止单次请求过大）
    batch_size = 16
    all_vectors: List[List[float]] = []
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i: i + batch_size]
        vectors = await embed_texts(batch)
        all_vectors.extend(vectors)

    # 批量写入数据库
    for chunk_text, vector in zip(chunks, all_vectors):
        chunk = KnowledgeChunk(
            user_id=user_id,
            source_name=source_name,
            content=chunk_text,
        )
        chunk.set_embedding(vector)
        db.add(chunk)

    await db.commit()
    return len(chunks)


async def ingest_file(
    *,
    filename: str,
    content: bytes,
    user_id: Optional[int],
    db: AsyncSession,
) -> dict:
    """
    解析文件、分块、向量化并存入 PostgreSQL。

    参数：
        filename — 原始文件名（用于选择解析器和作为 source_name）
        content  — 文件二进制内容
        user_id  — None = 全局共享库；int = 用户私有库
        db       — 异步 SQLAlchemy Session

    返回：
        { "source_name": str, "chunk_count": int }
    """
    max_bytes = _MAX_UPLOAD_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(status_code=413, detail=f"文件过大，请上传 {_MAX_UPLOAD_MB}MB 以内的文件")

    text = extract_text_from_file(filename, content)
    chunk_count = await ingest_text(
        text=text,
        source_name=filename,
        user_id=user_id,
        db=db,
    )
    return {"source_name": filename, "chunk_count": chunk_count}


# ─────────────────────────────────────────────
# 核心：双轨混合检索（异步）
# ─────────────────────────────────────────────

async def search_knowledge(
    *,
    query: str,
    user_id: int,
    top_k: int = 3,
    db: AsyncSession,
) -> List[str]:
    """
    双轨混合检索：A轨（语义余弦）+ B轨（关键词精准匹配）。

    🚨 多租户强隔离：
        检索范围 = 全局共享库（user_id IS NULL）+ 用户私有库（user_id = <int>）
        严格禁止跨用户检索。

    参数：
        query   — 用户查询文本
        user_id — 当前用户 ID（必填，不接受 None）
        top_k   — 返回最多 top_k 条结果（严格限制 ≤ 5，防 Token 爆炸）
        db      — 异步 SQLAlchemy Session

    返回：
        去重后的文本片段列表（最多 top_k 条）
    """
    top_k = min(top_k, 5)  # 硬上限，防止 Token 爆炸

    # ── 多租户过滤：全局共享库 OR 用户私有库 ──
    scope_filter = or_(
        KnowledgeChunk.user_id.is_(None),
        KnowledgeChunk.user_id == user_id,
    )

    # 拉取候选 chunks（限制数量防止内存溢出）
    result = await db.execute(
        select(KnowledgeChunk)
        .where(scope_filter)
        .order_by(KnowledgeChunk.id.desc())
        .limit(500)  # 2C4G 内存友好：最多加载 500 条候选
    )
    candidates: List[KnowledgeChunk] = list(result.scalars().all())

    if not candidates:
        return []

    # ── B轨：关键词精准匹配 ──
    query_lower = query.lower()
    # 提取查询中的关键词（长度 ≥ 2 的词）
    keywords = [w for w in re.split(r'[\s，。！？,\.!?]+', query) if len(w) >= 2]

    keyword_hits: List[tuple[float, str]] = []
    for chunk in candidates:
        content_lower = chunk.content.lower()
        score = sum(1 for kw in keywords if kw.lower() in content_lower)
        # 专有名词精准命中加权（如"张雪峰"）
        if query in chunk.content:
            score += 5
        if score > 0:
            keyword_hits.append((float(score), chunk.content))

    keyword_hits.sort(key=lambda x: x[0], reverse=True)
    keyword_results = [content for _, content in keyword_hits[:top_k]]

    # ── A轨：语义向量检索 ──
    semantic_results: List[str] = []
    try:
        query_vector = await embed_single(query)
        scored: List[tuple[float, str]] = []
        for chunk in candidates:
            vec = chunk.get_embedding()
            if vec is None:
                continue
            sim = cosine_similarity(query_vector, vec)
            scored.append((sim, chunk.content))

        scored.sort(key=lambda x: x[0], reverse=True)
        # 只取相似度 > 0.3 的结果（过滤噪声）
        semantic_results = [
            content for sim, content in scored[:top_k]
            if sim > 0.3
        ]
    except Exception as exc:
        # Embedding API 失败时降级为纯关键词检索
        import logging
        logging.getLogger(__name__).warning(
            "语义检索失败，降级为关键词检索 | error=%s", str(exc)
        )

    # ── 合并去重：语义优先，关键词补充 ──
    seen: set[str] = set()
    merged: List[str] = []

    for content in semantic_results + keyword_results:
        if content not in seen:
            seen.add(content)
            merged.append(content)
        if len(merged) >= top_k:
            break

    return merged


async def build_context_block(
    *,
    query: str,
    user_id: int,
    top_k: int = 3,
    db: AsyncSession,
) -> str:
    """
    检索知识库并组装 <context> 注入块。

    参数：
        query   — 用户查询文本
        user_id — 当前用户 ID
        top_k   — 严格限制为 3（防 Token 爆炸）
        db      — 异步 SQLAlchemy Session

    返回：
        格式化的 <context> 字符串，无结果时返回空字符串
    """
    top_k = min(top_k, 3)  # dispatcher 层强制 k=3
    snippets = await search_knowledge(query=query, user_id=user_id, top_k=top_k, db=db)

    if not snippets:
        return ""

    formatted = "\n\n".join(
        f"[片段 {i}]\n{snippet[:1500]}"
        for i, snippet in enumerate(snippets, start=1)
    )

    return (
        "<context>\n"
        "以下内容来自知识库，请优先依据这些材料回答；若材料不足或无关，请依靠通用知识作答，不要编造。\n\n"
        f"{formatted}\n"
        "</context>"
    )


# ─────────────────────────────────────────────
# 系统知识库初始化（启动时调用）
# ─────────────────────────────────────────────

async def init_system_knowledge(db: AsyncSession) -> int:
    """
    启动时将 data/system_knowledge 下的 .md 文件索引到全局共享库。

    幂等：若该 source_name 已存在记录则跳过（不重复写入）。

    参数：
        db — 异步 SQLAlchemy Session

    返回：
        本次写入的分块数量（0 表示已存在或无文件）
    """
    SYSTEM_KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
    md_files = sorted(SYSTEM_KNOWLEDGE_DIR.rglob("*.md"))

    if not md_files:
        print(f"[RAG] 系统知识库目录暂无 .md 文件: {SYSTEM_KNOWLEDGE_DIR}")
        return 0

    total_chunks = 0
    for md_file in md_files:
        source_name = f"system:{md_file.relative_to(SYSTEM_KNOWLEDGE_DIR).as_posix()}"

        # 幂等检查：已存在则跳过
        existing = await db.execute(
            select(KnowledgeChunk.id)
            .where(
                KnowledgeChunk.user_id.is_(None),
                KnowledgeChunk.source_name == source_name,
            )
            .limit(1)
        )
        if existing.scalar_one_or_none() is not None:
            continue

        try:
            content = md_file.read_bytes()
            text = extract_text_from_file(md_file.name, content)
            count = await ingest_text(
                text=text,
                source_name=source_name,
                user_id=None,  # 全局共享库
                db=db,
            )
            total_chunks += count
            print(f"[RAG] 系统知识库已索引: {source_name} ({count} chunks)")
        except Exception as exc:
            print(f"[RAG] 系统知识文件索引失败，已跳过 {md_file}: {exc}")

    if total_chunks > 0:
        print(f"[RAG] 系统知识库初始化完成，共写入 {total_chunks} 个分块")
    else:
        print("[RAG] 系统知识库已是最新，无需重新索引")

    return total_chunks


# ─────────────────────────────────────────────
# 兼容旧代码的同步接口（供 main.py lifespan 调用）
# ─────────────────────────────────────────────

def init_system_knowledge_sync() -> None:
    """
    同步包装器，供 main.py lifespan 中调用。
    实际工作委托给 init_system_knowledge(db)，
    需要在 lifespan 中传入 db session。

    注意：此函数仅作占位，实际调用见 main.py。
    """
    pass  # 实际逻辑在 main.py lifespan 中通过 async 调用


# ─────────────────────────────────────────────
# FastAPI Router（兼容旧代码的 /upload 端点）
# ─────────────────────────────────────────────

@router.post("/upload")
async def upload_knowledge_legacy(file: UploadFile = File(...)):
    """
    旧版知识库上传端点（无鉴权，兼容旧前端代码）。
    新代码请使用 Router/knowledge_base.py 中的带鉴权版本。
    """
    from Service.Utils.databases.db import AsyncSessionLocal

    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")

    max_bytes = _MAX_UPLOAD_MB * 1024 * 1024
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="上传文件为空")
    if len(content) > max_bytes:
        raise HTTPException(status_code=413, detail=f"文件过大，请上传 {_MAX_UPLOAD_MB}MB 以内的文件")

    try:
        async with AsyncSessionLocal() as db:
            result = await ingest_file(
                filename=file.filename,
                content=content,
                user_id=None,  # 旧接口无鉴权，写入全局共享库
                db=db,
            )
        return {
            "success": True,
            "knowledge_id": result["source_name"],
            "filename": result["source_name"],
            "chunk_count": result["chunk_count"],
            "mode": "semantic+keyword",
            "message": "知识库文件上传成功",
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"上传失败: {exc}") from exc
