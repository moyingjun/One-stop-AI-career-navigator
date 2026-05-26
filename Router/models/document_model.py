"""
Router/models/document_model.py — 文档工作台请求 / 响应模型
"""

from __future__ import annotations

import json
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

from Service.Agents.prompts.document_prompts import (
    LEVEL_WHITELIST,
    MODE_WHITELIST,
    STRENGTH_MAX,
    STRENGTH_MIN,
    STYLE_WHITELIST,
)

# 与前端约定的硬上限。前端会做 3000 字预校验；后端再做一次防御性校验。
MAX_REWRITE_TEXT_CHARS = 3000

# custom_instruction 上限。前端 textarea 也按 300 字硬限。
MAX_CUSTOM_INSTRUCTION_CHARS = 300


class RewriteRequest(BaseModel):
    """AI 润色请求体。"""

    text: str = Field(..., description="待改写的原文（已选中片段）", min_length=1)
    style: str = Field(..., description="改写风格枚举")
    custom_instruction: Optional[str] = Field(
        default=None,
        description="用户额外要求，最长 300 字，可为空。优先级低于安全约束。",
    )

    # D1.2 主字段
    rewrite_mode: str = Field(
        default="polish",
        description="模式：polish | suggest | draft",
    )
    rewrite_strength: int = Field(
        default=50,
        ge=STRENGTH_MIN,
        le=STRENGTH_MAX,
        description="表达增强度 0-100；0-30 保守 / 31-70 平衡 / 71-100 扩展",
    )

    # 兼容字段：旧 rewrite_level 仍允许传入，仅作降级映射，存在更高优先级的 rewrite_strength 时被忽略。
    rewrite_level: Optional[str] = Field(
        default=None,
        description="(已废弃) 旧字段 conservative | balanced | enhanced；仍接受以保持向后兼容",
    )

    provider_id: Optional[str] = Field(default=None, description="LLM Provider ID（可选）")

    @field_validator("text")
    @classmethod
    def _validate_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("text 不能为空")
        if len(stripped) > MAX_REWRITE_TEXT_CHARS:
            raise ValueError(f"text 超过 {MAX_REWRITE_TEXT_CHARS} 字上限")
        return value

    @field_validator("style")
    @classmethod
    def _validate_style(cls, value: str) -> str:
        if value not in STYLE_WHITELIST:
            raise ValueError(f"style 不在白名单内: {STYLE_WHITELIST}")
        return value

    @field_validator("rewrite_mode")
    @classmethod
    def _validate_rewrite_mode(cls, value: str) -> str:
        if value not in MODE_WHITELIST:
            raise ValueError(f"rewrite_mode 不在白名单内: {MODE_WHITELIST}")
        return value

    @field_validator("rewrite_level")
    @classmethod
    def _validate_rewrite_level(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        if value not in LEVEL_WHITELIST:
            raise ValueError(f"rewrite_level 不在白名单内: {LEVEL_WHITELIST}")
        return value

    @field_validator("custom_instruction")
    @classmethod
    def _validate_custom_instruction(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("custom_instruction 必须是字符串或 null")
        # 全空白等价于"未填"
        if not value.strip():
            return None
        if len(value) > MAX_CUSTOM_INSTRUCTION_CHARS:
            raise ValueError(
                f"custom_instruction 超过 {MAX_CUSTOM_INSTRUCTION_CHARS} 字上限"
            )
        return value


class RewriteResponse(BaseModel):
    """AI 润色响应体。"""

    success: bool
    result: str = ""


# ─────────────────────────────────────────────
# 简历抽取(extract-resume)— Resume Preview Builder MVP
# ─────────────────────────────────────────────

# Requirement 4.2 / 4.9:plain_text 上限 200000 字符
MAX_EXTRACT_PLAIN_TEXT_CHARS = 200_000
# Requirement 4.2:content_json 序列化后上限 1 MiB
MAX_EXTRACT_CONTENT_JSON_BYTES = 1024 * 1024
# Requirement 4.3:warnings 元素枚举集合
ALLOWED_EXTRACT_WARNING_CODES = {
    "empty_input",
    "json_parse_failed",
    "extraction_timeout",
    "fabrication_suspected",
    "non_resume_content_detected",
}


class FieldStatus(str, Enum):
    """Resume_JSON 中每个原子字段的状态枚举(Requirement 2.4 / 2.5)。"""

    confirmed = "confirmed"
    inferred_from_text = "inferred_from_text"
    missing = "missing"
    needs_confirmation = "needs_confirmation"


class ExtractResumeRequest(BaseModel):
    """
    Extract_Resume_API 请求体(Requirement 4.2 / 4.9)。

    校验:
      - document_id 长度 1..128
      - plain_text 长度 ≤ 200000
      - content_json 序列化后 ≤ 1 MiB
      - provider_id 长度 1..64 或 None
    """

    document_id: str = Field(..., min_length=1, max_length=128)
    plain_text: str = Field(..., max_length=MAX_EXTRACT_PLAIN_TEXT_CHARS)
    content_json: dict = Field(default_factory=dict)
    provider_id: Optional[str] = Field(default=None, max_length=64)

    @field_validator("content_json")
    @classmethod
    def _check_content_json_size(cls, value: dict) -> dict:
        if not isinstance(value, dict):
            raise ValueError("content_json 必须是对象")
        try:
            serialized = json.dumps(value, ensure_ascii=False)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"content_json 序列化失败: {exc}")
        if len(serialized.encode("utf-8")) > MAX_EXTRACT_CONTENT_JSON_BYTES:
            raise ValueError("content_json 序列化后超过 1 MiB 上限")
        return value

    @field_validator("provider_id")
    @classmethod
    def _check_provider_id(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("provider_id 必须是字符串或 null")
        # 全空白等价未填
        if not value.strip():
            return None
        return value


class ExtractResumeResponse(BaseModel):
    """
    Extract_Resume_API 响应体(Requirement 4.3)。

    - resume_json 永不为 null;失败时为安全骨架。
    - warnings 元素必须取自固定枚举集合。
    - debug_request_id:仅在 DEBUG_MODE=true 时返回非空,用于前端 console 与
      后端 debug/resume_extract/{rid}_* 取证文件关联。生产环境恒为 None。
    """

    success: bool
    resume_json: dict = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    missing_questions: list[str] = Field(default_factory=list)
    debug_request_id: Optional[str] = None

    @field_validator("warnings")
    @classmethod
    def _check_warnings(cls, value: list[str]) -> list[str]:
        if not isinstance(value, list):
            raise ValueError("warnings 必须是数组")
        for code in value:
            if code not in ALLOWED_EXTRACT_WARNING_CODES:
                raise ValueError(f"非法 warning code: {code}")
        return value
