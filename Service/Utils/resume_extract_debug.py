"""
Service/Utils/resume_extract_debug.py — Resume Builder 取证记录器

仅诊断用。开启 Settings.DEBUG_MODE 时,每次 /api/document/extract-resume 请求
会把以下六类产物写到 `debug/resume_extract/{request_id}_*.{txt,json}`:

    {rid}_raw_first.txt    — 第一次 LLM 原始返回(text 原样)
    {rid}_raw_retry.txt    — 重试 LLM 原始返回(text 原样)
    {rid}_parsed.json      — parse_resume_json 解析成功后的 dict
    {rid}_normalized.json  — normalize_resume_json + enforce_missing_fields_invariant 后的 dict
    {rid}_response.json    — 最终 ExtractResumeResponse 的 dict 形态
    {rid}_error.json       — 任何阶段的错误诊断(reason / msg / lineno / pos / raw_tail / contract_error)

约束:
  - DEBUG_MODE=false 时所有写入都是 no-op(零成本)
  - 不写入 .env 任何 key、不写入 JWT、不写入 user_id
  - 写入失败一律 swallow,不能让取证逻辑反过来污染主链路
  - 文件路径 debug/ 已在 .gitignore 中,绝不入库
  - 单文件最大保留 200 KiB(防止 LLM 偶尔吐百万字日志撑爆磁盘)
"""

from __future__ import annotations

import json
import os
import secrets
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

try:  # 导入失败也不能影响业务
    from Settings.config import DEBUG_MODE
except Exception:  # noqa: BLE001
    DEBUG_MODE = False

_DEBUG_ROOT = Path("debug") / "resume_extract"
_MAX_BYTES = 200 * 1024  # 单文件 200 KiB 截断


def is_debug_enabled() -> bool:
    """是否启用取证。生产环境必须为 False。"""
    return bool(DEBUG_MODE)


def new_request_id() -> str:
    """生成短 request_id(精确到毫秒 + 4 字节随机熵)。"""
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    # 加毫秒 + 随机熵,防止同一秒内多次请求碰撞
    ms = int((time.time() % 1) * 1000)
    rand = secrets.token_hex(2)
    return f"{ts}-{ms:03d}-{rand}"


def _ensure_dir() -> Optional[Path]:
    """确保 debug 目录存在。失败返回 None。"""
    if not is_debug_enabled():
        return None
    try:
        _DEBUG_ROOT.mkdir(parents=True, exist_ok=True)
        return _DEBUG_ROOT
    except OSError:
        return None


def _truncate_bytes(data: bytes, limit: int = _MAX_BYTES) -> bytes:
    if len(data) <= limit:
        return data
    suffix = b"\n\n[truncated by debug recorder]\n"
    keep = max(0, limit - len(suffix))
    return data[:keep] + suffix


def _safe_write(path: Path, payload: bytes) -> None:
    try:
        path.write_bytes(_truncate_bytes(payload))
    except OSError:
        # 取证失败不能反过来污染主链路
        pass


def save_text(request_id: str, kind: str, text: str) -> None:
    """
    保存 raw_first / raw_retry 这种纯文本产物。

    kind 取值: 'raw_first' | 'raw_retry'
    """
    if not is_debug_enabled() or not request_id or not text:
        return
    root = _ensure_dir()
    if root is None:
        return
    path = root / f"{request_id}_{kind}.txt"
    _safe_write(path, text.encode("utf-8", errors="replace"))


def save_json(request_id: str, kind: str, obj: Any) -> None:
    """
    保存 parsed / normalized / response / error 这种结构化产物。

    kind 取值: 'parsed' | 'normalized' | 'response' | 'error'
    """
    if not is_debug_enabled() or not request_id:
        return
    root = _ensure_dir()
    if root is None:
        return
    path = root / f"{request_id}_{kind}.json"
    try:
        text = json.dumps(obj, ensure_ascii=False, indent=2, default=_default_serializer)
    except (TypeError, ValueError):
        # 兜底:json.dumps 失败时退化成 repr
        text = repr(obj)
    _safe_write(path, text.encode("utf-8", errors="replace"))


def _default_serializer(value: Any) -> Any:
    """让 json.dumps 能吃下 Pydantic / set / Path 等常见类型。"""
    if hasattr(value, "model_dump"):  # Pydantic v2
        try:
            return value.model_dump()
        except Exception:  # noqa: BLE001
            return repr(value)
    if hasattr(value, "dict"):  # Pydantic v1
        try:
            return value.dict()
        except Exception:  # noqa: BLE001
            return repr(value)
    if isinstance(value, set):
        return sorted(value, key=str)
    if isinstance(value, Path):
        return str(value)
    return repr(value)
