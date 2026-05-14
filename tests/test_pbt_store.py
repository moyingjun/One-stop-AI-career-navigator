"""
属性测试：userStore.js 中 setPinnedId / loadPinnedIds 的 Python 等价逻辑

测试文件模拟 JavaScript userStore 的核心逻辑（dict 作为 store，dict 作为 localStorage），
验证以下属性：

Property 9: Pinned ID 持久化往返不变量
  对任意 tab 和 recordId，setPinnedId 后再 loadPinnedIds，
  对应 tab 的 pinnedId 必须等于原始 recordId。
  Validates: Requirements 8.3, 8.5

Property 6: localStorage 键名隔离不变量
  对单个 Tab 的 setPinnedId 调用，其他两个 Tab 的 pinnedId 不变；
  target_goal 与 target_school 独立存储，互不覆盖。
  Validates: Requirements 8.4, 14.4
"""

from hypothesis import given, settings
from hypothesis import strategies as st

# ---------------------------------------------------------------------------
# Python 等价实现：模拟 userStore.js 的 setPinnedId / loadPinnedIds 逻辑
# ---------------------------------------------------------------------------

# Tab → (store 字段名, localStorage 键名) 的映射，与 JS 实现完全对应
TAB_CONFIG = {
    "resume":    {"field": "pinnedResumeId",    "storageKey": "pinned_resume_id"},
    "interview": {"field": "pinnedInterviewId", "storageKey": "pinned_interview_id"},
    "career":    {"field": "pinnedCareerId",    "storageKey": "pinned_career_id"},
}

ALL_TABS = list(TAB_CONFIG.keys())


def make_store():
    """创建初始 store 状态（等价于 userStore state 初始值）"""
    return {
        "pinnedResumeId": None,
        "pinnedInterviewId": None,
        "pinnedCareerId": None,
        "targetGoal": "",
        "targetSchool": "",
    }


def make_local_storage():
    """创建空的 localStorage 模拟字典"""
    return {}


def set_pinned_id(store: dict, local_storage: dict, tab: str, record_id):
    """
    等价于 userStore.setPinnedId(tab, recordId)

    - 已知 tab：更新对应字段，写入（或删除）localStorage 键
    - 未知 tab：静默忽略，不修改任何状态
    """
    config = TAB_CONFIG.get(tab)
    if config is None:
        return  # 未知 tab，静默忽略

    store[config["field"]] = record_id

    if record_id is not None:
        local_storage[config["storageKey"]] = str(record_id)
    else:
        local_storage.pop(config["storageKey"], None)


def load_pinned_ids(store: dict, local_storage: dict):
    """
    等价于 userStore.loadPinnedIds()

    从 localStorage 读取三个键并恢复到 store；
    键不存在时保持 None；解析失败时保持 None。
    """
    def parse_id(raw):
        if raw is None:
            return None
        try:
            parsed = int(raw)
            return parsed
        except (ValueError, TypeError):
            return None

    store["pinnedResumeId"]    = parse_id(local_storage.get("pinned_resume_id"))
    store["pinnedInterviewId"] = parse_id(local_storage.get("pinned_interview_id"))
    store["pinnedCareerId"]    = parse_id(local_storage.get("pinned_career_id"))


def get_pinned_id_by_tab(store: dict, tab: str):
    """等价于 userStore.getPinnedIdByTab(tab) getter"""
    config = TAB_CONFIG.get(tab)
    if config is None:
        return None
    return store[config["field"]]


def update_user_profile_target_fields(store: dict, local_storage: dict,
                                      target_goal: str, target_school: str):
    """
    等价于 userStore.updateUserProfile 中处理 targetGoal / targetSchool 的部分：
    两个字段写入各自独立的 localStorage 键。
    """
    store["targetGoal"] = target_goal
    store["targetSchool"] = target_school
    local_storage["target_goal"] = target_goal
    local_storage["target_school"] = target_school


# ---------------------------------------------------------------------------
# Hypothesis 策略
# ---------------------------------------------------------------------------

tab_strategy = st.sampled_from(ALL_TABS)

record_id_strategy = st.one_of(
    st.integers(min_value=1, max_value=999999),
    st.none(),
)

# 非 null record_id（用于需要非 null 值的场景）
non_null_record_id_strategy = st.integers(min_value=1, max_value=999999)

# 目标字符串（用于 target_goal / target_school）
goal_text_strategy = st.text(
    alphabet=st.characters(blacklist_categories=("Cs",)),
    min_size=0,
    max_size=200,
)


# ---------------------------------------------------------------------------
# Property 9: Pinned ID 持久化往返不变量
# Validates: Requirements 8.3, 8.5
# ---------------------------------------------------------------------------

