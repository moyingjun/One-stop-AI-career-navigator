"""
属性测试：DataSourceModal.vue 中 filteredByTab computed 的 Python 等价逻辑

测试文件模拟 Vue 组件 DataSourceModal 的核心过滤逻辑，
验证以下属性：

Property 10: DataSourceModal Tab 过滤不变量
  对任意历史记录集合和任意 activeTab，过滤后所有记录的 category
  必须符合该 Tab 的映射规则：
    - resume  → category === 'resume_diagnosis'
    - interview → category.startsWith('interview')
    - career  → category === 'career_planning'
  Validates: Requirements 9.1, 9.2
"""

from hypothesis import given, settings
from hypothesis import strategies as st

# ---------------------------------------------------------------------------
# Python 等价实现：模拟 DataSourceModal.vue 的 filteredByTab computed 逻辑
# ---------------------------------------------------------------------------

# 所有合法的 activeTab 取值
ALL_TABS = ["resume", "interview", "career"]

# Tab → category 过滤谓词映射（与 Vue 实现完全对应）
TAB_FILTER_RULES = {
    "resume":    lambda category: category == "resume_diagnosis",
    "interview": lambda category: category.startswith("interview"),
    "career":    lambda category: category == "career_planning",
}


def filtered_by_tab(history_records: list, active_tab: str) -> list:
    """
    等价于 DataSourceModal.vue 中的 computed filteredByTab：

    resume    → records where category === 'resume_diagnosis'
    interview → records where category.startsWith('interview')
    career    → records where category === 'career_planning'

    未知 activeTab 返回空列表（防御性处理）。
    """
    rule = TAB_FILTER_RULES.get(active_tab)
    if rule is None:
        return []
    return [r for r in history_records if rule(r.get("category", ""))]


def matches_tab_rule(category: str, active_tab: str) -> bool:
    """判断单条记录的 category 是否符合指定 Tab 的映射规则"""
    rule = TAB_FILTER_RULES.get(active_tab)
    if rule is None:
        return False
    return rule(category)


# ---------------------------------------------------------------------------
# Hypothesis 策略
# ---------------------------------------------------------------------------

# 合法的 activeTab 策略
active_tab_strategy = st.sampled_from(ALL_TABS)

# 合法的 category 值（覆盖所有 Tab 的有效值及无效值）
valid_categories = [
    "resume_diagnosis",
    "interview",
    "interview_evaluate",
    "interview_mock",
    "interview_practice",
    "career_planning",
    "agent_chat",
    "agent_general",
    "other_category",
    "",
    "resume",
    "career",
    "RESUME_DIAGNOSIS",          # 大小写不同，不应匹配
    "interview_extra_long_name", # interview 前缀变体
    "career_planning_extra",     # 不完全匹配
]

category_strategy = st.one_of(
    st.sampled_from(valid_categories),
    # 也生成随机字符串，覆盖更广的输入空间
    st.text(
        alphabet=st.characters(
            whitelist_categories=("Ll", "Lu", "Nd"),
            whitelist_characters="_",
        ),
        min_size=0,
        max_size=50,
    ),
)

# 单条历史记录策略（dict，含 category 字段及其他可选字段）
history_record_strategy = st.fixed_dictionaries(
    {"category": category_strategy},
    optional={
        "id": st.integers(min_value=1, max_value=999999),
        "scores": st.one_of(st.none(), st.text(max_size=100)),
        "created_at": st.text(max_size=30),
    },
)

# 历史记录列表策略（0 到 30 条）
history_records_strategy = st.lists(history_record_strategy, min_size=0, max_size=30)


# ---------------------------------------------------------------------------
# Property 10: DataSourceModal Tab 过滤不变量
# Validates: Requirements 9.1, 9.2
# ---------------------------------------------------------------------------


