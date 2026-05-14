import io
import os
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import APIRouter, File, HTTPException, UploadFile


router = APIRouter(prefix="/api/knowledge", tags=["Knowledge"])

SYSTEM_ZHANGXUEFENG_KNOWLEDGE_ID = "system_zhangxuefeng"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SYSTEM_KNOWLEDGE_DIR = PROJECT_ROOT / "data" / "system_knowledge"


@dataclass
class KnowledgeBase:
    """单个文件或系统目录对应的轻量知识库对象。"""

    knowledge_id: str
    filename: str
    chunks: List[str]
    vector_store: Optional[object]
    created_at: str
    mode: str
    source: str = "user"


# 进程内知识库：适合 MVP 和单机演示。
# 注意：服务重启后用户上传知识库会丢失；系统知识库会在 startup 时重新索引。
KNOWLEDGE_BASES: Dict[str, KnowledgeBase] = {}

# Embedding 模型全局缓存，避免每次上传文件都重复加载模型。
_EMBEDDINGS = None


def _get_embeddings():
    """懒加载 Embedding 模型。

    默认使用适合中文和英文的轻量多语言模型。首次运行时 sentence-transformers
    可能会从 HuggingFace 下载模型；如果部署环境不能联网，请提前把模型缓存好，
    或通过 RAG_EMBEDDING_MODEL 指向本地模型目录。
    """
    global _EMBEDDINGS
    if _EMBEDDINGS is not None:
        return _EMBEDDINGS

    try:
        from langchain_community.embeddings import HuggingFaceEmbeddings

        model_name = os.getenv(
            "RAG_EMBEDDING_MODEL",
            "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        )
        _EMBEDDINGS = HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs={"device": os.getenv("RAG_EMBEDDING_DEVICE", "cpu")},
            encode_kwargs={"normalize_embeddings": True},
        )
        return _EMBEDDINGS
    except Exception as exc:
        print(f"[RAG] Embedding 模型加载失败，将退回关键词检索: {exc}")
        return None


async def _read_upload_file(file: UploadFile) -> bytes:
    """安全读取上传文件，并限制单文件大小。"""
    max_mb = int(os.getenv("RAG_MAX_UPLOAD_MB", "20"))
    max_bytes = max_mb * 1024 * 1024

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="上传文件为空")
    if len(content) > max_bytes:
        raise HTTPException(status_code=413, detail=f"文件过大，请上传 {max_mb}MB 以内的文件")
    return content


def _decode_text(content: bytes) -> str:
    """兼容常见中文编码读取纯文本类文件。"""
    for encoding in ("utf-8-sig", "utf-8", "gb18030", "gbk"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="ignore")


def _extract_text_from_pdf(content: bytes) -> str:
    """从 PDF 中提取文本。"""
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(content))
        pages = []
        for index, page in enumerate(reader.pages):
            try:
                text = page.extract_text() or ""
                if text.strip():
                    pages.append(f"\n\n[第 {index + 1} 页]\n{text.strip()}")
            except Exception as page_exc:
                print(f"[RAG] PDF 第 {index + 1} 页解析失败，已跳过: {page_exc}")
        return "\n".join(pages)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"PDF 解析失败: {exc}") from exc


def _extract_text_from_docx(content: bytes) -> str:
    """从 DOCX 文件中提取文本。"""
    try:
        from docx import Document

        doc = Document(io.BytesIO(content))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n".join(paragraphs)
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="服务器缺少 python-docx 依赖，无法解析 Word 文件",
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"DOCX 解析失败: {exc}") from exc


def _extract_text_from_image(content: bytes) -> str:
    """从图片中通过 OCR 提取文本 — 直接调用 SDK，消除死锁。"""
    import base64

    from Service.Utils.ocr_sdk import recognize_image_text

    base64_str = base64.b64encode(content).decode("utf-8")
    result = recognize_image_text(f"data:image/png;base64,{base64_str}")

    if not result or "图片解析失败" in result:
        raise HTTPException(
            status_code=400,
            detail="图片 OCR 识别失败，请确保图片清晰",
        )

    return result


def extract_text_from_file(filename: str, content: bytes) -> str:
    """根据文件扩展名选择解析器。"""
    suffix = os.path.splitext(filename.lower())[1]
    if suffix == ".pdf":
        text = _extract_text_from_pdf(content)
    elif suffix in {".txt", ".md"}:
        text = _decode_text(content)
    elif suffix in {".docx", ".doc"}:
        text = _extract_text_from_docx(content)
    elif suffix in {".jpg", ".jpeg", ".png", ".webp"}:
        text = _extract_text_from_image(content)
    else:
        raise HTTPException(
            status_code=400,
            detail="不支持的文件格式，请上传 PDF、Word、TXT、MD 或图片文件",
        )

    text = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    if not text:
        raise HTTPException(status_code=400, detail="未能从文件中提取到有效文本")
    return text


