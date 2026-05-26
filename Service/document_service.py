"""
Service/document_service.py — 文档工作台业务编排（D1.2 升级）

职责：
  - 校验输入（text 长度 / style 白名单 / rewrite_mode 白名单 / strength 范围 / custom_instruction 长度）
  - 处理 rewrite_strength（主） + rewrite_level（旧字段降级映射）
  - 组装 system prompt + user prompt
  - 调用 Service/Utils/llm_client.complete_chat
  - 清洗输出（去除 LLM 习惯加上的引号 / 前导语）；suggest 模式保留结构
  - 不写历史 / 不写知识库 / 不写数据库

设计约束：
  - 不直接 import httpx，全部走 llm_client
  - Prompt 字符串放在 Service/Agents/prompts/document_prompts.py（不在本文件硬编码）
"""

from __future__ import annotations

from typing import Optional

from Service.Agents.prompts.document_prompts import (
    LEVEL_WHITELIST,
    MODE_WHITELIST,
    STRENGTH_MAX,
    STRENGTH_MIN,
    STYLE_WHITELIST,
    build_rewrite_messages,
    coerce_strength,
    level_to_strength,
)
from Service.Utils.llm_client import LLMClientError, complete_chat

MAX_REWRITE_TEXT_CHARS = 3000
MAX_CUSTOM_INSTRUCTION_CHARS = 300


def _temperature_for_strength(strength: int, mode: str) -> float:
    """
    根据 strength（0-100）+ mode 选择温度。
    - polish: 0.2 ~ 0.5
    - suggest: 0.3 ~ 0.5（建议清单不需要太发散）
    - draft: 0.4 ~ 0.7（草稿允许稍微发散，但仍受占位符约束）
    """
    if mode == "polish":
        if strength <= 30:
            return 0.2
        if strength <= 70:
            return 0.4
        return 0.5
    if mode == "suggest":
        if strength <= 30:
            return 0.3
        if strength <= 70:
            return 0.4
        return 0.5
    # draft
    if strength <= 30:
        return 0.4
    if strength <= 70:
        return 0.55
    return 0.7


def _sanitize_polish_or_draft_output(raw: str) -> str:
    """
    polish / draft 模式输出清洗：
      - 剥离 markdown 围栏
      - 剥离常见前导语
      - 剥离首尾对称引号
    suggest 模式不走此函数（保留结构化清单）。
    """
    text = raw.strip()
    if not text:
        raise ValueError("AI 未返回有效内容")

    if text.startswith("```"):
        first_newline = text.find("\n")
        if first_newline != -1:
            text = text[first_newline + 1 :]
        if text.endswith("```"):
            text = text[: -3]
        text = text.strip()

    for prefix in (
        "改写后:", "改写后：", "改写：", "改写:",
        "建议:", "建议：",
        "草稿:", "草稿：",
        "以下是改写后的文本:", "以下是改写后的文本：",
        "以下是改写后的文本",
        "Here is the rewritten text:",
    ):
        if text.startswith(prefix):
            text = text[len(prefix) :].lstrip()

    if (
        len(text) >= 2
        and text[0] in ("\"", "'", "“", "‘")
        and text[-1] in ("\"", "'", "”", "’")
    ):
        text = text[1:-1].strip()

    if not text:
        raise ValueError("AI 未返回有效内容")
    return text


def _sanitize_suggest_output(raw: str) -> str:
    """
    suggest 模式：保留结构化清单，仅做最浅清洗。
      - 剥离围栏 / 前导语
      - 不剥离引号（清单内可能包含引用）
    """
    text = raw.strip()
    if not text:
        raise ValueError("AI 未返回有效内容")

    if text.startswith("```"):
        first_newline = text.find("\n")
        if first_newline != -1:
            text = text[first_newline + 1 :]
        if text.endswith("```"):
            text = text[: -3]
        text = text.strip()

    for prefix in (
        "以下是建议:", "以下是建议：",
        "Here are the suggestions:",
    ):
        if text.startswith(prefix):
            text = text[len(prefix) :].lstrip()

    if not text:
        raise ValueError("AI 未返回有效内容")
    return text


