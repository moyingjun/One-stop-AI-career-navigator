"""
Service/Utils/resume_json_validator.py — Resume_JSON 校验与安全骨架工具层

仅纯函数，不依赖 FastAPI / Pydantic / httpx。

导出：
  - validate_resume_json_contract(obj)          → Optional[str]
  - parse_resume_json(raw_text)                 → Optional[dict]
  - normalize_resume_json(raw, document_id)     → dict（hotfix:LLM 近似 JSON 兼容层）
  - build_safe_skeleton(document_id)            → dict
  - enforce_missing_fields_invariant(resume)    → resume(就地修复)
  - detect_fabrication(resume, plain_text, ...) → list[str]
  - detect_non_resume_content(plain_text)       → bool
  - utc_now_iso8601()                           → str

满足需求：
  - Requirement 3.1 / 3.2 / 3.3 / 3.4 / 3.6 / 3.8（顶级 8 Section + Field_Status 枚举 + templateId 枚举 + 数组上限）
  - Requirement 2.1 / 2.5 / 2.7（Fact_Safety_Lock 反编造可定位）
  - Requirement 3.5（missingFields ↔ Field_Status 互蕴 + 幂等 + missing 字段值为空）
  - Requirement 3.7 / 4.5 / 4.6 / 4.8 / 11.2（安全骨架默认值）
  - Requirement 5.5（非简历内容启发式）
  - Requirement 5.6 / 4.6（parse_resume_json 鲁棒性：剥离围栏、拒收多 JSON / 解释段）

Hotfix（normalize_resume_json）：
  - 实际 LLM 经常返回近似 Resume_JSON,缺 missingFields / 把 basics 字段写成裸字符串 /
    把 skills 写成纯字符串数组等。normalize 先尽力把这些"近亲"形态修成标准结构,
    再交给 enforce_missing_fields_invariant + validate_resume_json_contract 校验。
  - normalize **不是**反编造防线;反编造仍由 detect_fabrication 在 Service 层执行。
"""

from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime, timezone
from typing import Any, Optional

# ─────────────────────────────────────────────
# 常量：契约定义
# ─────────────────────────────────────────────

ALLOWED_FIELD_STATUS = {
    "confirmed",
    "inferred_from_text",
    "missing",
    "needs_confirmation",
}

ALLOWED_TEMPLATE_IDS = {"ats_single_column", "tech_two_column"}

TOP_LEVEL_SECTIONS = (
    "basics",
    "education",
    "skills",
    "projects",
    "experience",
    "awards",
    "certificates",
    "meta",
)

# 数组型 Section 上限（Requirement 3.3 / 3.4）
ARRAY_SECTION_MAX = 50
SKILLS_GROUP_MAX = 10
SKILLS_ITEM_MAX = 30

# basics 固定字段（Requirement 3.2）
BASICS_FIELDS = ("name", "targetRole", "email", "phone", "city", "websiteOrRepo")

# 各数组 Section 内部条目允许的字段（与 design.md D3 对齐）
ITEM_FIELDS = {
    "education": ("school", "degree", "major", "startDate", "endDate", "gpa", "highlights"),
    "projects": ("name", "role", "stack", "startDate", "endDate", "summary", "highlights", "link"),
    "experience": ("company", "title", "startDate", "endDate", "location", "summary", "highlights"),
    "awards": ("name", "issuer", "date", "summary"),
    "certificates": ("name", "issuer", "issueDate", "expireDate", "credentialId"),
}


# ─────────────────────────────────────────────
# 时间工具
# ─────────────────────────────────────────────