@given(history_records=history_records_strategy, active_tab=active_tab_strategy)
@settings(max_examples=300)
def test_property10_all_filtered_records_match_tab_rule(history_records, active_tab):
    """
    **Validates: Requirements 9.1, 9.2**

    Property 10: DataSourceModal Tab 过滤不变量（核心断言）

    对任意历史记录集合和任意 activeTab，
    filteredByTab 返回的所有记录的 category 必须符合该 Tab 的映射规则：
      - resume    → category == 'resume_diagnosis'
      - interview → category.startsWith('interview')
      - career    → category == 'career_planning'

    不符合规则的记录绝对不能出现在过滤结果中。
    """
    result = filtered_by_tab(history_records, active_tab)

    for record in result:
        category = record.get("category", "")
        assert matches_tab_rule(category, active_tab), (
            f"过滤不变量违反: activeTab={active_tab!r} 时，"
            f"结果中出现了不符合规则的记录 category={category!r}"
        )


@given(history_records=history_records_strategy, active_tab=active_tab_strategy)
@settings(max_examples=300)
def test_property10_non_matching_records_are_excluded(history_records, active_tab):
    """
    **Validates: Requirements 9.1, 9.2**

    Property 10 补充：不符合规则的记录必须被排除

    对任意历史记录集合和任意 activeTab，
    原始集合中所有不符合该 Tab 映射规则的记录，
    在 filteredByTab 的结果中必须不存在。
    """
    result = filtered_by_tab(history_records, active_tab)
    result_ids = {id(r) for r in result}

    for record in history_records:
        category = record.get("category", "")
        if not matches_tab_rule(category, active_tab):
            assert id(record) not in result_ids, (
                f"排除不变量违反: activeTab={active_tab!r} 时，"
                f"category={category!r} 的记录不应出现在过滤结果中，但实际出现了"
            )


@given(history_records=history_records_strategy, active_tab=active_tab_strategy)
@settings(max_examples=300)
def test_property10_filtered_is_subset_of_original(history_records, active_tab):
    """
    **Validates: Requirements 9.1, 9.2**

    Property 10 补充：过滤结果是原始集合的子集

    filteredByTab 只能减少记录，不能凭空增加记录。
    结果中的每条记录必须来自原始 history_records。
    """
    result = filtered_by_tab(history_records, active_tab)

    # 结果数量不超过原始数量
    assert len(result) <= len(history_records), (
        f"子集不变量违反: 过滤结果 ({len(result)} 条) 超过原始集合 ({len(history_records)} 条)"
    )

    # 结果中每条记录的对象引用必须来自原始列表
    original_ids = {id(r) for r in history_records}
    for record in result:
        assert id(record) in original_ids, (
            f"子集不变量违反: 过滤结果中出现了原始集合中不存在的记录 {record!r}"
        )


@given(active_tab=active_tab_strategy)
@settings(max_examples=100)
def test_property10_empty_input_returns_empty(active_tab):
    """
    **Validates: Requirements 9.1, 9.2**

    Property 10 补充：空输入返回空结果

    当 history_records 为空列表时，任意 activeTab 的过滤结果也必须为空。
    """
    result = filtered_by_tab([], active_tab)
    assert result == [], (
        f"空输入不变量违反: activeTab={active_tab!r}，"
        f"空输入应返回空列表，实际返回 {result!r}"
    )


@given(active_tab=active_tab_strategy)
@settings(max_examples=100)
def test_property10_all_matching_records_are_included(active_tab):
    """
    **Validates: Requirements 9.1, 9.2**

    Property 10 补充：所有符合规则的记录必须被包含（完整性）

    构造一批全部符合当前 Tab 规则的记录，
    过滤结果必须包含所有这些记录（不能漏掉任何一条）。
    """
    # 根据 activeTab 构造完全匹配的 category 值
    matching_categories = {
        "resume":    ["resume_diagnosis"],
        "interview": ["interview", "interview_evaluate", "interview_mock", "interview_practice"],
        "career":    ["career_planning"],
    }
    categories = matching_categories[active_tab]

    # 构造全部符合规则的记录列表
    matching_records = [{"category": cat, "id": i} for i, cat in enumerate(categories)]

    result = filtered_by_tab(matching_records, active_tab)

    assert len(result) == len(matching_records), (
        f"完整性不变量违反: activeTab={active_tab!r}，"
        f"输入 {len(matching_records)} 条全匹配记录，"
        f"但过滤结果只有 {len(result)} 条"
    )