def _resolve_strength(
    rewrite_strength: Optional[int],
    rewrite_level: Optional[str],
) -> int:
    """
    解析最终使用的 strength：
      - 显式传入 rewrite_strength → 钳制到 [0, 100]
      - 否则 fallback 到 rewrite_level 的映射（D1.1 兼容）
      - 否则默认 50
    """
    if rewrite_strength is not None:
        return coerce_strength(rewrite_strength, default=50)
    mapped = level_to_strength(rewrite_level)
    if mapped is not None:
        return mapped
    return 50


async def rewrite_text(
    text: str,
    style: str,
    rewrite_mode: str = "polish",
    rewrite_strength: Optional[int] = None,
    rewrite_level: Optional[str] = None,
    custom_instruction: Optional[str] = None,
    provider_id: Optional[str] = None,
) -> str:
    """
    AI 润色 / 建议 / 草稿入口：返回纯文本结果。

    参数：
      - rewrite_mode：polish / suggest / draft
      - rewrite_strength：主字段，0-100
      - rewrite_level：兼容 D1.1 旧字段；仅在 rewrite_strength 缺省时降级使用

    Raises:
        ValueError — 输入校验失败
        LLMClientError — LLM 调用失败 / 空返回
    """
    if not isinstance(text, str):
        raise ValueError("text 必须是字符串")
    cleaned = text.strip()
    if not cleaned:
        raise ValueError("text 不能为空")
    if len(cleaned) > MAX_REWRITE_TEXT_CHARS:
        raise ValueError(f"text 超过 {MAX_REWRITE_TEXT_CHARS} 字上限")
    if style not in STYLE_WHITELIST:
        raise ValueError(f"style 不在白名单内: {STYLE_WHITELIST}")
    if rewrite_mode not in MODE_WHITELIST:
        raise ValueError(f"rewrite_mode 不在白名单内: {MODE_WHITELIST}")
    if rewrite_level is not None and rewrite_level not in LEVEL_WHITELIST:
        raise ValueError(f"rewrite_level 不在白名单内: {LEVEL_WHITELIST}")
    if rewrite_strength is not None:
        if not isinstance(rewrite_strength, int):
            raise ValueError("rewrite_strength 必须是整数")
        if rewrite_strength < STRENGTH_MIN or rewrite_strength > STRENGTH_MAX:
            raise ValueError(
                f"rewrite_strength 必须在 [{STRENGTH_MIN}, {STRENGTH_MAX}] 范围内"
            )
    if custom_instruction is not None:
        if not isinstance(custom_instruction, str):
            raise ValueError("custom_instruction 必须是字符串或 None")
        if len(custom_instruction) > MAX_CUSTOM_INSTRUCTION_CHARS:
            raise ValueError(
                f"custom_instruction 超过 {MAX_CUSTOM_INSTRUCTION_CHARS} 字上限"
            )

    final_strength = _resolve_strength(rewrite_strength, rewrite_level)

    messages = build_rewrite_messages(
        text=cleaned,
        style=style,
        rewrite_mode=rewrite_mode,
        rewrite_strength=final_strength,
        custom_instruction=custom_instruction,
    )

    raw = await complete_chat(
        messages=messages,
        temperature=_temperature_for_strength(final_strength, rewrite_mode),
        max_tokens=2048,
        timeout=60.0,
        provider_id=provider_id,
    )
    if raw is None or not raw.strip():
        raise LLMClientError("AI 未返回有效内容")

    try:
        if rewrite_mode == "suggest":
            return _sanitize_suggest_output(raw)
        return _sanitize_polish_or_draft_output(raw)
    except ValueError as exc:
        raise LLMClientError(str(exc))



# ═════════════════════════════════════════════════════════════════════════════
# 简历抽取(Extract_Resume_API)业务编排 — Resume Preview Builder MVP
# ═════════════════════════════════════════════════════════════════════════════

import asyncio
from typing import Any, Optional