def split_text(text: str) -> List[str]:
    """把长文档切成适合检索和注入 Prompt 的片段。"""
    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=int(os.getenv("RAG_CHUNK_SIZE", "800")),
            chunk_overlap=int(os.getenv("RAG_CHUNK_OVERLAP", "120")),
            separators=["\n\n", "\n", "。", "！", "？", ";", "；", "，", " ", ""],
        )
        chunks = splitter.split_text(text)
    except Exception as exc:
        print(f"[RAG] LangChain 分块失败，将使用朴素分块: {exc}")
        chunk_size = int(os.getenv("RAG_CHUNK_SIZE", "800"))
        overlap = int(os.getenv("RAG_CHUNK_OVERLAP", "120"))
        chunks = []
        start = 0
        while start < len(text):
            chunks.append(text[start : start + chunk_size])
            start += max(chunk_size - overlap, 1)

    return [chunk.strip() for chunk in chunks if chunk.strip()]


def _build_vector_store(chunks: List[str]):
    """基于 DocArrayInMemorySearch 构建内存向量库。"""
    embeddings = _get_embeddings()
    if embeddings is None:
        return None

    try:
        from langchain_community.vectorstores import DocArrayInMemorySearch

        return DocArrayInMemorySearch.from_texts(chunks, embedding=embeddings)
    except Exception as exc:
        print(f"[RAG] 内存向量库构建失败，将退回关键词检索: {exc}")
        return None


def _create_knowledge_base_from_text(
    *,
    knowledge_id: str,
    filename: str,
    text: str,
    source: str,
) -> KnowledgeBase:
    """复用同一套分块和向量化逻辑创建知识库。"""
    chunks = split_text(text)
    if not chunks:
        raise ValueError("文档分块后没有可检索内容")

    vector_store = _build_vector_store(chunks)
    knowledge_base = KnowledgeBase(
        knowledge_id=knowledge_id,
        filename=filename,
        chunks=chunks,
        vector_store=vector_store,
        created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        mode="vector" if vector_store is not None else "keyword_fallback",
        source=source,
    )
    KNOWLEDGE_BASES[knowledge_id] = knowledge_base
    return knowledge_base


def init_system_knowledge() -> Optional[KnowledgeBase]:
    """启动时索引 data/system_knowledge 下的系统级 Markdown 知识库。

    该知识库固定 ID 为 system_zhangxuefeng，专门服务【张雪峰分身】。
    如果目录不存在或没有 .md 文件，函数会安静跳过，不影响服务启动。
    """
    try:
        SYSTEM_KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
        # 递归扫描所有 Markdown 文件，支持在 data/system_knowledge 下按主题建立多级子目录。
        md_files = sorted(SYSTEM_KNOWLEDGE_DIR.rglob("*.md"))
        if not md_files:
            print(f"[RAG] 系统知识库目录暂无 .md 文件: {SYSTEM_KNOWLEDGE_DIR}")
            KNOWLEDGE_BASES.pop(SYSTEM_ZHANGXUEFENG_KNOWLEDGE_ID, None)
            return None

        documents = []
        for md_file in md_files:
            try:
                content = md_file.read_bytes()
                text = extract_text_from_file(md_file.name, content)
                relative_path = md_file.relative_to(SYSTEM_KNOWLEDGE_DIR).as_posix()
                documents.append(f"# 来源文件：{relative_path}\n\n{text}")
            except Exception as file_exc:
                print(f"[RAG] 系统知识文件解析失败，已跳过 {md_file}: {file_exc}")

        merged_text = "\n\n---\n\n".join(documents).strip()
        if not merged_text:
            print("[RAG] 系统知识库没有可索引文本")
            KNOWLEDGE_BASES.pop(SYSTEM_ZHANGXUEFENG_KNOWLEDGE_ID, None)
            return None

        knowledge_base = _create_knowledge_base_from_text(
            knowledge_id=SYSTEM_ZHANGXUEFENG_KNOWLEDGE_ID,
            filename="system_knowledge/*.md",
            text=merged_text,
            source="system",
        )
        print(
            "[RAG] 系统知识库已挂载: "
            f"{SYSTEM_ZHANGXUEFENG_KNOWLEDGE_ID}, files={len(md_files)}, "
            f"chunks={len(knowledge_base.chunks)}, mode={knowledge_base.mode}"
        )
        return knowledge_base
    except Exception as exc:
        print(f"[RAG] 系统知识库初始化失败，服务继续启动: {exc}")
        return None


