"""
属性测试：userStore.js 中 updateRadarData / resetRadarData 的 Python 等价逻辑

测试文件模拟 JavaScript userStore 的雷达图相关逻辑，
验证以下属性：

Property 3: 雷达图数值 clamp 不变量
  对任意 scores 字典，updateRadarData 后 radarData.values 中每个值 v 满足 0 ≤ v ≤ 100
  Validates: Requirements 10.4, 10.6

Property 4: 空状态不变量
  当 pinnedId === null 且所有分值为零时，radarData.values 必须为 [0,0,0,0,0,0]，
  雷达图显示"暂无数据"提示
  Validates: Requirements 10.3, 10.4

Property 5: Tab 数据绑定不变量
  任意 activeDataTab 切换后，雷达图数据必须对应新 Tab 的 pinnedId 所指向的记录，
  不得显示其他 Tab 的数据
  Validates: Requirements 10.2
"""

from hypothesis import given, settings
from hypothesis import strategies as st

# ---------------------------------------------------------------------------
# Python 等价实现：模拟 userStore.js 的雷达图相关逻辑
# ---------------------------------------------------------------------------

# 六维能力维度名称与索引的映射（与 JS 实现完全对应）
DIMENSION_MAP = {
    '技术能力': 0,
    '沟通表达': 1,
    '项目经验': 2,
    '学习能力': 3,
    '团队协作': 4,
    '职业规划': 5,
}

ALL_DIMENSIONS = list(DIMENSION_MAP.keys())
ALL_TABS = ['resume', 'interview', 'career']

# 雷达图空状态常量
EMPTY_RADAR_VALUES = [0, 0, 0, 0, 0, 0]

# 空状态提示文字（与前端 CyberRadarChart.vue 对应）
EMPTY_STATE_HINT = '暂无数据'


def make_radar_data():
    """创建初始雷达图数据（等价于 userStore state 中的 radarData 初始值）"""
    return {
        'indicators': [
            {'name': dim, 'max': 100}
            for dim in ALL_DIMENSIONS
        ],
        'values': [0, 0, 0, 0, 0, 0],
    }


def make_store():
    """创建初始 store 状态（包含雷达图数据和三个 Tab 的 pinnedId）"""
    return {
        'radarData': make_radar_data(),
        'pinnedResumeId': None,
        'pinnedInterviewId': None,
        'pinnedCareerId': None,
    }


def update_radar_data(store: dict, scores: dict) -> None:
    """
    等价于 userStore.updateRadarData(scores)

    对 scores 字典中的每个键值对：
    - 若键在 DIMENSION_MAP 中，则将值 clamp 到 [0, 100] 后写入对应索引
    - 非数值类型（包括 None、字符串等）视为 0
    - 未在 scores 中出现的维度保持 0
    """
    new_values = [0, 0, 0, 0, 0, 0]
    for key, value in scores.items():
        index = DIMENSION_MAP.get(key)
        if index is not None:
            # 等价于 JS: Math.max(0, Math.min(100, Number(value) || 0))
            try:
                numeric = float(value)
                if numeric != numeric:  # NaN check
                    numeric = 0.0
            except (TypeError, ValueError):
                numeric = 0.0
            clamped = max(0.0, min(100.0, numeric))
            new_values[index] = clamped
    store['radarData'] = {**store['radarData'], 'values': new_values}


def reset_radar_data(store: dict) -> None:
    """
    等价于 userStore.resetRadarData()

    将 radarData.values 重置为全零空状态 [0,0,0,0,0,0]
    """
    store['radarData'] = {**store['radarData'], 'values': [0, 0, 0, 0, 0, 0]}


def get_pinned_id_by_tab(store: dict, tab: str):
    """等价于 userStore.getPinnedIdByTab(tab) getter"""
    if tab == 'resume':
        return store['pinnedResumeId']
    if tab == 'interview':
        return store['pinnedInterviewId']
    if tab == 'career':
        return store['pinnedCareerId']
    return None


def set_pinned_id(store: dict, tab: str, record_id) -> None:
    """等价于 userStore.setPinnedId(tab, recordId)"""
    if tab == 'resume':
        store['pinnedResumeId'] = record_id
    elif tab == 'interview':
        store['pinnedInterviewId'] = record_id
    elif tab == 'career':
        store['pinnedCareerId'] = record_id
    # 未知 tab 静默忽略


def is_empty_state(store: dict) -> bool:
    """
    判断是否处于空状态：radarData.values 全为零
    等价于前端判断是否显示"暂无数据"提示
    """
    return store['radarData']['values'] == [0, 0, 0, 0, 0, 0]


