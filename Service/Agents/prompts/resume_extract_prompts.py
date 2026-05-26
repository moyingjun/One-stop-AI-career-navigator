"""
Service/Agents/prompts/resume_extract_prompts.py — 简历抽取 Prompt 模板

满足 Requirement 5.1 / 5.6 / 2.1 / 2.6:
  - System Prompt 与代码解耦,严禁在 Router/Agent 中硬编码 Prompt。
  - 强约束 Fact_Safety_Lock:不得编造草稿之外的事实。
  - 强约束严格 JSON:不得输出 Markdown 围栏 / 解释段 / 多 JSON 片段。
  - 重试时附加 RETRY_REMINDER。
"""

from __future__ import annotations

from typing import Any

import json


# ─────────────────────────────────────────────
# Fact_Safety_Lock & JSON 输出约束
# ─────────────────────────────────────────────

SYSTEM_PROMPT = """你是简历结构化抽取器。把用户草稿抽成 Resume_JSON。

【硬约束】
- 只输出一个 JSON 对象。不输出 Markdown 代码块,不输出 <think> 思考过程,不输出任何解释或前后缀文字。
- 不编造草稿中没有的事实(姓名/公司/学校/岗位/时间/数字/技能/链接)。找不到就用 missing。
- 每个标量字段必须是 {"value": "...", "status": "..."},status ∈ {confirmed, inferred_from_text, missing, needs_confirmation}。
- 顶级 8 键必须齐全:basics / education / skills / projects / experience / awards / certificates / meta。
- 每个 section 形态:{"items": [...], "missingFields": []};即使 items 为空也要写 "missingFields": []。
- basics 必须是对象,固定含 6 字段(name / targetRole / email / phone / city / websiteOrRepo)+ "missingFields": []。
- meta.templateId ∈ {"ats_single_column", "tech_two_column"}。
- status=missing 时 value 置 "" / [] / null,不写"待补充""N/A"。
- 顶级追加 "_missing_questions"(string[]),每条 8-80 字简体中文,提及字段中文名(如"在校时间")。

【最小 schema】
{
  "basics": {"name":{"value":"","status":"missing"}, "targetRole":{"value":"","status":"missing"}, "email":{"value":"","status":"missing"}, "phone":{"value":"","status":"missing"}, "city":{"value":"","status":"missing"}, "websiteOrRepo":{"value":"","status":"missing"}, "missingFields":[]},
  "education":   {"items":[], "missingFields":[]},
  "skills":      {"items":[{"category":"...", "items":[{"name":"...","status":"confirmed"}]}], "missingFields":[]},
  "projects":    {"items":[], "missingFields":[]},
  "experience":  {"items":[], "missingFields":[]},
  "awards":      {"items":[], "missingFields":[]},
  "certificates":{"items":[], "missingFields":[]},
  "meta": {"confirmedByUser":false, "templateId":"ats_single_column", "generatedAt":"2024-01-01T12:00:00Z", "sourceDocumentId":"doc-id"},
  "_missing_questions": []
}
"""


USER_PROMPT_PREFIX = """把下面草稿抽成 Resume_JSON。只输出 JSON,不要 <think>,不要解释。

【plain_text】
"""

USER_PROMPT_MIDDLE = """

【content_json】
"""

USER_PROMPT_SUFFIX = """

只输出一个 JSON 对象。"""


RETRY_REMINDER = "\n\n【重试】上次输出无法解析,请只输出一个 JSON 对象,不要任何 Markdown / <think> / 解释。"


# ─────────────────────────────────────────────
# 公共 API
# ─────────────────────────────────────────────


def _safe_dump_content_json(content_json: Any) -> str:
    """把 content_json 序列化为字符串,失败时返回 '{}'."""
    try:
        return json.dumps(content_json or {}, ensure_ascii=False)
    except (TypeError, ValueError):
        return "{}"


def build_extract_messages(
    plain_text: str,
    content_json: Any,
    is_retry: bool = False,
) -> list[dict]:
    """
    构造 LLM 抽取调用的 messages。

    plain_text 长度由上游裁剪;此处不再做长度校验,以保持 Agent/Service 边界清晰。
    """
    plain_text = plain_text or ""
    serialized = _safe_dump_content_json(content_json)
    user_content = (
        USER_PROMPT_PREFIX
        + plain_text
        + USER_PROMPT_MIDDLE
        + serialized
        + USER_PROMPT_SUFFIX
    )
    if is_retry:
        user_content += RETRY_REMINDER

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]