def _keyword_fallback_search(query: str, chunks: List[str], top_k: int) -> List[str]:
    """当向量能力不可用时的兜底检索，保证系统仍可用。"""
    query_terms = {term for term in query.lower().split() if term.strip()}
    scored = []

    for chunk in chunks:
        lower_chunk = chunk.lower()
        score = sum(1 for term in query_terms if term in lower_chunk)
        if query and query in chunk:
            score += 5
        scored.append((score, chunk))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [chunk for score, chunk in scored[:top_k] if score > 0] or chunks[:top_k]


async def create_knowledge_base(file: UploadFile) -> KnowledgeBase:
    """解析上传文件并创建用户知识库。"""
    try:
        filename = file.filename or "unknown"
        content = await _read_upload_file(file)
        text = extract_text_from_file(filename, content)
        return _create_knowledge_base_from_text(
            knowledge_id=str(uuid.uuid4()),
            filename=filename,
            text=text,
            source="user",
        )
    except HTTPException:
        raise
    except Exception as exc:
        print(f"[RAG] 创建知识库失败: {exc}")
        raise HTTPException(status_code=500, detail=f"知识库创建失败: {exc}") from exc


def search_knowledge(knowledge_id: str, query: str, top_k: int = 4) -> List[str]:
    """从指定知识库中检索和用户问题最相关的 Top-K 文本片段。"""
    if not knowledge_id:
        return []

    knowledge_base = KNOWLEDGE_BASES.get(knowledge_id)
    if knowledge_base is None:
        raise ValueError("knowledge_id 不存在或服务已重启，请重新上传文件")

    top_k = max(1, min(top_k, 8))
    try:
        if knowledge_base.vector_store is not None:
            docs = knowledge_base.vector_store.similarity_search(query, k=top_k)
            return [doc.page_content for doc in docs if getattr(doc, "page_content", "").strip()]
        return _keyword_fallback_search(query, knowledge_base.chunks, top_k)
    except Exception as exc:
        print(f"[RAG] 向量检索失败，将退回关键词检索: {exc}")
        return _keyword_fallback_search(query, knowledge_base.chunks, top_k)


def build_context_block(knowledge_id: Optional[str], query: str, top_k: int = 4) -> str:
    """把检索结果包装成可注入专家 Prompt 的上下文块。"""
    if not knowledge_id:
        return ""

    knowledge_base = KNOWLEDGE_BASES.get(knowledge_id)
    snippets = search_knowledge(knowledge_id, query, top_k=top_k)
    if not snippets:
        return ""

    source_label = "系统预设知识库" if knowledge_base and knowledge_base.source == "system" else "用户上传知识库"
    formatted = []
    for index, snippet in enumerate(snippets, start=1):
        formatted.append(f"[片段 {index}]\n{snippet[:1500]}")

    return (
        f"【知识库 Context：{source_label}】\n"
        "以下内容来自已挂载知识库。回答时请优先依据这些材料；如果材料不足，请明确说明不足，不要编造。\n\n"
        + "\n\n".join(formatted)
    )


@router.post("/upload")
async def upload_knowledge(file: UploadFile = File(...)):
    """上传 PDF/TXT/MD 文件并创建轻量知识库。"""
    try:
        knowledge_base = await create_knowledge_base(file)
        return {
            "success": True,
            "knowledge_id": knowledge_base.knowledge_id,
            "filename": knowledge_base.filename,
            "chunk_count": len(knowledge_base.chunks),
            "mode": knowledge_base.mode,
            "message": "知识库文件上传成功",
        }
    except HTTPException:
        raise
    except Exception as exc:
        print(f"[RAG] 上传接口异常: {exc}")
        raise HTTPException(status_code=500, detail=f"上传失败: {exc}") from exc


@router.get("/{knowledge_id}")
async def get_knowledge_info(knowledge_id: str):
    """查询知识库元信息，便于前端展示上传状态。"""
    knowledge_base = KNOWLEDGE_BASES.get(knowledge_id)
    if knowledge_base is None:
        raise HTTPException(status_code=404, detail="知识库不存在")

    return {
        "success": True,
        "knowledge_id": knowledge_base.knowledge_id,
        "filename": knowledge_base.filename,
        "chunk_count": len(knowledge_base.chunks),
        "mode": knowledge_base.mode,
        "source": knowledge_base.source,
        "created_at": knowledge_base.created_at,
    }