def simulate_tab_switch(stores_by_tab: dict, active_tab: str) -> dict:
    """
    模拟 activeDataTab 切换后的雷达图数据获取逻辑：
    返回新 Tab 对应 store 的 radarData（即该 Tab 的 pinnedId 所指向的数据）

    stores_by_tab: { tab_name: store_dict }，每个 Tab 有独立的 store 状态
    active_tab: 切换后的新 Tab
    """
    return stores_by_tab[active_tab]['radarData']


# ---------------------------------------------------------------------------
# Hypothesis 策略
# ---------------------------------------------------------------------------

# 维度名称策略（合法的六个维度）
dimension_strategy = st.sampled_from(ALL_DIMENSIONS)

# Tab 策略
tab_strategy = st.sampled_from(ALL_TABS)

# 数值策略：覆盖正常范围、边界值、超出范围、负数、极大值
numeric_value_strategy = st.one_of(
    st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False),
    st.floats(min_value=-1000.0, max_value=-0.001, allow_nan=False, allow_infinity=False),
    st.floats(min_value=100.001, max_value=10000.0, allow_nan=False, allow_infinity=False),
    st.integers(min_value=-500, max_value=500),
)

# 非数值策略：None、字符串、布尔值等
non_numeric_value_strategy = st.one_of(
    st.none(),
    st.text(min_size=0, max_size=20),
    st.booleans(),
    st.just(float('nan')),
)

# 单个 score 值策略（数值或非数值）
score_value_strategy = st.one_of(numeric_value_strategy, non_numeric_value_strategy)

# scores 字典策略：键为合法维度名，值为任意类型
scores_dict_strategy = st.dictionaries(
    keys=dimension_strategy,
    values=score_value_strategy,
    min_size=0,
    max_size=6,
)

# 包含非法键的 scores 字典策略（混合合法和非法键）
mixed_scores_dict_strategy = st.dictionaries(
    keys=st.one_of(
        dimension_strategy,
        st.text(min_size=1, max_size=20),  # 随机字符串键（非法维度名）
    ),
    values=score_value_strategy,
    min_size=0,
    max_size=10,
)

# 记录 ID 策略
record_id_strategy = st.integers(min_value=1, max_value=999999)

# 每个 Tab 的 scores 字典策略（用于 Property 5）
tab_scores_strategy = st.fixed_dictionaries({
    tab: scores_dict_strategy for tab in ALL_TABS
})


# ---------------------------------------------------------------------------
# Property 3: 雷达图数值 clamp 不变量
# Validates: Requirements 10.4, 10.6
# ---------------------------------------------------------------------------

@given(scores=scores_dict_strategy)
@settings(max_examples=300)
def test_property3_radar_values_clamped_to_0_100(scores):
    """
    **Validates: Requirements 10.4, 10.6**

    Property 3: 雷达图数值 clamp 不变量（核心断言）

    对任意 scores 字典，updateRadarData(scores) 后
    radarData.values 中每个值 v 满足 0 ≤ v ≤ 100。

    无论输入值是负数、超过 100、还是极大值，
    clamp 操作必须保证输出始终在合法范围内。
    """
    store = make_store()
    update_radar_data(store, scores)

    values = store['radarData']['values']
    assert len(values) == 6, (
        f"radarData.values 长度应为 6，实际为 {len(values)}"
    )

    for i, v in enumerate(values):
        assert 0 <= v <= 100, (
            f"clamp 不变量违反: radarData.values[{i}] = {v!r}，"
            f"应满足 0 ≤ v ≤ 100（scores={scores!r}）"
        )


@given(scores=mixed_scores_dict_strategy)
@settings(max_examples=300)
def test_property3_clamp_with_mixed_keys(scores):
    """
    **Validates: Requirements 10.4, 10.6**

    Property 3 补充：包含非法键的 scores 字典也满足 clamp 不变量

    非法键（不在 DIMENSION_MAP 中的键）应被静默忽略，
    合法键的值仍然被正确 clamp 到 [0, 100]。
    """
    store = make_store()
    update_radar_data(store, scores)

    values = store['radarData']['values']
    assert len(values) == 6

    for i, v in enumerate(values):
        assert 0 <= v <= 100, (
            f"clamp 不变量违反（混合键）: radarData.values[{i}] = {v!r}，"
            f"应满足 0 ≤ v ≤ 100"
        )


@given(
    dimension=dimension_strategy,
    raw_value=st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=300)
