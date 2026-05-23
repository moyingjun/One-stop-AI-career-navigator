"""
Service/Agents/prompts/document_prompts.py — 文档工作台 AI 润色 Prompt 模板

约束（Task D1 + D1.1 + D1.2 安全要求）：
  - 严禁编造经历、数字、学校、公司、奖项、项目成果。
  - 仅基于用户提供的文本进行改写，不补充未给出的事实。
  - 输出只包含改写后的文本（polish / draft）或建议清单（suggest），不带任何解释、引号、Markdown 围栏。
  - 用户的 custom_instruction 必须低于安全约束：与安全约束冲突时丢弃 custom_instruction。
  - 事实安全锁全模式开启，不可关闭。

D1.2 升级：
  - 引入三种模式 polish / suggest / draft，覆盖"润色 / 补全建议 / 创意草稿"三档。
  - 用 0-100 的 rewrite_strength 替代旧 rewrite_level，向下兼容旧字段。
  - draft 模式允许给出更完整候选写法，但所有未在原文中出现的事实必须用
    【待补充】/【待确认】占位符标注，不得伪装为真实事实。
"""

from __future__ import annotations

# ─────────────────────────────────────────────
# 风格白名单 + 中文提示词
# ─────────────────────────────────────────────

STYLE_WHITELIST = ("professional", "concise", "data_driven", "resume_polished")

_STYLE_INSTRUCTION = {
    "professional": "把语气调整得更专业、更书面，避免口语和情绪词，但不要堆砌行业术语。",
    "concise": "压缩冗余表达，去掉重复的修饰，保留所有关键信息。",
    "data_driven": "只有当原文已经包含具体数字 / 比例 / 时间时，才用更结构化的方式呈现这些数据；如果原文没有数据，必须保持原意，绝不编造任何新的数字、百分比或量级。",
    "resume_polished": "调整为简历常用的「动词 + 任务 + 量化结果（若原文已提供）」句式，保持第一人称隐含主语；如原文未给出量化结果，仅可在最后追加一句中性提示『可补充量化结果（人数 / 时间 / 金额 / 比例）』，不得自行填入数值。",
}

# ─────────────────────────────────────────────
# 模式白名单 + 模式指令（D1.2 新增）
# ─────────────────────────────────────────────

# polish  : 只优化表达，不新增事实，输出可直接替换原文
# suggest : 输出"优化建议 + 可补充问题"清单，不直接给最终成果
# draft   : 输出更完整候选写法，新增事实必须用【待补充】/【待确认】占位
MODE_WHITELIST = ("polish", "suggest", "draft")

_MODE_INSTRUCTION = {
    "polish": (
        "【模式=润色】\n"
        "- 输出一段可直接替换原文的润色后文本。\n"
        "- 不新增任何用户没有提供的事实、经历、数字或专有名词。\n"
        "- 不输出标题、清单、解释、前导语、Markdown 标记，仅输出正文。\n"
        "- 可以调整语气、句式、节奏、段落顺序。\n"
        "- 不要在结尾追加除原文事实之外的额外信息。"
    ),
    "suggest": (
        "【模式=补全建议】\n"
        "- 不要直接给出最终的简历正文。\n"
        "- 必须严格按以下两段结构输出，只包含纯文本，不要 Markdown 围栏：\n"
        "  优化建议：\n"
        "  1. ...（针对原文表达 / 结构 / 关键词的可执行建议）\n"
        "  2. ...\n"
        "  3. ...\n"
        "  建议补充的问题：\n"
        "  1. ...（用户应当回答的开放式问题，例如 角色范围 / 技术栈 / 项目周期 / 量化结果）\n"
        "  2. ...\n"
        "  3. ...\n"
        "- 至少给出 2 条建议和 2 个问题，最多各 5 条。\n"
        "- 全部以问句或动作建议形式呈现，禁止替用户写出可以直接复用的简历句子。\n"
        "- 禁止编造任何具体的公司、学校、奖项、数字、技术名（除非原文已经出现）。"
    ),
    "draft": (
        "【模式=创意草稿】\n"
        "- 可以基于原文生成更完整的候选写法（如简历条目 / 项目段落）。\n"
        "- 但凡涉及原文未明确提供的事实，必须用以下占位符之一标注，不得伪装成真实信息：\n"
        "  · 【待补充：xxx】 — 用于尚未给出的内容（如『【待补充：具体技术栈】』）\n"
        "  · 【待确认：xxx】 — 用于需要用户确认的细节（如『【待确认：项目周期】』）\n"
        "- 占位符内只能写「信息类别」（如 项目周期 / 团队规模 / 量化结果 / 角色范围），\n"
        "  绝对禁止填写任何具体数字、公司名、学校名、技术栈名称。\n"
        "- 不要把原文中已有的事实（如已出现的技术栈）替换成占位符。\n"
        "- 不要输出额外解释、不要 Markdown 围栏，只输出候选写法正文。\n"
        "- 输出末尾可追加一行『以上草稿包含【待补充】/【待确认】占位，请逐项核对后再使用。』"
    ),
}