from Router.models.document_model import (
    ExtractResumeResponse,
    MAX_EXTRACT_CONTENT_JSON_BYTES,
    MAX_EXTRACT_PLAIN_TEXT_CHARS,
)
from Service.Agents.resume_extract_agent import (
    RESUME_EXTRACT_LLM_TIMEOUT_SECONDS_FIRST,
    RESUME_EXTRACT_LLM_TIMEOUT_SECONDS_RETRY,
    ResumeExtractAgent,
)
from Service.Utils.llm_client import LLMClientError
from Service.Utils.resume_extract_debug import (
    is_debug_enabled as _debug_enabled,
    save_json as _debug_save_json,
    save_text as _debug_save_text,
)
from Service.Utils.resume_json_validator import (
    build_safe_skeleton,
    detect_fabrication,
    detect_non_resume_content,
    enforce_missing_fields_invariant,
    normalize_resume_json,
    parse_resume_json,
    parse_resume_json_with_diag,
    utc_now_iso8601,
    validate_resume_json_contract,
)

# Requirement 4.8 原本规定 30 秒,Hotfix 4 升级为分层超时(首次 90s + 重试 45s)以应对真实
# Mimo / DeepSeek thinking 模型,具体常量定义在 resume_extract_agent.py 中。
EXTRACT_TIMEOUT_SECONDS = RESUME_EXTRACT_LLM_TIMEOUT_SECONDS_FIRST