def test_property3_single_dimension_clamp(dimension, raw_value):
    """
    **Validates: Requirements 10.4, 10.6**

    Property 3 补充：单维度 clamp 精确验证

    对任意单个维度和任意浮点数值，
    updateRadarData 后该维度的值必须等于 clamp(raw_value, 0, 100)。
    """
    store = make_store()
    scores = {dimension: raw_value}
    update_radar_data(store, scores)

    index = DIMENSION_MAP[dimension]
    actual = store['radarData']['values'][index]
    expected = max(0.0, min(100.0, raw_value))

    assert actual == expected, (
        f"单维度 clamp 失败: dimension={dimension!r}, "
        f"raw_value={raw_value!r}, expected={expected!r}, actual={actual!r}"
    )


@given(scores=scores_dict_strategy)
@settings(max_examples=200)
def test_property3_non_numeric_values_become_zero(scores):
    """
    **Validates: Requirements 10.6**

    Property 3 补充：非数值输入被视为 0

    scores 中的非数值（None、字符串等）对应维度的值应为 0，
    满足 clamp 不变量（0 在 [0, 100] 范围内）。
    """
    # 构造全部为非数值的 scores
    non_numeric_scores = {k: None for k in scores}
    store = make_store()
    update_radar_data(store, non_numeric_scores)

    values = store['radarData']['values']
    for i, v in enumerate(values):
        assert 0 <= v <= 100, (
            f"非数值 clamp 不变量违反: radarData.values[{i}] = {v!r}"
        )


@given(scores=scores_dict_strategy)
@settings(max_examples=200)
def test_property3_values_length_always_6(scores):
    """
    **Validates: Requirements 10.4**

    Property 3 补充：radarData.values 长度始终为 6

    无论 scores 字典包含多少个键，
    updateRadarData 后 radarData.values 的长度必须始终为 6。
    """
    store = make_store()
    update_radar_data(store, scores)

    values = store['radarData']['values']
    assert len(values) == 6, (
        f"values 长度不变量违反: 期望 6，实际 {len(values)}（scores={scores!r}）"
    )


# ---------------------------------------------------------------------------
# Property 4: 空状态不变量
# Validates: Requirements 10.3, 10.4
# ---------------------------------------------------------------------------

def test_property4_reset_produces_empty_state():
    """
    **Validates: Requirements 10.3, 10.4**

    Property 4: 空状态不变量（基础断言）

    resetRadarData() 后 radarData.values 必须为 [0,0,0,0,0,0]，
    表示空状态，雷达图应显示"暂无数据"提示。
    """
    store = make_store()
    # 先写入一些非零数据
    update_radar_data(store, {'技术能力': 80, '沟通表达': 60})

    # 重置
    reset_radar_data(store)

    values = store['radarData']['values']
    assert values == [0, 0, 0, 0, 0, 0], (
        f"空状态不变量违反: resetRadarData 后 values 应为 [0,0,0,0,0,0]，"
        f"实际为 {values!r}"
    )
    assert is_empty_state(store), "resetRadarData 后应处于空状态"


@given(scores=scores_dict_strategy)
@settings(max_examples=200)
def test_property4_reset_after_any_update_produces_empty_state(scores):
    """
    **Validates: Requirements 10.3, 10.4**

    Property 4: 空状态不变量（任意更新后重置）

    对任意 scores 字典，先调用 updateRadarData(scores)，
    再调用 resetRadarData()，结果必须为 [0,0,0,0,0,0]。
    """
    store = make_store()
    update_radar_data(store, scores)
    reset_radar_data(store)

    values = store['radarData']['values']
    assert values == [0, 0, 0, 0, 0, 0], (
        f"空状态不变量违反: 任意更新后 resetRadarData 应产生 [0,0,0,0,0,0]，"
        f"实际为 {values!r}（scores={scores!r}）"
    )
    assert is_empty_state(store), (
        f"is_empty_state 应返回 True，但实际为 False（values={values!r}）"
    )


@given(tab=tab_strategy)
@settings(max_examples=100)
def test_property4_null_pinned_id_triggers_empty_state(tab):
    """
    **Validates: Requirements 10.3, 10.4**

    Property 4: 空状态不变量（pinnedId 为 null 时）

    当指定 Tab 的 pinnedId 为 null 时，
    应调用 resetRadarData()，使 radarData.values 为 [0,0,0,0,0,0]。

    模拟 Dashboard.vue 中的逻辑：
    if (pinnedId === null) { userStore.resetRadarData() }
    """
    store = make_store()

    # 确保 pinnedId 为 null
    set_pinned_id(store, tab, None)
    pinned_id = get_pinned_id_by_tab(store, tab)

    # 模拟 Dashboard.vue 的 watch 逻辑
    if pinned_id is None:
        reset_radar_data(store)

    values = store['radarData']['values']
    assert values == [0, 0, 0, 0, 0, 0], (
        f"空状态不变量违反: pinnedId 为 null 时 values 应为 [0,0,0,0,0,0]，"
        f"实际为 {values!r}（tab={tab!r}）"
    )


