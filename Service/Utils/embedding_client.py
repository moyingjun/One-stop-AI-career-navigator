"""
Service/Utils/embedding_client.py — 云端 Embedding API 客户端

⚠️  资源防御：绝对禁止引入 torch、sentence-transformers 等重型 ML 库。
    所有向量化操作通过 httpx 调用外部 API 完成（兼容 OpenAI /v1/embeddings 规范）。

支持的 API 格式（OpenAI 兼容）：
    POST /v1/embeddings
    Body: { "model": "BAAI/bge-m3", "input": ["text1", "text2"] }
    Response: { "data": [{ "embedding": [0.1, 0.2, ...] }, ...] }
"""

import logging
from typing import List

import httpx

from Service.Settings.config import EMBEDDING_API_KEY, EMBEDDING_API_URL, EMBEDDING_MODEL_NAME

logger = logging.getLogger(__name__)

# Embedding API 端点（确保路径正确）
_EMBED_ENDPOINT = f"{EMBEDDING_API_URL.rstrip('/')}/embeddings"

# httpx 客户端超时配置（Embedding 请求可能较慢）
_TIMEOUT = httpx.Timeout(connect=5.0, read=30.0, write=10.0, pool=5.0)


async def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    批量将文本列表转换为向量（异步）。

    调用外部 Embedding API（OpenAI /v1/embeddings 兼容格式）。
    单次调用建议不超过 32 条文本，避免超时。

    参数：
        texts — 待向量化的文本列表（非空字符串）

    返回：
        与 texts 等长的向量列表，每个向量为 float 列表

    抛出：
        RuntimeError — API 调用失败或响应格式异常时
    """
    if not texts:
        return []

    # 截断过长文本，防止超出 API token 限制（BGE-M3 最大 8192 tokens）
    truncated = [t[:4000] for t in texts]

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {EMBEDDING_API_KEY}",
    }

    payload = {
        "model": EMBEDDING_MODEL_NAME,
        "input": truncated,
    }

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.post(_EMBED_ENDPOINT, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        # 解析 OpenAI 兼容格式：data[].embedding
        embeddings_data = data.get("data", [])
        if len(embeddings_data) != len(texts):
            raise RuntimeError(
                f"Embedding API 返回数量不匹配：期望 {len(texts)}，实际 {len(embeddings_data)}"
            )

        vectors = [item["embedding"] for item in embeddings_data]
        logger.debug("Embedding 成功 | count=%d | model=%s", len(texts), EMBEDDING_MODEL_NAME)
        return vectors

    except httpx.TimeoutException as exc:
        logger.error("Embedding API 超时 | endpoint=%s", _EMBED_ENDPOINT)
        raise RuntimeError("Embedding API 请求超时，请稍后重试") from exc
    except httpx.HTTPStatusError as exc:
        logger.error(
            "Embedding API 返回错误状态码 | status=%d | body=%s",
            exc.response.status_code,
            exc.response.text[:200],
        )
        raise RuntimeError(f"Embedding API 错误（HTTP {exc.response.status_code}）") from exc
    except (KeyError, IndexError, TypeError) as exc:
        logger.error("Embedding API 响应格式异常 | error=%s", str(exc))
        raise RuntimeError("Embedding API 响应格式异常") from exc


async def embed_single(text: str) -> List[float]:
    """
    将单条文本转换为向量（异步）。

    参数：
        text — 待向量化的文本

    返回：
        向量（float 列表）

    抛出：
        RuntimeError — API 调用失败时
    """
    results = await embed_texts([text])
    return results[0]


def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """
    计算两个向量的余弦相似度（纯 Python 实现，无需 numpy）。

    ⚠️  2C4G 资源防御：不引入 numpy/scipy，用标准库实现。
        对于 RAG Top-K 检索（通常 < 1000 个 chunk），性能完全足够。

    参数：
        vec_a, vec_b — 等长的 float 列表

    返回：
        余弦相似度（-1.0 ~ 1.0），向量为零向量时返回 0.0
    """
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0

    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = sum(a * a for a in vec_a) ** 0.5
    norm_b = sum(b * b for b in vec_b) ** 0.5

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    return dot / (norm_a * norm_b)