def utc_now_iso8601() -> str:
    """返回当前 UTC 时间的 ISO 8601 字符串（秒精度）。"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ─────────────────────────────────────────────
# 安全骨架（Requirement 4.5 / 4.6 / 4.8 / 11.2）
# ─────────────────────────────────────────────


def _empty_field_cell() -> dict:
    """生成一个 status=missing 的空字段单元。"""
    return {"value": "", "status": "missing"}


def build_safe_skeleton(document_id: str, template_id: str = "ats_single_column") -> dict:
    """
    生成一份所有 Section 全 missing 的安全骨架 Resume_JSON。

    满足:
      - 顶级 8 Section 严格存在
      - basics 6 字段全 missing 且 value 为空
      - 数组 Section items=[] 且 missingFields=[]
      - meta.confirmedByUser=false / templateId 默认 ats_single_column / generatedAt=ISO 8601 / sourceDocumentId
    """
    if template_id not in ALLOWED_TEMPLATE_IDS:
        template_id = "ats_single_column"

    basics = {field: _empty_field_cell() for field in BASICS_FIELDS}
    basics["missingFields"] = list(BASICS_FIELDS)

    return {
        "basics": basics,
        "education": {"items": [], "missingFields": []},
        "skills": {"items": [], "missingFields": []},
        "projects": {"items": [], "missingFields": []},
        "experience": {"items": [], "missingFields": []},
        "awards": {"items": [], "missingFields": []},
        "certificates": {"items": [], "missingFields": []},
        "meta": {
            "confirmedByUser": False,
            "templateId": template_id,
            "generatedAt": utc_now_iso8601(),
            "sourceDocumentId": document_id or "",
        },
    }


# ─────────────────────────────────────────────
# 契约校验（Requirement 3.1 / 3.2 / 3.3 / 3.4 / 3.6 / 3.8）
# ─────────────────────────────────────────────


def _is_field_cell(cell: Any) -> bool:
    """字段单元结构：{value: any, status: FieldStatus}。"""
    if not isinstance(cell, dict):
        return False
    if "status" not in cell or "value" not in cell:
        return False
    return cell["status"] in ALLOWED_FIELD_STATUS


def _validate_basics(basics: Any) -> Optional[str]:
    if not isinstance(basics, dict):
        return "basics 必须是对象"
    for field in BASICS_FIELDS:
        if field not in basics:
            return f"basics.{field} 缺失"
        if not _is_field_cell(basics[field]):
            return f"basics.{field} 不是合法 Field 单元"
    if "missingFields" not in basics or not isinstance(basics["missingFields"], list):
        return "basics.missingFields 必须是数组"
    return None


def _validate_array_section(name: str, section: Any) -> Optional[str]:
    if not isinstance(section, dict):
        return f"{name} 必须是 {{items, missingFields}} 对象"
    items = section.get("items")
    if not isinstance(items, list):
        return f"{name}.items 必须是数组"
    if len(items) > ARRAY_SECTION_MAX:
        return f"{name}.items 长度超过上限 {ARRAY_SECTION_MAX}"
    mf = section.get("missingFields")
    if not isinstance(mf, list):
        return f"{name}.missingFields 必须是数组"
    return None


def _validate_skills(skills: Any) -> Optional[str]:
    if not isinstance(skills, dict):
        return "skills 必须是 {items, missingFields} 对象"
    items = skills.get("items")
    if not isinstance(items, list):
        return "skills.items 必须是数组"
    if len(items) > SKILLS_GROUP_MAX:
        return f"skills.items 长度超过上限 {SKILLS_GROUP_MAX}"
    for idx, group in enumerate(items):
        if not isinstance(group, dict):
            return f"skills.items[{idx}] 必须是对象"
        sub = group.get("items")
        if not isinstance(sub, list):
            return f"skills.items[{idx}].items 必须是数组"
        if len(sub) > SKILLS_ITEM_MAX:
            return f"skills.items[{idx}].items 长度超过上限 {SKILLS_ITEM_MAX}"
    return None


def _validate_meta(meta: Any) -> Optional[str]:
    if not isinstance(meta, dict):
        return "meta 必须是对象"
    if not isinstance(meta.get("confirmedByUser"), bool):
        return "meta.confirmedByUser 必须是布尔"
    template_id = meta.get("templateId")
    if template_id not in ALLOWED_TEMPLATE_IDS:
        return "meta.templateId 不在合法枚举内"
    if not isinstance(meta.get("generatedAt"), str):
        return "meta.generatedAt 必须是字符串"
    if not isinstance(meta.get("sourceDocumentId"), str):
        return "meta.sourceDocumentId 必须是字符串"
    return None


def validate_resume_json_contract(obj: Any) -> Optional[str]:
    """
    校验 Resume_JSON 契约。

    返回 None 表示合法；返回非空字符串表示首个发现的违例描述。
    """
    if not isinstance(obj, dict):
        return "Resume_JSON 顶级必须是对象"

    # 顶级键集合严格相等（Requirement 3.1）
    extra = set(obj.keys()) - set(TOP_LEVEL_SECTIONS)
    if extra:
        return f"Resume_JSON 含非法顶级键: {sorted(extra)}"
    missing_top = set(TOP_LEVEL_SECTIONS) - set(obj.keys())
    if missing_top:
        return f"Resume_JSON 缺失顶级 Section: {sorted(missing_top)}"

    err = _validate_basics(obj["basics"])
    if err:
        return err

    for name in ("education", "projects", "experience", "awards", "certificates"):
        err = _validate_array_section(name, obj[name])
        if err:
            return err

    err = _validate_skills(obj["skills"])
    if err:
        return err

    err = _validate_meta(obj["meta"])
    if err:
        return err

    return None


# ─────────────────────────────────────────────
# parse_resume_json（Requirement 5.6 / 4.6 / 2.8）
# ─────────────────────────────────────────────

# 容忍的 Markdown 围栏：```json ... ``` 或 ``` ... ```（中间可以有任意行)
_FENCE_INNER_RE = re.compile(
    r"```\s*(?:json|JSON|JSON5|json5)?\s*[\r\n]+(?P<body>.*?)[\r\n]+```",
    re.DOTALL,
)
# <think>...</think> 思维链(开源 LLM 常见,如 DeepSeek R1)
_THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
# 反引号围栏夹带前后说明文字时的整体匹配(只取第一段围栏内容)
_FENCED_BLOCK_FIRST_RE = re.compile(
    r"```\s*(?:json|JSON|JSON5|json5)?\s*[\r\n]+(?P<body>.*?)[\r\n]+```",
    re.DOTALL,
)
# 容忍的尾部多余逗号:`,}` / `, }` / `,]` / `, ]`
_TRAILING_COMMA_RE = re.compile(r",(\s*[}\]])")
# UTF-8 BOM
_BOM = "\ufeff"


def _strip_safe_prefixes(text: str) -> str:
    """去掉 BOM、剥离 <think>...</think> 思维链、紧前后空白。"""
    if not isinstance(text, str):
        return ""
    s = text.lstrip(_BOM).strip()
    if not s:
        return ""
    if "<think>" in s.lower():
        s = _THINK_BLOCK_RE.sub("", s).strip()
    return s


def _strip_trailing_commas(text: str) -> str:
    """安全清洗:把 `,}` / `,]` 改成 `}` / `]`。

    这是一个对 LLM 常见小毛病(尾部逗号)的最小修复。仍然走标准 JSON 解析,
    不引入 JSON5 / yaml 等宽容模式。
    """
    return _TRAILING_COMMA_RE.sub(r"\1", text)


def _balanced_json_object(text: str, start: int) -> Optional[str]:
    """
    从 text[start] 处的 '{' 开始,按括号配对截取一个完整 JSON 对象子串。

    支持字符串内的 \" 转义和 { } 字面量。返回截取出的子串(含外层花括号),
    若无法配对(被截断 / 不完整)则返回 None。
    """
    if start >= len(text) or text[start] != "{":
        return None
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


# ─────────────────────────────────────────────
# parse_resume_json:Hotfix 6 强化版
#
# 现在采用"raw_decode 优先 + 括号配对兜底"的双层策略:
#   1. raw_decode 能稳定吃掉"JSON + 尾部说明文字"形态,JSON 完整时一次成功
#   2. 括号配对兜底处理 raw_decode 仍失败的边角情况(尾部逗号 / 注释嫌疑)
#   3. 失败时通过 parse_resume_json_with_diag 返回详细诊断信息(JSONDecodeError
#      msg/lineno/colno/pos、`unbalanced_json_object`、`raw_tail`),让 Service
#      层日志能告诉用户到底哪里不对
# ─────────────────────────────────────────────


def _attempt_decode_with_decoder(text: str) -> tuple[Optional[dict], Optional[json.JSONDecodeError]]:
    """对一段 text 尝试 raw_decode + json.loads + 尾逗号修复 + json.loads 三种宽容度递增的解析。

    返回 (obj 或 None, last_decode_error)。obj 非 None 时一定是 dict。
    """
    last_err: Optional[json.JSONDecodeError] = None

    # 1) raw_decode:容忍"JSON 后面有尾部说明文字"
    try:
        obj, _idx = json.JSONDecoder().raw_decode(text)
        if isinstance(obj, dict):
            return obj, None
    except (json.JSONDecodeError, ValueError) as exc:
        if isinstance(exc, json.JSONDecodeError):
            last_err = exc

    # 2) 严格 json.loads:整段必须是合法 JSON
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj, None
    except (json.JSONDecodeError, ValueError) as exc:
        if isinstance(exc, json.JSONDecodeError):
            last_err = exc

    # 3) 修复尾部多余逗号后再试一次 raw_decode
    fixed = _strip_trailing_commas(text)
    if fixed != text:
        try:
            obj, _idx = json.JSONDecoder().raw_decode(fixed)
            if isinstance(obj, dict):
                return obj, None
        except (json.JSONDecodeError, ValueError) as exc:
            if isinstance(exc, json.JSONDecodeError):
                last_err = exc

    return None, last_err


def parse_resume_json_with_diag(raw: Any) -> tuple[Optional[dict], dict]:
    """
    解析 LLM 输出为 dict,并返回失败诊断。

    成功时返回 (dict, {"reason": "ok"})。
    失败时返回 (None, {"reason": "...", "msg": "...", "lineno": N, "colno": N, "pos": N,
                          "raw_len": N, "raw_tail": "<最后 800 字>"})。

    诊断 reason 取值:
      - ok                             — 解析成功
      - non_string                     — 输入非字符串
      - empty                          — 全空白
      - no_open_brace                  — 找不到 '{'
      - json_decode_error              — JSON 解析失败,见 msg/lineno/colno/pos
      - unbalanced_json_object         — 找到 '{' 但配对失败,JSON 未闭合(疑似 max_tokens 截断)
      - non_dict_top_level             — 解析成功但顶级不是 object(罕见)
    """

    if not isinstance(raw, str):
        return None, {"reason": "non_string", "raw_len": 0}

    raw_len = len(raw)
    cleaned = _strip_safe_prefixes(raw)
    if not cleaned:
        return None, {"reason": "empty", "raw_len": raw_len}

    # 1) 优先剥围栏:```json ... ```
    fence_match = _FENCED_BLOCK_FIRST_RE.search(cleaned)
    fence_body: Optional[str] = None
    if fence_match:
        fb = fence_match.group("body").strip()
        if fb:
            fence_body = fb

    # 候选解析顺序:围栏 body → 整段
    candidates: list[str] = []
    if fence_body:
        candidates.append(fence_body)
    candidates.append(cleaned)

    last_err: Optional[json.JSONDecodeError] = None
    for body in candidates:
        # 1a) 直接 raw_decode
        obj, err = _attempt_decode_with_decoder(body)
        if obj is not None:
            return obj, {"reason": "ok"}
        if err is not None:
            last_err = err

        # 1b) 找第一个 '{',括号配对截取出完整 JSON 对象,再解析
        first_brace = body.find("{")
        if first_brace < 0:
            continue
        candidate = _balanced_json_object(body, first_brace)
        if candidate is None:
            # 找到 '{' 但无法闭合 — 极可能是被 max_tokens 截断
            tail = body[-800:] if len(body) > 800 else body
            return None, {
                "reason": "unbalanced_json_object",
                "raw_len": raw_len,
                "first_brace_pos": first_brace,
                "raw_tail": tail.replace("\n", "\\n").replace("\r", ""),
            }
        obj, err = _attempt_decode_with_decoder(candidate)
        if obj is not None:
            return obj, {"reason": "ok"}
        if err is not None:
            last_err = err

    # 全部失败 — 收集诊断
    tail_src = cleaned[-800:] if len(cleaned) > 800 else cleaned
    diag: dict = {
        "reason": "json_decode_error",
        "raw_len": raw_len,
        "raw_tail": tail_src.replace("\n", "\\n").replace("\r", ""),
    }
    if last_err is not None:
        diag["msg"] = last_err.msg
        diag["lineno"] = last_err.lineno
        diag["colno"] = last_err.colno
        diag["pos"] = last_err.pos
    if cleaned.find("{") < 0:
        diag["reason"] = "no_open_brace"
    return None, diag


def parse_resume_json(raw: Any) -> Optional[dict]:
    """
    解析 LLM 返回的字符串为 dict。容忍真实场景里的多种"近似 JSON"形态:

    1. 纯 JSON                                          → 直接解析
    2. ```json ... ``` / ``` ... ``` Markdown 围栏       → 剥离围栏后解析
    3. <think>思维链</think> + JSON                    → 剥离 think 块后解析
    4. "以下是抽取结果:\n{...}\n请确认。"               → 截取首个完整 JSON 对象
    5. "{...}\n说明:此抽取..."                         → raw_decode 自动忽略尾部
    6. 两段或多段 JSON 片段                             → 取第一段合法且 dict 类型的
    7. 末尾多余逗号 ,} / ,]                             → 安全修复后再解析

    返回:
      - 合法 dict
      - 解析失败 / 无任何 JSON 对象 / 解析结果非 dict → None

    诊断版本见 `parse_resume_json_with_diag`,提供失败 reason / msg / pos / raw_tail。
    """
    obj, _diag = parse_resume_json_with_diag(raw)
    return obj


# ─────────────────────────────────────────────
# missingFields ↔ Field_Status 强一致化（Requirement 3.5 / 6.5 / 6.6）
# ─────────────────────────────────────────────


def _is_empty_value(value: Any) -> bool:
    """判定字段值是否"空"。"""
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    if isinstance(value, (list, tuple, dict)):
        return len(value) == 0
    return False


def _status_implies_missing(status: str) -> bool:
    return status in ("missing", "needs_confirmation", "inferred_from_text")


def _coerce_basics(basics: dict) -> None:
    """basics 内部强一致化（就地）。"""
    missing_keys = []
    for field in BASICS_FIELDS:
        cell = basics.get(field)
        if not _is_field_cell(cell):
            cell = _empty_field_cell()
            basics[field] = cell
        # missing 状态强制 value 为空
        if cell["status"] == "missing":
            cell["value"] = "" if not isinstance(cell["value"], list) else []
        if _status_implies_missing(cell["status"]):
            missing_keys.append(field)
    basics["missingFields"] = sorted(set(missing_keys))


def _coerce_array_section_item(name: str, item: dict, idx: int, missing_keys: list) -> None:
    """对单条数组 Section 条目内部字段做强一致化。"""
    allowed = ITEM_FIELDS.get(name, ())
    for field in allowed:
        cell = item.get(field)
        if not _is_field_cell(cell):
            # highlights / stack 默认是数组型；其余按字符串
            if field in ("highlights", "stack"):
                item[field] = {"value": [], "status": "missing"}
            else:
                item[field] = _empty_field_cell()
            cell = item[field]
        if cell["status"] == "missing":
            if isinstance(cell["value"], list):
                cell["value"] = []
            else:
                cell["value"] = ""
        if _status_implies_missing(cell["status"]):
            missing_keys.append(f"items[{idx}].{field}")


def _coerce_array_section(name: str, section: dict) -> None:
    """education / projects / experience / awards / certificates 强一致化。"""
    items = section.get("items")
    if not isinstance(items, list):
        section["items"] = []
        section["missingFields"] = []
        return
    # 截断到上限
    if len(items) > ARRAY_SECTION_MAX:
        section["items"] = items[:ARRAY_SECTION_MAX]
        items = section["items"]
    missing_keys: list = []
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            items[idx] = {}
            item = items[idx]
        _coerce_array_section_item(name, item, idx, missing_keys)
    section["missingFields"] = sorted(set(missing_keys))


def _coerce_skills(skills: dict) -> None:
    """skills 分组强一致化。"""
    items = skills.get("items")
    if not isinstance(items, list):
        skills["items"] = []
        skills["missingFields"] = []
        return
    if len(items) > SKILLS_GROUP_MAX:
        skills["items"] = items[:SKILLS_GROUP_MAX]
        items = skills["items"]
    missing_keys: list = []
    for gidx, group in enumerate(items):
        if not isinstance(group, dict):
            items[gidx] = {"category": "", "items": []}
            group = items[gidx]
        if not isinstance(group.get("category"), str):
            group["category"] = ""
        sub = group.get("items")
        if not isinstance(sub, list):
            group["items"] = []
            sub = group["items"]
        if len(sub) > SKILLS_ITEM_MAX:
            group["items"] = sub[:SKILLS_ITEM_MAX]
            sub = group["items"]
        for sidx, skill in enumerate(sub):
            if not isinstance(skill, dict):
                sub[sidx] = {"name": "", "status": "missing"}
                skill = sub[sidx]
            if "name" not in skill or not isinstance(skill["name"], str):
                skill["name"] = ""
            status = skill.get("status")
            if status not in ALLOWED_FIELD_STATUS:
                skill["status"] = "missing"
                status = "missing"
            if status == "missing":
                skill["name"] = ""
            if _status_implies_missing(status):
                missing_keys.append(f"items[{gidx}].items[{sidx}].name")
    skills["missingFields"] = sorted(set(missing_keys))


def enforce_missing_fields_invariant(resume_json: dict) -> dict:
    """
    使每个 Section 的 missingFields 与 Field_Status 强一致；幂等。

    返回 *同一个对象*（就地修复），避免不必要的深拷贝。
    """
    if not isinstance(resume_json, dict):
        return resume_json

    if isinstance(resume_json.get("basics"), dict):
        _coerce_basics(resume_json["basics"])

    for name in ("education", "projects", "experience", "awards", "certificates"):
        if isinstance(resume_json.get(name), dict):
            _coerce_array_section(name, resume_json[name])

    if isinstance(resume_json.get("skills"), dict):
        _coerce_skills(resume_json["skills"])

    return resume_json


# ─────────────────────────────────────────────
# normalize_resume_json — Hotfix:LLM 近似 JSON 兼容层
# ─────────────────────────────────────────────


def _value_is_meaningful(value: Any) -> bool:
    """字段值在归一化语境下是否"有意义"。"""
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() != ""
    if isinstance(value, (list, tuple, set)):
        return len(value) > 0
    if isinstance(value, dict):
        return len(value) > 0
    return True  # 数字 / 布尔等都视为有意义


def _normalize_status_token(token: Any, value: Any) -> str:
    """
    把 LLM 返回的 status 值归一化到合法枚举。
    超出枚举时:有值 → inferred_from_text,空值 → missing。
    """
    if isinstance(token, str):
        t = token.strip().lower()
        if t in ALLOWED_FIELD_STATUS:
            return t
        # 常见别名
        if t in ("ok", "filled", "true", "yes"):
            return "confirmed"
        if t in ("none", "null", "empty", "n/a", "na", "false", "no"):
            return "missing"
        if t in ("inferred", "guess", "guessed", "infer"):
            return "inferred_from_text"
        if t in ("uncertain", "doubt", "ambiguous", "needs-confirmation", "needs_review"):
            return "needs_confirmation"
    # 不在枚举内或非字符串 → 看 value
    return "confirmed" if _value_is_meaningful(value) else "missing"


def _normalize_scalar_cell(raw: Any, *, array_field: bool = False) -> dict:
    """
    把 LLM 返回的"近似字段"归一化为 {value, status}。

    支持的输入形态:
      - None / 缺失              → {value: '', status: missing}
      - "张三"                   → {value: '张三', status: confirmed}
      - 13800000000              → {value: '13800000000', status: confirmed}
      - {value: '张三'}          → 补 status:confirmed
      - {value: '张三', status: 'confirmed'} → 透传
      - {text: '张三'} / {name: '张三'} / {content: '张三'} → 提取后归一
      - 数组型字段(highlights / stack)还能接收 ["a", "b"] 这样的裸数组

    输出始终是合法 FieldCell。
    """
    if raw is None:
        return {"value": ([] if array_field else ""), "status": "missing"}

    # 已是合法字段单元 → 仅做 status 归一化
    if isinstance(raw, dict) and "value" in raw:
        value = raw.get("value")
        status_raw = raw.get("status")
        if array_field:
            if isinstance(value, str):
                # 字符串 → 按换行/逗号拆分
                value = [s.strip() for s in re.split(r"[\n,，;；]", value) if s.strip()]
            elif not isinstance(value, list):
                value = []
            else:
                value = [str(v).strip() for v in value if isinstance(v, (str, int, float)) and str(v).strip()]
        else:
            if isinstance(value, list):
                value = ", ".join(str(v) for v in value if v is not None)
            elif value is None:
                value = ""
            elif not isinstance(value, str):
                value = str(value)
        status = _normalize_status_token(status_raw, value)
        if status == "missing":
            value = [] if array_field else ""
        return {"value": value, "status": status}

    # LLM 直接返回字符串/数字 → 包成 cell
    if isinstance(raw, (str, int, float)):
        if array_field:
            text = str(raw).strip()
            if not text:
                return {"value": [], "status": "missing"}
            value_list = [s.strip() for s in re.split(r"[\n,，;；]", text) if s.strip()]
            return {"value": value_list, "status": "confirmed" if value_list else "missing"}
        text = str(raw).strip()
        if not text:
            return {"value": "", "status": "missing"}
        return {"value": text, "status": "confirmed"}

    # 数组形式(用于 highlights / stack)
    if isinstance(raw, list):
        if array_field:
            value_list = [str(v).strip() for v in raw if isinstance(v, (str, int, float)) and str(v).strip()]
            return {"value": value_list, "status": "confirmed" if value_list else "missing"}
        # 标量字段被传成数组 → 拼接后视为字符串
        joined = ", ".join(str(v) for v in raw if v is not None and str(v).strip())
        if not joined:
            return {"value": "", "status": "missing"}
        return {"value": joined, "status": "confirmed"}

    # 字典但缺 value → 尝试从常见别名提取
    if isinstance(raw, dict):
        for alias in ("text", "name", "content", "val"):
            if alias in raw:
                return _normalize_scalar_cell(raw[alias], array_field=array_field)

    # 兜底
    return {"value": ([] if array_field else ""), "status": "missing"}


def _normalize_basics(raw: Any) -> dict:
    """
    把 LLM 的 basics(可能是各种近似形态)归一化到标准结构。

    支持:
      - basics 缺失 / None / 非 dict → 全 missing 骨架
      - basics 字段是字符串
      - basics 字段是 {value} 缺 status
      - basics 字段是 {value, status}
      - 用户写成 {phone_number: ...} / {mail: ...} 等别名
    """
    if not isinstance(raw, dict):
        raw = {}

    # 字段别名映射:容忍 LLM 把 email 写成 mail / e_mail
    aliases = {
        "name": ("name", "fullName", "fullname", "full_name"),
        "targetRole": ("targetRole", "target_role", "title", "position", "role"),
        "email": ("email", "mail", "e_mail", "emailAddress", "email_address"),
        "phone": ("phone", "phoneNumber", "phone_number", "mobile", "tel"),
        "city": ("city", "location", "address"),
        "websiteOrRepo": (
            "websiteOrRepo",
            "website_or_repo",
            "website",
            "homepage",
            "github",
            "githubUrl",
            "url",
            "link",
        ),
    }

    out = {}
    for canonical, alias_list in aliases.items():
        picked = None
        for alias in alias_list:
            if alias in raw and raw[alias] not in (None, "", []):
                picked = raw[alias]
                break
        out[canonical] = _normalize_scalar_cell(picked)

    out["missingFields"] = []
    return out


def _normalize_array_item(name: str, raw: Any) -> dict:
    """归一化 education/projects/experience/awards/certificates 的单条条目。"""
    fields = ITEM_FIELDS.get(name, ())
    if not isinstance(raw, dict):
        # 容忍纯字符串("某公司 某岗位")— 全部塞到首字段
        if isinstance(raw, str) and raw.strip() and fields:
            first_field = fields[0]
            cell = _normalize_scalar_cell(raw)
            item = {f: _normalize_scalar_cell(None, array_field=(f in ("highlights", "stack"))) for f in fields}
            item[first_field] = cell
            return item
        return {f: _normalize_scalar_cell(None, array_field=(f in ("highlights", "stack"))) for f in fields}

    # 字段别名容忍
    item_aliases = {
        "school": ("school", "institution", "university", "college"),
        "degree": ("degree", "level"),
        "major": ("major", "field", "fieldOfStudy", "field_of_study"),
        "startDate": ("startDate", "start_date", "start", "from", "begin"),
        "endDate": ("endDate", "end_date", "end", "to", "until"),
        "gpa": ("gpa", "GPA", "score"),
        "highlights": ("highlights", "courses", "achievements", "details", "bullets"),
        "name": ("name", "title", "projectName", "project_name", "awardName", "certName"),
        "role": ("role", "position", "responsibility"),
        "stack": ("stack", "techStack", "tech_stack", "technologies", "tech"),
        "summary": ("summary", "description", "desc", "intro"),
        "link": ("link", "url", "homepage"),
        "company": ("company", "employer", "organization"),
        "title": ("title", "position", "jobTitle", "job_title"),
        "location": ("location", "city", "address"),
        "issuer": ("issuer", "publisher", "from", "by"),
        "date": ("date", "year", "awardedDate", "awarded_at"),
        "issueDate": ("issueDate", "issue_date", "issuedAt"),
        "expireDate": ("expireDate", "expire_date", "expiry", "expiresAt"),
        "credentialId": ("credentialId", "credential_id", "id", "code", "number"),
    }

    out = {}
    for f in fields:
        is_array = f in ("highlights", "stack")
        picked = None
        for alias in item_aliases.get(f, (f,)):
            if alias in raw and raw[alias] not in (None,):
                picked = raw[alias]
                break
        out[f] = _normalize_scalar_cell(picked, array_field=is_array)
    return out


def _normalize_array_section(name: str, raw: Any) -> dict:
    """
    归一化 education / projects / experience / awards / certificates。

    支持:
      - 缺失 / None / 非 dict 非 list → {items: [], missingFields: []}
      - 直接是数组([...])           → 包裹成 {items: [...], missingFields: []}
      - {items: [...]} 缺 missingFields → 自动补 missingFields: []
      - items 中条目可能是裸字符串 / 缺字段
    """
    if isinstance(raw, list):
        items_raw = raw
    elif isinstance(raw, dict):
        items_raw = raw.get("items")
        if not isinstance(items_raw, list):
            # 也容忍 {data: [...]} / {list: [...]}
            for alias in ("data", "list", "entries"):
                if isinstance(raw.get(alias), list):
                    items_raw = raw[alias]
                    break
            else:
                items_raw = []
    else:
        items_raw = []

    items = []
    for item in items_raw[:ARRAY_SECTION_MAX]:
        items.append(_normalize_array_item(name, item))

    return {"items": items, "missingFields": []}


def _normalize_skills(raw: Any) -> dict:
    """
    归一化 skills。

    支持:
      - None / 缺失                              → {items: [], missingFields: []}
      - ["Java", "Spring Boot"]                  → 单一分组 "技能"
      - {items: [{category, items: [...]}]}      → 透传 + 归一化
      - {items: ["Java", "Spring Boot"]}         → 自动包成单一分组
      - {Java: 'high', Python: 'mid'}            → 单一分组(每个 key 当 skill 名)
      - {后端: ["Java","Spring"], 数据库: [...]} → 多分组
    """
    if raw is None or raw == "":
        return {"items": [], "missingFields": []}

    # 形式 1:纯字符串数组
    if isinstance(raw, list):
        if not raw:
            return {"items": [], "missingFields": []}
        # 元素都是字符串 → 单一分组
        if all(isinstance(s, (str, int, float)) for s in raw):
            sub_items = []
            for s in raw[:SKILLS_ITEM_MAX]:
                text = str(s).strip()
                if not text:
                    continue
                sub_items.append({"name": text, "status": "confirmed"})
            return {
                "items": [{"category": "技能", "items": sub_items}] if sub_items else [],
                "missingFields": [],
            }
        # 元素是分组对象
        groups = []
        for g in raw[:SKILLS_GROUP_MAX]:
            normalized = _normalize_skills_group(g)
            if normalized is not None:
                groups.append(normalized)
        return {"items": groups, "missingFields": []}

    if isinstance(raw, dict):
        # 形式 2:标准 {items: [...]} 或 {items: ["a","b"]}
        items_raw = raw.get("items")
        if isinstance(items_raw, list):
            # items 全部是字符串 → 包成单一分组
            if items_raw and all(isinstance(s, (str, int, float)) for s in items_raw):
                sub_items = []
                for s in items_raw[:SKILLS_ITEM_MAX]:
                    text = str(s).strip()
                    if not text:
                        continue
                    sub_items.append({"name": text, "status": "confirmed"})
                return {
                    "items": [{"category": "技能", "items": sub_items}] if sub_items else [],
                    "missingFields": [],
                }
            # 否则每条按分组归一
            groups = []
            for g in items_raw[:SKILLS_GROUP_MAX]:
                normalized = _normalize_skills_group(g)
                if normalized is not None:
                    groups.append(normalized)
            return {"items": groups, "missingFields": []}

        # 形式 3:{后端: ["Java",...], 数据库: [...]}
        groups = []
        for category, value in list(raw.items())[:SKILLS_GROUP_MAX]:
            if category in ("missingFields", "items"):
                continue
            if not isinstance(category, str):
                continue
            sub_items = []
            if isinstance(value, list):
                for v in value[:SKILLS_ITEM_MAX]:
                    text = str(v).strip() if not isinstance(v, dict) else str(v.get("name", "")).strip()
                    if text:
                        sub_items.append({"name": text, "status": "confirmed"})
            elif isinstance(value, str):
                text = value.strip()
                if text:
                    sub_items.append({"name": text, "status": "confirmed"})
            if sub_items:
                groups.append({"category": category, "items": sub_items})
        return {"items": groups, "missingFields": []}

    # 形式 4:纯字符串
    if isinstance(raw, str) and raw.strip():
        items = [s.strip() for s in re.split(r"[\n,，;；、]", raw) if s.strip()]
        return {
            "items": [
                {
                    "category": "技能",
                    "items": [{"name": s, "status": "confirmed"} for s in items[:SKILLS_ITEM_MAX]],
                }
            ]
            if items
            else [],
            "missingFields": [],
        }

    return {"items": [], "missingFields": []}


def _normalize_skills_group(raw: Any) -> Optional[dict]:
    """归一化单个 skill 分组。返回 None 表示该分组应被丢弃。"""
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return None
        return {"category": "技能", "items": [{"name": text, "status": "confirmed"}]}

    if not isinstance(raw, dict):
        return None

    category = raw.get("category")
    if not isinstance(category, str):
        # 容忍 "name" 当作 category
        category = raw.get("name") if isinstance(raw.get("name"), str) else "技能"
    category = category.strip() or "技能"

    sub_raw = raw.get("items")
    sub_items = []
    if isinstance(sub_raw, list):
        for s in sub_raw[:SKILLS_ITEM_MAX]:
            if isinstance(s, str):
                text = s.strip()
                if text:
                    sub_items.append({"name": text, "status": "confirmed"})
            elif isinstance(s, dict):
                name = s.get("name") if isinstance(s.get("name"), str) else None
                if name and name.strip():
                    status = _normalize_status_token(s.get("status"), name)
                    sub_items.append({"name": name.strip(), "status": status})
    return {"category": category, "items": sub_items}


def _normalize_meta(raw: Any, document_id: str) -> dict:
    """归一化 meta;字段缺失/越界时补默认值。"""
    if not isinstance(raw, dict):
        raw = {}

    template_id = raw.get("templateId")
    if not isinstance(template_id, str) or template_id not in ALLOWED_TEMPLATE_IDS:
        template_id = "ats_single_column"

    confirmed = raw.get("confirmedByUser")
    if not isinstance(confirmed, bool):
        confirmed = False

    generated_at = raw.get("generatedAt")
    if not isinstance(generated_at, str) or not generated_at.strip():
        generated_at = utc_now_iso8601()

    source_id = raw.get("sourceDocumentId")
    if not isinstance(source_id, str) or not source_id.strip():
        source_id = document_id or ""

    return {
        "confirmedByUser": confirmed,
        "templateId": template_id,
        "generatedAt": generated_at,
        "sourceDocumentId": source_id,
    }


def normalize_resume_json(raw: Any, document_id: str) -> dict:
    """
    把 LLM 返回的"近似 Resume_JSON"修整成标准 Resume_JSON。

    保证(无论输入多畸形):
      - 顶级 8 Section 都存在
      - basics 的 6 个字段都是合法 FieldCell
      - 数组型 Section 形态为 {items: [...], missingFields: [...]}
      - skills 形态为 {items: [{category, items: [{name, status}]}], missingFields}
      - meta 含 confirmedByUser / templateId / generatedAt / sourceDocumentId
      - 全部 status 取值都在合法枚举
      - 所有 missingFields 字段先置 [](由调用方再走 enforce_missing_fields_invariant 重算)

    本函数不做反编造比对(归 detect_fabrication);也不抛异常 — 任何 LLM 形态都能被吃下来。
    """
    if not isinstance(raw, dict):
        return build_safe_skeleton(document_id)

    out: dict = {}
    out["basics"] = _normalize_basics(raw.get("basics"))
    out["education"] = _normalize_array_section("education", raw.get("education"))
    out["projects"] = _normalize_array_section("projects", raw.get("projects"))
    out["experience"] = _normalize_array_section(
        "experience", raw.get("experience") if "experience" in raw else raw.get("work")
    )
    out["awards"] = _normalize_array_section("awards", raw.get("awards"))
    out["certificates"] = _normalize_array_section(
        "certificates", raw.get("certificates") if "certificates" in raw else raw.get("certs")
    )
    out["skills"] = _normalize_skills(raw.get("skills"))
    out["meta"] = _normalize_meta(raw.get("meta"), document_id)
    return out


# ─────────────────────────────────────────────
# 反编造比对（Requirement 2.1 / 2.7 / 5.2）
# ─────────────────────────────────────────────

_PUNCT_RE = re.compile(r"[\W_]+", flags=re.UNICODE)
_WS_RUN_RE = re.compile(r"\s+", flags=re.UNICODE)


def _normalize_for_match(text: str) -> str:
    """NFKC + casefold + 压平空白 + 剔除标点。"""
    if not isinstance(text, str):
        return ""
    norm = unicodedata.normalize("NFKC", text).casefold()
    norm = _WS_RUN_RE.sub("", norm)
    norm = _PUNCT_RE.sub("", norm)
    return norm


def _flatten_text_from_content_json(content_json: Any) -> str:
    """从 Tiptap content_json 中递归提取纯文本拼串。"""
    chunks: list[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            text = node.get("text")
            if isinstance(text, str):
                chunks.append(text)
            children = node.get("content")
            if isinstance(children, list):
                for child in children:
                    walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(content_json)
    return "\n".join(chunks)


def _iter_atomic_field_values(resume_json: dict):
    """
    遍历 Resume_JSON 中所有携带 (value, status) 的标量字段（不含 highlights/stack 数组型）。
    yield (field_path, value, status)
    """
    basics = resume_json.get("basics")
    if isinstance(basics, dict):
        for field in BASICS_FIELDS:
            cell = basics.get(field)
            if _is_field_cell(cell):
                yield f"basics.{field}", cell["value"], cell["status"]

    for name in ("education", "projects", "experience", "awards", "certificates"):
        section = resume_json.get(name)
        if not isinstance(section, dict):
            continue
        items = section.get("items") or []
        for idx, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            for field in ITEM_FIELDS.get(name, ()):
                cell = item.get(field)
                if _is_field_cell(cell):
                    yield f"{name}.items[{idx}].{field}", cell["value"], cell["status"]

    skills = resume_json.get("skills")
    if isinstance(skills, dict):
        items = skills.get("items") or []
        for gidx, group in enumerate(items):
            if not isinstance(group, dict):
                continue
            sub = group.get("items") or []
            for sidx, skill in enumerate(sub):
                if isinstance(skill, dict) and "name" in skill and "status" in skill:
                    yield (
                        f"skills.items[{gidx}].items[{sidx}].name",
                        skill.get("name"),
                        skill.get("status"),
                    )


def detect_fabrication(
    resume_json: dict,
    plain_text: str,
    content_json: Any = None,
) -> list[str]:
    """
    反编造比对：返回所有 status=confirmed/inferred_from_text 但值在草稿中找不到的字段路径列表。

    比对算法：NFKC + casefold + 压平空白 + 剔除标点的子串匹配。
    长度 < 2 字符的值被视为偶然子串，跳过比对（避免单字误判）。
    """
    haystack_raw = (plain_text or "")
    if content_json is not None:
        haystack_raw = haystack_raw + "\n" + _flatten_text_from_content_json(content_json)
    haystack = _normalize_for_match(haystack_raw)
    if not haystack:
        # 没有原文可比对，但仍有 confirmed 字段 → 全部疑似编造
        suspect: list[str] = []
        for path, value, status in _iter_atomic_field_values(resume_json):
            if status not in ("confirmed", "inferred_from_text"):
                continue
            if isinstance(value, str) and value.strip():
                if len(value.strip()) >= 2:
                    suspect.append(path)
            elif isinstance(value, list) and value:
                # 列表型字段每个元素都看
                for v in value:
                    if isinstance(v, str) and len(v.strip()) >= 2:
                        suspect.append(path)
                        break
        return suspect

    suspect = []
    for path, value, status in _iter_atomic_field_values(resume_json):
        if status not in ("confirmed", "inferred_from_text"):
            continue
        if isinstance(value, str):
            v = value.strip()
            if len(v) < 2:
                continue
            normalized = _normalize_for_match(v)
            if normalized and normalized not in haystack:
                suspect.append(path)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str) and len(item.strip()) >= 2:
                    normalized = _normalize_for_match(item)
                    if normalized and normalized not in haystack:
                        suspect.append(path)
                        break
    return suspect


# ─────────────────────────────────────────────
# 非简历内容启发式（Requirement 5.5）
# ─────────────────────────────────────────────

# 简历常见关键词
_RESUME_KEYWORDS = (
    "简历", "教育", "项目", "实习", "工作", "技能", "研究", "毕业", "学校", "公司",
    "experience", "education", "project", "skill", "intern", "resume", "cv",
)
# 非简历常见关键词（日记、待办、聊天）
_NON_RESUME_KEYWORDS = (
    "今天天气", "亲爱的日记", "todo", "待办", "@", "晚安", "❤", "聊天",
)


def detect_non_resume_content(plain_text: str) -> bool:
    """
    极简启发式：
      - 文本明显短（< 40 字符）→ False（让上游走 empty_input 路径）
      - 命中 ≥ 2 个非简历关键词且未命中任何简历关键词 → True
      - 否则 False
    """
    if not isinstance(plain_text, str):
        return False
    text = plain_text.strip()
    if len(text) < 40:
        return False
    lowered = text.casefold()
    resume_hits = sum(1 for kw in _RESUME_KEYWORDS if kw.casefold() in lowered)
    non_hits = sum(1 for kw in _NON_RESUME_KEYWORDS if kw.casefold() in lowered)
    return resume_hits == 0 and non_hits >= 2