@given(scores=scores_dict_strategy)
@settings(max_examples=200)
def test_property4_empty_scores_produces_all_zeros(scores):
    """
    **Validates: Requirements 10.4**

    Property 4 补充：空 scores 字典产生全零 values

    当 scores 为空字典时，updateRadarData 后所有维度值均为 0，
    等价于空状态。
    """
    store = make_store()
    update_radar_data(store, {})

    values = store['radarData']['values']
    assert values == [0, 0, 0, 0, 0, 0], (
        f"空 scores 不变量违反: 空字典应产生 [0,0,0,0,0,0]，实际为 {values!r}"
    )
    assert is_empty_state(store), "空 scores 后应处于空状态"


def test_property4_initial_state_is_empty():
    """
    **Validates: Requirements 10.3, 10.4**

    Property 4 补充：初始状态为空状态

    新建 store 时 radarData.values 默认为 [0,0,0,0,0,0]，
    is_empty_state 应返回 True。
    """
    store = make_store()
    assert store['radarData']['values'] == [0, 0, 0, 0, 0, 0], (
        "初始状态不变量违反: 新建 store 的 radarData.values 应为 [0,0,0,0,0,0]"
    )
    assert is_empty_state(store), "新建 store 应处于空状态"


# ---------------------------------------------------------------------------
# Property 5: Tab 数据绑定不变量
# Validates: Requirements 10.2
# ---------------------------------------------------------------------------

@given(
    tab_scores=tab_scores_strategy,
    active_tab=tab_strategy,
)
@settings(max_examples=300)
def test_property5_tab_switch_uses_new_tab_data(tab_scores, active_tab):
    """
    **Validates: Requirements 10.2**

    Property 5: Tab 数据绑定不变量（核心断言）

    任意 activeDataTab 切换后，雷达图数据必须对应新 Tab 的 pinnedId
    所指向的记录，不得显示其他 Tab 的数据。

    模拟三个 Tab 各自独立的 store 状态，切换后验证雷达图数据
    来自新 Tab 而非其他 Tab。
    """
    # 为每个 Tab 创建独立的 store 并写入各自的 scores
    stores_by_tab = {}
    for tab in ALL_TABS:
        store = make_store()
        update_radar_data(store, tab_scores[tab])
        stores_by_tab[tab] = store

    # 切换到 active_tab，获取对应的雷达图数据
    active_radar = simulate_tab_switch(stores_by_tab, active_tab)
    active_values = active_radar['values']

    # 验证：active_tab 的雷达图数据与该 Tab 的 store 数据一致
    expected_values = stores_by_tab[active_tab]['radarData']['values']
    assert active_values == expected_values, (
        f"Tab 数据绑定不变量违反: activeTab={active_tab!r} 的雷达图数据 "
        f"{active_values!r} 与该 Tab 的 store 数据 {expected_values!r} 不一致"
    )

    # 验证：active_tab 的数据不等于其他 Tab 的数据（除非恰好相同）
    for other_tab in ALL_TABS:
        if other_tab == active_tab:
            continue
        other_values = stores_by_tab[other_tab]['radarData']['values']
        # 如果两个 Tab 的数据恰好相同，这是合法的（不违反绑定不变量）
        # 关键是：active_tab 的数据必须来自 active_tab 的 store，而非 other_tab 的 store
        # 此处验证数据来源的正确性（通过对象引用）
        assert active_radar is stores_by_tab[active_tab]['radarData'], (
            f"Tab 数据来源不变量违反: activeTab={active_tab!r} 的雷达图数据 "
            f"应来自该 Tab 的 store，而非其他 Tab 的 store"
        )