def _is_effectively_empty(plain_text: Any, content_json: Any) -> bool:
    """plain_text 与 content_json 是否同时为"空"(Requirement 4.5)。"""
    pt_blank = not isinstance(plain_text, str) or not plain_text.strip()
    if not pt_blank:
        return False
    if content_json is None or content_json == {}:
        return True
    if not isinstance(content_json, dict):
        return False
    # 递归检查是否含任何非空 text
    chunks: list[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            text = node.get("text")
            if isinstance(text, str) and text.strip():
                chunks.append(text)
            children = node.get("content")
            if isinstance(children, list):
                for child in children:
                    walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(content_json)
    return len(chunks) == 0


def _build_skeleton_response(
    document_id: str,
    warnings: list[str],
    request_id: str = "",
) -> ExtractResumeResponse:
    """构造一份基于安全骨架的失败响应(Requirement 4.5 / 4.6 / 4.8 / 11.2)。"""
    skeleton = build_safe_skeleton(document_id)
    return ExtractResumeResponse(
        success=False,
        resume_json=skeleton,
        warnings=list(warnings),
        missing_questions=[],
        debug_request_id=request_id or None,
    )


def _filter_missing_questions(raw: Any) -> list[str]:
    """过滤 missing_questions:每条必须为字符串且长度 ∈ [8, 80](Requirement 2.6)。"""
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for item in raw:
        if not isinstance(item, str):
            continue
        s = item.strip()
        if 8 <= len(s) <= 80:
            out.append(s)
    return out


def _log_parse_failure(raw_text: str, diag: dict, *, stage: str) -> None:
    """
    Hotfix 6:把 parse_resume_json_with_diag 的失败原因详细打印出来。

    覆盖:
      - JSONDecodeError msg / lineno / colno / pos
      - unbalanced_json_object(疑似 max_tokens 截断)
      - raw_len + raw_tail 后 800 字(转义换行)
    """
    if not isinstance(diag, dict):
        diag = {"reason": "unknown"}
    reason = diag.get("reason", "unknown")
    raw_len = diag.get("raw_len", len(raw_text or ""))
    print(
        f"[extract-resume] {stage}_diag reason={reason}"
        f" raw_len={raw_len}"
    )
    if reason == "json_decode_error":
        print(
            f"[extract-resume] {stage}_diag json_msg={diag.get('msg')!r}"
            f" lineno={diag.get('lineno')} colno={diag.get('colno')} pos={diag.get('pos')}"
        )
    if reason == "unbalanced_json_object":
        print(
            f"[extract-resume] {stage}_diag first_brace_pos={diag.get('first_brace_pos')}"
            " 提示:JSON 未闭合,疑似 max_tokens 截断"
        )
    tail = diag.get("raw_tail")
    if isinstance(tail, str) and tail:
        # 截断到 800 字以避免日志爆炸
        if len(tail) > 800:
            tail = tail[-800:]
        print(f"[extract-resume] {stage}_diag raw_tail={tail}")


async def extract_resume_from_draft(
    *,
    document_id: str,
    plain_text: str,
    content_json: dict,
    provider_id: Optional[str] = None,
    request_id: str = "",
) -> ExtractResumeResponse:
    """
    Extract_Resume_API 业务编排入口。

    设计契约:
      - HTTP 始终返回 200 + 业务级 success;失败也必须给出安全骨架。
      - 不向上抛 5xx(Router 兜底,但本函数尽量不让其发生)。
      - 不接 RAG / 历史 / 知识库,仅调用 LLM 单次抽取(Requirement 11.5)。

    取证(仅 DEBUG_MODE=true 时):
      - request_id 由 Router 层生成并贯穿日志 + 写入 debug 产物文件。
      - 6 类产物:raw_first / raw_retry / parsed / normalized / response / error。
      - 文件路径见 Service/Utils/resume_extract_debug.py。
    """
    rid_tag = f"[rid:{request_id}] " if request_id else ""
    debug_on = _debug_enabled() and bool(request_id)

    # 诊断日志(非敏感):草稿长度
    print(f"[extract-resume] {rid_tag}plain_text_len={len(plain_text or '')}")
    print(
        f"[extract-resume] {rid_tag}llm_timeout_seconds={int(RESUME_EXTRACT_LLM_TIMEOUT_SECONDS_FIRST)}"
        f" llm_retry_timeout_seconds={int(RESUME_EXTRACT_LLM_TIMEOUT_SECONDS_RETRY)}"
    )

    def _record_response(resp: ExtractResumeResponse, *, stage: str) -> ExtractResumeResponse:
        """统一日志 + 产物写入,确保返回前一定记下。"""
        print(
            f"[extract-resume] {rid_tag}response stage={stage}"
            f" success={resp.success} warnings={list(resp.warnings)}"
        )
        if debug_on:
            try:
                _debug_save_json(
                    request_id,
                    "response",
                    {
                        "stage": stage,
                        "success": resp.success,
                        "warnings": list(resp.warnings),
                        "missing_questions": list(resp.missing_questions),
                        "resume_json": resp.resume_json,
                        "debug_request_id": resp.debug_request_id,
                    },
                )
            except Exception:  # noqa: BLE001
                pass
        return resp

    def _record_error(stage: str, payload: dict) -> None:
        """把任意阶段的失败原因写到 {rid}_error.json。"""
        if not debug_on:
            return
        try:
            _debug_save_json(
                request_id,
                "error",
                {"stage": stage, **payload},
            )
        except Exception:  # noqa: BLE001
            pass

    # 1) 空输入(Requirement 4.5)
    if _is_effectively_empty(plain_text, content_json):
        print(f"[extract-resume] {rid_tag}short_circuit=empty_input")
        _record_error("empty_input", {"plain_text_len": len(plain_text or "")})
        resp = _build_skeleton_response(document_id, ["empty_input"], request_id)
        return _record_response(resp, stage="empty_input")

    # 2) 越界防御(Pydantic 已挡,这里仅做兜底)
    if isinstance(plain_text, str) and len(plain_text) > MAX_EXTRACT_PLAIN_TEXT_CHARS:
        print(f"[extract-resume] {rid_tag}short_circuit=plain_text_oversized len={len(plain_text)}")
        _record_error("plain_text_oversized", {"plain_text_len": len(plain_text)})
        resp = _build_skeleton_response(document_id, ["empty_input"], request_id)
        return _record_response(resp, stage="oversized")

    agent = ResumeExtractAgent(provider_id=provider_id)

    # 3) 第一次抽取(Requirement 4.8 — 30s 超时)
    raw: Optional[str] = None
    try:
        raw = await asyncio.wait_for(
            agent.extract(
                plain_text=plain_text,
                content_json=content_json,
            ),
            timeout=EXTRACT_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        print(f"[extract-resume] {rid_tag}llm_first_call=timeout")
        _record_error("llm_first_call_timeout", {})
        resp = _build_skeleton_response(document_id, ["extraction_timeout"], request_id)
        return _record_response(resp, stage="llm_first_timeout")
    except LLMClientError as exc:
        print(f"[extract-resume] {rid_tag}llm_first_call=client_error msg={exc}")
        _record_error("llm_first_call_client_error", {"msg": str(exc)})
        resp = _build_skeleton_response(document_id, ["json_parse_failed"], request_id)
        return _record_response(resp, stage="llm_first_client_error")
    except Exception as exc:  # noqa: BLE001
        print(f"[extract-resume] {rid_tag}llm_first_call=unexpected {type(exc).__name__}: {exc}")
        _record_error(
            "llm_first_call_unexpected",
            {"type": type(exc).__name__, "msg": str(exc)},
        )
        resp = _build_skeleton_response(document_id, ["json_parse_failed"], request_id)
        return _record_response(resp, stage="llm_first_unexpected")

    # 诊断日志:LLM 原始返回长度 + 前 500 字预览(转义换行,避免破坏日志格式)
    raw_text = raw or ""
    print(f"[extract-resume] {rid_tag}raw_llm_len={len(raw_text)}")
    preview = raw_text[:500].replace("\n", "\\n").replace("\r", "")
    print(f"[extract-resume] {rid_tag}raw_llm_preview={preview}")
    if debug_on:
        _debug_save_text(request_id, "raw_first", raw_text)

    parsed, parse_diag = parse_resume_json_with_diag(raw)

    # 4) 解析失败时重试一次(Requirement 5.3)。重试用更短预算以避免用户累计等待 > 2 分钟。
    if parsed is None:
        # Hotfix 6:输出详细 parse 失败诊断,便于定位是否被 max_tokens 截断 / JSON 真的非法 / 其他
        _log_parse_failure(raw_text, parse_diag, stage="parse_first")
        _record_error("parse_first", {**parse_diag, "raw_len": len(raw_text)})
        print(
            f"[extract-resume] {rid_tag}parse_first=fail retrying once"
            f" retry_timeout={int(RESUME_EXTRACT_LLM_TIMEOUT_SECONDS_RETRY)}"
        )
        try:
            raw = await asyncio.wait_for(
                agent.extract(
                    plain_text=plain_text,
                    content_json=content_json,
                    is_retry=True,
                ),
                timeout=RESUME_EXTRACT_LLM_TIMEOUT_SECONDS_RETRY,
            )
            raw_text = raw or ""
            print(f"[extract-resume] {rid_tag}retry_raw_llm_len={len(raw_text)}")
            preview = raw_text[:500].replace("\n", "\\n").replace("\r", "")
            print(f"[extract-resume] {rid_tag}retry_raw_llm_preview={preview}")
            if debug_on:
                _debug_save_text(request_id, "raw_retry", raw_text)
            parsed, parse_diag = parse_resume_json_with_diag(raw)
            if parsed is None:
                # Hotfix 6:重试解析仍失败时,把 raw_tail 与 JSONDecodeError 细节一起打印
                _log_parse_failure(raw_text, parse_diag, stage="parse_retry")
                _record_error("parse_retry", {**parse_diag, "raw_len": len(raw_text)})
        except asyncio.TimeoutError:
            print(f"[extract-resume] {rid_tag}llm_retry_call=timeout")
            _record_error("llm_retry_call_timeout", {})
            resp = _build_skeleton_response(document_id, ["extraction_timeout"], request_id)
            return _record_response(resp, stage="llm_retry_timeout")
        except LLMClientError as exc:
            print(f"[extract-resume] {rid_tag}llm_retry_call=client_error msg={exc}")
            _record_error("llm_retry_call_client_error", {"msg": str(exc)})
            parsed = None
        except Exception as exc:  # noqa: BLE001
            print(f"[extract-resume] {rid_tag}llm_retry_call=unexpected {type(exc).__name__}: {exc}")
            _record_error(
                "llm_retry_call_unexpected",
                {"type": type(exc).__name__, "msg": str(exc)},
            )
            parsed = None

    if parsed is None:
        print(f"[extract-resume] {rid_tag}parse_retry=fail returning skeleton")
        resp = _build_skeleton_response(document_id, ["json_parse_failed"], request_id)
        return _record_response(resp, stage="parse_retry_fail")

    # 诊断日志:parse 后顶级键
    try:
        top_keys = list(parsed.keys())[:20]
    except Exception:  # noqa: BLE001
        top_keys = []
    print(f"[extract-resume] {rid_tag}parse_ok top_keys={top_keys}")
    if debug_on:
        _debug_save_json(request_id, "parsed", parsed)

    # 5) 抽出 _missing_questions(在 normalize 之前先剥离,避免 normalize 误吞)
    raw_missing_questions = parsed.pop("_missing_questions", []) if isinstance(parsed, dict) else []

    # 6) 归一化 + 不变量同步(hotfix:LLM 经常返回缺 missingFields / 字段是裸字符串等近似形态)
    parsed = normalize_resume_json(parsed, document_id)
    enforce_missing_fields_invariant(parsed)

    # 诊断日志:normalize 后的 basics + 各 Section 条目数
    try:
        basics_snapshot = parsed.get("basics") if isinstance(parsed, dict) else {}
    except Exception:  # noqa: BLE001
        basics_snapshot = {}
    print(f"[extract-resume] {rid_tag}normalized basics={basics_snapshot}")
    counts = {
        "education": len(parsed.get("education", {}).get("items", []) if isinstance(parsed, dict) else []),
        "projects": len(parsed.get("projects", {}).get("items", []) if isinstance(parsed, dict) else []),
        "experience": len(parsed.get("experience", {}).get("items", []) if isinstance(parsed, dict) else []),
        "skills": len(parsed.get("skills", {}).get("items", []) if isinstance(parsed, dict) else []),
        "awards": len(parsed.get("awards", {}).get("items", []) if isinstance(parsed, dict) else []),
        "certificates": len(parsed.get("certificates", {}).get("items", []) if isinstance(parsed, dict) else []),
    }
    print(f"[extract-resume] {rid_tag}normalized counts={counts}")
    if debug_on:
        _debug_save_json(
            request_id,
            "normalized",
            {"resume_json": parsed, "counts": counts},
        )

    # 7) 契约校验(Requirement 3.1 - 3.8 / 5.2)
    contract_error = validate_resume_json_contract(parsed)
    if contract_error is not None:
        # normalize 之后仍然失败属于真正畸形,记日志后落安全骨架
        print(f"[extract-resume] {rid_tag}validate_failed_after_normalize={contract_error}")
        _record_error(
            "validate_failed_after_normalize",
            {
                "contract_error": contract_error,
                "normalized_resume_json": parsed,
                "counts": counts,
            },
        )
        resp = _build_skeleton_response(document_id, ["json_parse_failed"], request_id)
        return _record_response(resp, stage="validate_failed")

    # 8) 反编造比对(Requirement 2.7 / 5.2)
    warnings: list[str] = []
    try:
        fabrication_fields = detect_fabrication(parsed, plain_text or "", content_json)
    except Exception:  # noqa: BLE001
        fabrication_fields = []
    if fabrication_fields:
        warnings.append("fabrication_suspected")

    # 9) 非简历内容启发式(Requirement 5.5)
    try:
        if detect_non_resume_content(plain_text or ""):
            warnings.append("non_resume_content_detected")
    except Exception:  # noqa: BLE001
        pass

    # 10) 注入 meta 默认值(Requirement 3.6 / 3.7)— normalize 已经设过,这里只做最终覆写
    meta = parsed.setdefault("meta", {})
    if not isinstance(meta, dict):
        meta = {}
        parsed["meta"] = meta
    meta["sourceDocumentId"] = document_id
    meta["generatedAt"] = utc_now_iso8601()
    template_id = meta.get("templateId")
    if template_id not in ("ats_single_column", "tech_two_column"):
        meta["templateId"] = "ats_single_column"
    meta["confirmedByUser"] = False

    # 11) 过滤 missing_questions(Requirement 2.6)
    missing_questions = _filter_missing_questions(raw_missing_questions)

    resp = ExtractResumeResponse(
        success=True,
        resume_json=parsed,
        warnings=warnings,
        missing_questions=missing_questions,
        debug_request_id=request_id or None,
    )
    return _record_response(resp, stage="success")