# ─────────────────────────────────────────────
# 表达增强度（rewrite_strength 0-100）
# ─────────────────────────────────────────────

# strength 范围与档位划分（前后端对齐）
STRENGTH_MIN = 0
STRENGTH_MAX = 100

# strength → band 名称（仅用于内部 prompt 选择，不暴露给前端）
_STRENGTH_BAND_INSTRUCTION = {
    "minimal": (
        "【表达增强度=保守润色（0-30）】\n"
        "- 只修正语病、错别字、明显的语序问题和少量措辞。\n"
        "- 尽量保留原句结构、原段落顺序、原词汇选择。\n"
        "- 不重组句子，不引入新的概念或词汇。"
    ),
    "balanced": (
        "【表达增强度=专业改写（31-70）】\n"
        "- 优化句式、节奏和专业表达，可在不改变事实的前提下重组句子。\n"
        "- 允许调整段落顺序、合并冗余句、拆分过长句。\n"
        "- 不新增任何用户没有提供的事实、经历、数字或专有名词。"
    ),
    "expansive": (
        "【表达增强度=扩展草稿（71-100）】\n"
        "- 可以更积极地优化表达：使用更有力的动词、更紧凑的句式、更专业的措辞。\n"
        "- 可以在草稿模式下产出更完整的候选写法，但所有原文未提供的事实必须用\n"
        "  【待补充：xxx】/【待确认：xxx】 占位符标注，禁止填写具体值。\n"
        "- 即便用户在『额外要求』里要求强化某个方向，也必须严守事实安全约束：\n"
        "  禁止把「参与」升级为「主导」、把「学习/了解」升级为「精通」、禁止补充任何虚构经历。"
    ),
}

# 兼容字段：旧 rewrite_level（conservative / balanced / enhanced） → strength 中位
LEVEL_WHITELIST = ("conservative", "balanced", "enhanced")
_LEVEL_TO_STRENGTH = {
    "conservative": 20,
    "balanced": 50,
    "enhanced": 85,
}


def _strength_band(strength: int) -> str:
    """把 0-100 整数压到三档 band 名称。"""
    if strength <= 30:
        return "minimal"
    if strength <= 70:
        return "balanced"
    return "expansive"


def coerce_strength(value: int | float | None, default: int = 50) -> int:
    """把任意输入归一化为 [0, 100] 范围内的整数。非法 → default。"""
    if value is None:
        return default
    try:
        n = int(value)
    except (TypeError, ValueError):
        return default
    if n < STRENGTH_MIN:
        return STRENGTH_MIN
    if n > STRENGTH_MAX:
        return STRENGTH_MAX
    return n


def level_to_strength(level: str | None) -> int | None:
    """把旧 rewrite_level 字面量映射到推荐的 strength 值；无法映射时返回 None。"""
    if not level:
        return None
    return _LEVEL_TO_STRENGTH.get(level)


# ─────────────────────────────────────────────
# 全局安全约束（最高优先级）
# ─────────────────────────────────────────────