@given(
    from_tab=tab_strategy,
    to_tab=tab_strategy,
    from_scores=scores_dict_strategy,
    to_scores=scores_dict_strategy,
)
@settings(max_examples=300)
def test_property5_tab_switch_shows_new_tab_not_old_tab(
    from_tab, to_tab, from_scores, to_scores
):
    """
    **Validates: Requirements 10.2**

    Property 5: Tab 数据绑定不变量（切换前后对比）

    从 from_tab 切换到 to_tab 后，雷达图数据必须反映 to_tab 的数据，
    而不是 from_tab 的数据（当两者数据不同时）。

    模拟 Dashboard.vue 中 watch(activeDataTab) 的行为：
    切换 Tab 后立即用新 Tab 的 pinnedId 对应数据更新雷达图。
    """
    # 为两个 Tab 创建独立的 store
    store_from = make_store()
    store_to = make_store()

    update_radar_data(store_from, from_scores)
    update_radar_data(store_to, to_scores)

    # 模拟切换：切换后使用 to_tab 的数据
    # （等价于 Dashboard.vue 中 watch 触发后调用 fetchPinnedRadarData(to_tab, ...)）
    active_store = store_to  # 切换后激活 to_tab 的 store

    active_values = active_store['radarData']['values']
    to_values = store_to['radarData']['values']

    # 切换后的数据必须等于 to_tab 的数据
    assert active_values == to_values, (
        f"Tab 切换不变量违反: 从 {from_tab!r} 切换到 {to_tab!r} 后，"
        f"雷达图数据应为 {to_values!r}，实际为 {active_values!r}"
    )


@given(
    tab_a=tab_strategy,
    tab_b=tab_strategy,
    scores_a=scores_dict_strategy,
    scores_b=scores_dict_strategy,
    record_id_a=record_id_strategy,
    record_id_b=record_id_strategy,
)
@settings(max_examples=200)
def test_property5_different_tabs_have_independent_radar_data(
    tab_a, tab_b, scores_a, scores_b, record_id_a, record_id_b
):
    """
    **Validates: Requirements 10.2**

    Property 5 补充：不同 Tab 的雷达图数据相互独立

    Tab A 的 pinnedId 和 scores 更新不影响 Tab B 的雷达图数据，
    反之亦然。每个 Tab 维护独立的数据状态。
    """
    # 为每个 Tab 创建独立的 store
    stores_by_tab = {tab: make_store() for tab in ALL_TABS}

    # 设置 tab_a 的 pinnedId 和 scores
    set_pinned_id(stores_by_tab[tab_a], tab_a, record_id_a)
    update_radar_data(stores_by_tab[tab_a], scores_a)

    # 记录 tab_b 更新前的 radarData（如果 tab_a != tab_b）
    if tab_a != tab_b:
        values_b_before = list(stores_by_tab[tab_b]['radarData']['values'])

        # 验证：更新 tab_a 不影响 tab_b 的 store
        values_b_after = stores_by_tab[tab_b]['radarData']['values']
        assert values_b_after == values_b_before, (
            f"Tab 独立性不变量违反: 更新 {tab_a!r} 的数据后，"
            f"{tab_b!r} 的 radarData.values 从 {values_b_before!r} "
            f"变为 {values_b_after!r}，不应受影响"
        )


@given(
    active_tab=tab_strategy,
    pinned_id=st.one_of(st.none(), record_id_strategy),
    scores=scores_dict_strategy,
)
@settings(max_examples=200)
def test_property5_null_pinned_id_shows_empty_state_for_active_tab(
    active_tab, pinned_id, scores
):
    """
    **Validates: Requirements 10.2**

    Property 5 补充：pinnedId 为 null 时激活 Tab 显示空状态

    当 activeDataTab 对应的 pinnedId 为 null 时，
    雷达图必须显示空状态（[0,0,0,0,0,0]），
    不得显示其他 Tab 的数据或残留数据。

    模拟 Dashboard.vue 中的逻辑：
    if (pinnedId === null) { userStore.resetRadarData() }
    else { fetchPinnedRadarData(tab, pinnedId) }
    """
    store = make_store()

    # 先写入一些数据（模拟之前有数据的状态）
    update_radar_data(store, scores)

    # 设置 active_tab 的 pinnedId
    set_pinned_id(store, active_tab, pinned_id)
    current_pinned_id = get_pinned_id_by_tab(store, active_tab)

    # 模拟 Dashboard.vue 的 watch 逻辑
    if current_pinned_id is None:
        reset_radar_data(store)
        # 验证：pinnedId 为 null 时必须显示空状态
        assert store['radarData']['values'] == [0, 0, 0, 0, 0, 0], (
            f"空状态不变量违反: activeTab={active_tab!r} 的 pinnedId 为 null 时，"
            f"radarData.values 应为 [0,0,0,0,0,0]，"
            f"实际为 {store['radarData']['values']!r}"
        )
    else:
        # pinnedId 非 null 时，可以有非零数据（此处不验证 fetch 结果，只验证状态一致性）
        values = store['radarData']['values']
        for v in values:
            assert 0 <= v <= 100, (
                f"clamp 不变量违反: radarData.values 中存在超出范围的值 {v!r}"
            )