@given(history_records=history_records_strategy)
@settings(max_examples=200)
def test_property10_resume_tab_only_shows_resume_diagnosis(history_records):
    """
    **Validates: Requirements 9.1, 9.2**

    Property 10 具体规则验证：resume Tab

    resume Tab 只显示 category == 'resume_diagnosis' 的记录，
    其他任何 category 值（包括 'resume'、'resume_analysis' 等）均不显示。
    """
    result = filtered_by_tab(history_records, "resume")

    for record in result:
        assert record.get("category") == "resume_diagnosis", (
            f"resume Tab 规则违反: 出现了 category={record.get('category')!r}，"
            f"resume Tab 只允许 'resume_diagnosis'"
        )


@given(history_records=history_records_strategy)
@settings(max_examples=200)
def test_property10_interview_tab_uses_startswith_rule(history_records):
    """
    **Validates: Requirements 9.1, 9.2**

    Property 10 具体规则验证：interview Tab

    interview Tab 使用 startsWith('interview') 规则，
    所有以 'interview' 开头的 category 均应显示，
    不以 'interview' 开头的均不显示。
    """
    result = filtered_by_tab(history_records, "interview")

    for record in result:
        category = record.get("category", "")
        assert category.startswith("interview"), (
            f"interview Tab 规则违反: 出现了 category={category!r}，"
            f"interview Tab 只允许以 'interview' 开头的 category"
        )


@given(history_records=history_records_strategy)
@settings(max_examples=200)
def test_property10_career_tab_only_shows_career_planning(history_records):
    """
    **Validates: Requirements 9.1, 9.2**

    Property 10 具体规则验证：career Tab

    career Tab 只显示 category == 'career_planning' 的记录，
    其他任何 category 值均不显示。
    """
    result = filtered_by_tab(history_records, "career")

    for record in result:
        assert record.get("category") == "career_planning", (
            f"career Tab 规则违反: 出现了 category={record.get('category')!r}，"
            f"career Tab 只允许 'career_planning'"
        )


@given(
    history_records=history_records_strategy,
    tab_a=active_tab_strategy,
    tab_b=active_tab_strategy,
)
@settings(max_examples=200)
def test_property10_different_tabs_have_disjoint_results_for_exclusive_categories(
    history_records, tab_a, tab_b
):
    """
    **Validates: Requirements 9.1, 9.2**

    Property 10 补充：不同 Tab 的过滤结果对于互斥 category 不重叠

    resume 和 career Tab 使用精确匹配规则，
    'resume_diagnosis' 和 'career_planning' 是互斥的 category 值，
    因此当 tab_a != tab_b 且两者均为精确匹配 Tab 时，
    它们的过滤结果不应有重叠（同一条记录不能同时出现在两个结果中）。
    """
    if tab_a == tab_b:
        return  # 同一 Tab，跳过

    # 只对 resume 和 career 这两个精确匹配 Tab 验证互斥性
    exact_match_tabs = {"resume", "career"}
    if tab_a not in exact_match_tabs or tab_b not in exact_match_tabs:
        return

    result_a = filtered_by_tab(history_records, tab_a)
    result_b = filtered_by_tab(history_records, tab_b)

    ids_a = {id(r) for r in result_a}
    ids_b = {id(r) for r in result_b}

    overlap = ids_a & ids_b
    assert len(overlap) == 0, (
        f"互斥不变量违反: tab_a={tab_a!r} 和 tab_b={tab_b!r} 的过滤结果有 {len(overlap)} 条重叠记录"
    )