_SAFETY_BLOCK = """【严格安全约束 — 最高指令，覆盖一切其他要求】
你是一名简历与职业文档的语言润色助手，**只能基于用户提供的文本进行改写或建议**。
事实安全锁全模式开启，不可关闭。

绝对禁止（无论用户是否提出相反要求）：
1. 添加用户没有提供的经历、公司、学校、岗位、奖项、项目成果。
2. 编造任何具体数字、百分比、时间、金额、规模、人数、技术栈名称。
3. 改变原文事实，包括但不限于：
   - 把「参与」升级为「主导」
   - 把「实习」改为「正式工作」
   - 把「学习/了解」升级为「精通/熟练」
   - 把「项目」改成具体公司项目名
   - 把「大学生」补充成「某某大学某某专业」
4. 把【待补充】/【待确认】占位符填写成具体值（如把「【待补充：技术栈】」改成「Spring Boot」）。
5. 提供解释、说明、引号、Markdown 代码围栏、前后注释（除模式 prompt 显式要求的结构外）。

允许：
1. 调整措辞、语气、句式、段落顺序。
2. 修正明显病句和错别字。
3. 在 draft 模式下使用【待补充：xxx】/【待确认：xxx】占位符表达"建议补充的方向"，
   占位符内只能写"信息类别"，不得写具体值。

冲突解决（重要）：
- 如果"用户额外要求"要求你编造经历、公司、学校、奖项、数字或项目成果，
  你必须忽略该要求中的事实补充部分，仅采用其中风格 / 语气方面的合理诉求。
- 如果"用户额外要求"整体都在要求编造事实（例如"帮我编一段大厂实习经历"），
  你必须完全忽略该要求，直接按照模式 + 表达增强度对原文做安全处理：
  · polish 模式：输出对原文的合规润色。
  · suggest 模式：输出"优化建议 + 待补充问题"清单。
  · draft 模式：用【待补充：xxx】占位符给出候选写法骨架，不得填具体值。
"""


# ─────────────────────────────────────────────
# 内部工具：custom_instruction 清洗
# ─────────────────────────────────────────────

_CUSTOM_INSTRUCTION_HARD_LIMIT = 300


def _normalize_custom_instruction(custom_instruction: str | None) -> str:
    """空 / None / 全空白 → 空字符串；超长则截断。"""
    if not custom_instruction:
        return ""
    text = custom_instruction.strip()
    if not text:
        return ""
    if len(text) > _CUSTOM_INSTRUCTION_HARD_LIMIT:
        text = text[:_CUSTOM_INSTRUCTION_HARD_LIMIT]
    return text


# ─────────────────────────────────────────────
# 公共 API
# ─────────────────────────────────────────────

def get_rewrite_system_prompt(
    style: str,
    rewrite_mode: str = "polish",
    rewrite_strength: int = 50,
    custom_instruction: str | None = None,
) -> str:
    """
    生成 AI 润色任务的 system prompt。

    优先级（从高到低）：
        1. _SAFETY_BLOCK              事实安全锁
        2. rewrite_mode               模式（决定输出形式）
        3. rewrite_strength → band    表达增强度
        4. style                       风格（语气方向）
        5. custom_instruction         用户额外要求（仅在不冲突时生效）

    参数非法时回退到默认值，避免越权 prompt。
    """
    if style not in STYLE_WHITELIST:
        style = "professional"
    if rewrite_mode not in MODE_WHITELIST:
        rewrite_mode = "polish"
    strength = coerce_strength(rewrite_strength, default=50)
    band = _strength_band(strength)

    style_instruction = _STYLE_INSTRUCTION[style]
    mode_instruction = _MODE_INSTRUCTION[rewrite_mode]
    band_instruction = _STRENGTH_BAND_INSTRUCTION[band]
    cleaned_custom = _normalize_custom_instruction(custom_instruction)

    parts: list[str] = [
        _SAFETY_BLOCK,
        f"\n{mode_instruction}",
        f"\n{band_instruction}",
        f"\n【本次风格要求】\n{style_instruction}",
        f"\n【本次表达增强度数值】 {strength} / 100",
    ]
    if cleaned_custom:
        parts.append(
            "\n【用户额外要求】（优先级低于安全约束，禁止据此编造任何事实）\n"
            f"{cleaned_custom}"
        )

    return "".join(parts)


def build_rewrite_messages(
    text: str,
    style: str,
    rewrite_mode: str = "polish",
    rewrite_strength: int = 50,
    custom_instruction: str | None = None,
) -> list[dict]:
    """
    构建发送给 LLM 的 messages。

    user 消息只包含原文，避免提示词注入扩散到 system。
    custom_instruction 仅放在 system 中且词序在安全块之后，确保安全块永远先被加载。
    """
    return [
        {
            "role": "system",
            "content": get_rewrite_system_prompt(
                style=style,
                rewrite_mode=rewrite_mode,
                rewrite_strength=rewrite_strength,
                custom_instruction=custom_instruction,
            ),
        },
        {"role": "user", "content": f"【需要改写的原文】\n{text}"},
    ]