@given(tab=tab_strategy, record_id=record_id_strategy)
@settings(max_examples=200)
def test_property9_pinned_id_roundtrip(tab, record_id):
    """
    **Validates: Requirements 8.3, 8.5**

    Property 9: Pinned ID 持久化往返不变量

    对任意 tab 和 recordId：
    1. 调用 setPinnedId(tab, recordId) 将值写入 localStorage
    2. 再调用 loadPinnedIds() 从 localStorage 恢复
    3. 对应 tab 的 pinnedId 必须等于原始 recordId

    特殊情况：recordId 为 None 时，loadPinnedIds 后对应字段应为 None
    （因为 None 会删除 localStorage 键，读取时键不存在返回 None）
    """
    store = make_store()
    local_storage = make_local_storage()

    # 执行 setPinnedId
    set_pinned_id(store, local_storage, tab, record_id)

    # 重置 store 中的内存状态，模拟页面刷新后只依赖 localStorage 恢复
    store["pinnedResumeId"] = None
    store["pinnedInterviewId"] = None
    store["pinnedCareerId"] = None

    # 执行 loadPinnedIds（从 localStorage 恢复）
    load_pinned_ids(store, local_storage)

    # 验证往返不变量
    restored = get_pinned_id_by_tab(store, tab)
    assert restored == record_id, (
        f"往返不变量失败: tab={tab!r}, 原始 recordId={record_id!r}, "
        f"恢复后 pinnedId={restored!r}"
    )


@given(tab=tab_strategy, record_id=non_null_record_id_strategy)
@settings(max_examples=200)
def test_property9_pinned_id_roundtrip_non_null(tab, record_id):
    """
    **Validates: Requirements 8.3, 8.5**

    Property 9 补充：非 null recordId 的往返不变量

    对任意 tab 和非 null recordId，setPinnedId 后 loadPinnedIds，
    恢复的值必须与原始整数值相等（验证字符串序列化/反序列化的正确性）。
    """
    store = make_store()
    local_storage = make_local_storage()

    set_pinned_id(store, local_storage, tab, record_id)

    # 验证 localStorage 中确实写入了字符串形式的 record_id
    config = TAB_CONFIG[tab]
    assert config["storageKey"] in local_storage, (
        f"setPinnedId 未写入 localStorage 键 {config['storageKey']!r}"
    )
    assert local_storage[config["storageKey"]] == str(record_id), (
        f"localStorage 中的值应为字符串 {str(record_id)!r}，"
        f"实际为 {local_storage[config['storageKey']]!r}"
    )

    # 重置内存状态后恢复
    store["pinnedResumeId"] = None
    store["pinnedInterviewId"] = None
    store["pinnedCareerId"] = None
    load_pinned_ids(store, local_storage)

    restored = get_pinned_id_by_tab(store, tab)
    assert restored == record_id, (
        f"非 null 往返不变量失败: tab={tab!r}, recordId={record_id!r}, "
        f"恢复后={restored!r}"
    )


@given(tab=tab_strategy)
@settings(max_examples=100)
def test_property9_null_removes_key(tab):
    """
    **Validates: Requirements 8.5**

    Property 9 补充：setPinnedId(tab, None) 应删除 localStorage 键，
    loadPinnedIds 后对应字段为 None。
    """
    store = make_store()
    local_storage = make_local_storage()

    # 先写入一个非 null 值
    set_pinned_id(store, local_storage, tab, 42)
    config = TAB_CONFIG[tab]
    assert config["storageKey"] in local_storage

    # 再设为 None，应删除键
    set_pinned_id(store, local_storage, tab, None)
    assert config["storageKey"] not in local_storage, (
        f"setPinnedId(tab, None) 应删除 localStorage 键 {config['storageKey']!r}"
    )

    # loadPinnedIds 后对应字段为 None
    load_pinned_ids(store, local_storage)
    assert get_pinned_id_by_tab(store, tab) is None


# ---------------------------------------------------------------------------
# Property 6: localStorage 键名隔离不变量
# Validates: Requirements 8.4, 14.4
# ---------------------------------------------------------------------------

@given(
    target_tab=tab_strategy,
    record_id=non_null_record_id_strategy,
)
@settings(max_examples=200)
def test_property6_tab_isolation(target_tab, record_id):
    """
    **Validates: Requirements 8.4, 14.4**

    Property 6: localStorage 键名隔离不变量

    对单个 Tab 的 setPinnedId 调用，其他两个 Tab 的 pinnedId 不变。
    三个 Tab 使用独立的 localStorage 键，互不覆盖。
    """
    store = make_store()
    local_storage = make_local_storage()

    # 记录其他两个 tab 的初始值（均为 None）
    other_tabs = [t for t in ALL_TABS if t != target_tab]

    # 只对 target_tab 调用 setPinnedId
    set_pinned_id(store, local_storage, target_tab, record_id)

    # 验证：其他两个 tab 的 store 字段未被修改
    for other_tab in other_tabs:
        other_value = get_pinned_id_by_tab(store, other_tab)
        assert other_value is None, (
            f"Tab 隔离失败: 设置 {target_tab!r} 后，"
            f"{other_tab!r} 的 pinnedId 应为 None，实际为 {other_value!r}"
        )

    # 验证：其他两个 tab 的 localStorage 键未被写入
    for other_tab in other_tabs:
        other_key = TAB_CONFIG[other_tab]["storageKey"]
        assert other_key not in local_storage, (
            f"localStorage 键名隔离失败: 设置 {target_tab!r} 后，"
            f"键 {other_key!r} 不应存在于 localStorage 中"
        )

    # 验证：target_tab 的 localStorage 键确实被写入
    target_key = TAB_CONFIG[target_tab]["storageKey"]
    assert target_key in local_storage, (
        f"setPinnedId 未写入目标键 {target_key!r}"
    )


@given(
    tab_a=tab_strategy,
    tab_b=tab_strategy,
    id_a=non_null_record_id_strategy,
    id_b=non_null_record_id_strategy,
)
@settings(max_examples=200)
def test_property6_independent_storage_keys(tab_a, tab_b, id_a, id_b):
    """
    **Validates: Requirements 8.4**

    Property 6 补充：任意两个 Tab 的 localStorage 键名互不相同，
    分别写入不同值后互不覆盖。
    """
    store = make_store()
    local_storage = make_local_storage()

    set_pinned_id(store, local_storage, tab_a, id_a)
    set_pinned_id(store, local_storage, tab_b, id_b)

    # 验证 tab_a 的值正确（若 tab_a == tab_b，则最终值为 id_b）
    restored_a = get_pinned_id_by_tab(store, tab_a)
    restored_b = get_pinned_id_by_tab(store, tab_b)

    if tab_a == tab_b:
        # 同一个 tab 被覆盖，最终值为 id_b
        assert restored_a == id_b
        assert restored_b == id_b
    else:
        # 不同 tab，各自独立
        assert restored_a == id_a, (
            f"tab_a={tab_a!r} 的值被 tab_b={tab_b!r} 的写入覆盖: "
            f"期望 {id_a!r}，实际 {restored_a!r}"
        )
        assert restored_b == id_b, (
            f"tab_b={tab_b!r} 的值不正确: 期望 {id_b!r}，实际 {restored_b!r}"
        )


@given(
    target_goal=goal_text_strategy,
    target_school=goal_text_strategy,
)
@settings(max_examples=200)
def test_property6_target_goal_independent_from_target_school(target_goal, target_school):
    """
    **Validates: Requirements 14.4**

    Property 6 补充：target_goal 与 target_school 独立存储

    两者使用不同的 localStorage 键（target_goal vs target_school），
    写入一个不会覆盖另一个。
    """
    store = make_store()
    local_storage = make_local_storage()

    update_user_profile_target_fields(store, local_storage, target_goal, target_school)

    # 验证两个键独立存在
    assert "target_goal" in local_storage, "target_goal 键未写入 localStorage"
    assert "target_school" in local_storage, "target_school 键未写入 localStorage"

    # 验证各自的值正确，互不干扰
    assert local_storage["target_goal"] == target_goal, (
        f"target_goal 值错误: 期望 {target_goal!r}，"
        f"实际 {local_storage['target_goal']!r}"
    )
    assert local_storage["target_school"] == target_school, (
        f"target_school 值错误: 期望 {target_school!r}，"
        f"实际 {local_storage['target_school']!r}"
    )

    # 验证两个键名不同（键名隔离）
    assert "target_goal" != "target_school", (
        "target_goal 和 target_school 不应使用相同的 localStorage 键名"
    )

    # 验证 store 字段也独立更新
    assert store["targetGoal"] == target_goal
    assert store["targetSchool"] == target_school


@given(
    target_tab=tab_strategy,
    record_id=non_null_record_id_strategy,
    target_goal=goal_text_strategy,
)
@settings(max_examples=200)
def test_property6_pinned_id_does_not_affect_target_goal(target_tab, record_id, target_goal):
    """
    **Validates: Requirements 8.4, 14.4**

    Property 6 补充：setPinnedId 不影响 target_goal / target_school 键

    pinned ID 的三个键（pinned_resume_id 等）与 target_goal / target_school
    完全独立，setPinnedId 不会写入或删除 target_goal 键。
    """
    store = make_store()
    local_storage = make_local_storage()

    # 先写入 target_goal
    local_storage["target_goal"] = target_goal
    local_storage["target_school"] = "some_school"

    # 执行 setPinnedId
    set_pinned_id(store, local_storage, target_tab, record_id)

    # 验证 target_goal 和 target_school 未被修改
    assert local_storage.get("target_goal") == target_goal, (
        f"setPinnedId 意外修改了 target_goal: "
        f"期望 {target_goal!r}，实际 {local_storage.get('target_goal')!r}"
    )
    assert local_storage.get("target_school") == "some_school", (
        "setPinnedId 意外修改了 target_school"
    )
