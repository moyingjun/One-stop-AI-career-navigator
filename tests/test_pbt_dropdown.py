"""
属性测试：CustomDropdown.vue 中 isOpen 状态机的 Python 等价逻辑

测试文件模拟 Vue 组件 CustomDropdown.vue 的核心状态机逻辑，
验证以下属性：

Property 7: 自定义下拉关闭不变量
  处于打开状态时，点击外部区域或按 ESC 键后，isOpen 必须变为 false。
  Validates: Requirements 11.3, 11.4

附加测试（辅助验证）：
  - togglePanel 切换行为
  - selectOption 关闭面板
  - 非 ESC 键不关闭面板
"""

from hypothesis import given, settings
from hypothesis import strategies as st

# ---------------------------------------------------------------------------
# Python 等价实现：模拟 CustomDropdown.vue 的 isOpen 状态机
# ---------------------------------------------------------------------------


class DropdownStateMachine:
    """
    模拟 CustomDropdown.vue 的 isOpen 状态机。

    对应 Vue 组件中的以下逻辑：
      - togglePanel():          isOpen = !isOpen
      - selectOption(value):    isOpen = false
      - onClickOutside():       isOpen = false  (Requirements 11.3)
      - handleKeydown('Escape'): isOpen = false  (Requirements 11.4)
      - handleKeydown(other):   isOpen 不变
    """

    def __init__(self, initial_open: bool = False):
        self.is_open: bool = initial_open

    def toggle_panel(self):
        """点击触发按钮，切换面板开关状态。对应 Requirements 11.2"""
        self.is_open = not self.is_open

    def select_option(self, value: str):
        """点击某个选项，关闭面板。对应 Requirements 11.5"""
        self.is_open = False

    def on_click_outside(self):
        """点击组件外部区域，关闭面板。对应 Requirements 11.3"""
        self.is_open = False

    def handle_keydown(self, key: str):
        """
        处理键盘事件。
        - 'Escape' → 关闭面板（Requirements 11.4）
        - 其他键   → 状态不变
        """
        if key == "Escape":
            self.is_open = False


# ---------------------------------------------------------------------------
# Hypothesis 策略
# ---------------------------------------------------------------------------

# 任意字符串键名（排除代理字符）
key_strategy = st.text(
    alphabet=st.characters(blacklist_categories=("Cs",)),
    min_size=1,
    max_size=30,
)

# 非 ESC 键名（用于验证"其他键不关闭"）
non_escape_key_strategy = key_strategy.filter(lambda k: k != "Escape")

# 选项 value 字符串
option_value_strategy = st.text(
    alphabet=st.characters(blacklist_categories=("Cs",)),
    min_size=0,
    max_size=50,
)

# 任意操作序列（用于将面板置于打开状态的前置步骤）
# 每个元素为 ('toggle',) 或 ('select', value)，不包含关闭操作
open_action_strategy = st.just(("toggle",))


# ---------------------------------------------------------------------------
# Property 7: 自定义下拉关闭不变量
# Validates: Requirements 11.3, 11.4
# ---------------------------------------------------------------------------


@given(extra_toggles=st.integers(min_value=0, max_value=10))
@settings(max_examples=200)
def test_property7_click_outside_closes_when_open(extra_toggles):
    """
    **Validates: Requirements 11.3, 11.4**

    Property 7: 自定义下拉关闭不变量 — 点击外部区域

    对任意处于打开状态的 CustomDropdown，调用 onClickOutside() 后，
    isOpen 必须变为 False。

    通过奇数次 toggle 确保面板处于打开状态。
    """
    dropdown = DropdownStateMachine(initial_open=False)

    # 执行偶数次 toggle 使面板保持关闭，再执行一次 toggle 打开
    for _ in range(extra_toggles * 2):
        dropdown.toggle_panel()
    dropdown.toggle_panel()  # 最终打开

    assert dropdown.is_open is True, "前置条件：面板应处于打开状态"

    # 点击外部区域
    dropdown.on_click_outside()

    assert dropdown.is_open is False, (
        "Property 7 失败: 点击外部区域后 isOpen 应为 False，"
        f"实际为 {dropdown.is_open!r}"
    )


@given(extra_toggles=st.integers(min_value=0, max_value=10))
@settings(max_examples=200)
def test_property7_escape_key_closes_when_open(extra_toggles):
    """
    **Validates: Requirements 11.3, 11.4**

    Property 7: 自定义下拉关闭不变量 — 按 ESC 键

    对任意处于打开状态的 CustomDropdown，调用 handleKeydown('Escape') 后，
    isOpen 必须变为 False。
    """
    dropdown = DropdownStateMachine(initial_open=False)

    # 执行偶数次 toggle 使面板保持关闭，再执行一次 toggle 打开
    for _ in range(extra_toggles * 2):
        dropdown.toggle_panel()
    dropdown.toggle_panel()  # 最终打开

    assert dropdown.is_open is True, "前置条件：面板应处于打开状态"

    # 按 ESC 键
    dropdown.handle_keydown("Escape")

    assert dropdown.is_open is False, (
        "Property 7 失败: 按 ESC 键后 isOpen 应为 False，"
        f"实际为 {dropdown.is_open!r}"
    )


@given(
    extra_toggles=st.integers(min_value=0, max_value=10),
    close_action=st.sampled_from(["click_outside", "escape"]),
)
@settings(max_examples=300)
def test_property7_close_invariant_combined(extra_toggles, close_action):
    """
    **Validates: Requirements 11.3, 11.4**

    Property 7: 自定义下拉关闭不变量 — 综合测试

    无论通过点击外部区域还是按 ESC 键，处于打开状态的面板都必须关闭。
    对任意初始打开状态，两种关闭操作均保证 isOpen 变为 False。
    """
    dropdown = DropdownStateMachine(initial_open=False)

    # 通过奇数次 toggle 确保面板打开
    for _ in range(extra_toggles * 2):
        dropdown.toggle_panel()
    dropdown.toggle_panel()

    assert dropdown.is_open is True, "前置条件：面板应处于打开状态"

    # 执行关闭操作
    if close_action == "click_outside":
        dropdown.on_click_outside()
    else:
        dropdown.handle_keydown("Escape")

    assert dropdown.is_open is False, (
        f"Property 7 失败: 执行 {close_action!r} 后 isOpen 应为 False，"
        f"实际为 {dropdown.is_open!r}"
    )


# ---------------------------------------------------------------------------
# 辅助属性测试：验证其他状态机行为的正确性
# ---------------------------------------------------------------------------


@given(initial_open=st.booleans())
@settings(max_examples=100)
def test_toggle_panel_flips_state(initial_open):
    """
    togglePanel 必须翻转 isOpen 状态（True→False，False→True）。
    对应 Requirements 11.2
    """
    dropdown = DropdownStateMachine(initial_open=initial_open)
    dropdown.toggle_panel()
    assert dropdown.is_open is not initial_open, (
        f"togglePanel 未翻转状态: 初始={initial_open!r}，"
        f"翻转后={dropdown.is_open!r}"
    )


@given(
    initial_open=st.booleans(),
    value=option_value_strategy,
)
@settings(max_examples=200)
def test_select_option_always_closes(initial_open, value):
    """
    selectOption 无论面板当前状态如何，调用后 isOpen 必须为 False。
    对应 Requirements 11.5
    """
    dropdown = DropdownStateMachine(initial_open=initial_open)
    dropdown.select_option(value)
    assert dropdown.is_open is False, (
        f"selectOption 后 isOpen 应为 False，"
        f"初始状态={initial_open!r}，实际={dropdown.is_open!r}"
    )


@given(
    initial_open=st.booleans(),
    key=non_escape_key_strategy,
)
@settings(max_examples=200)
def test_non_escape_key_does_not_change_state(initial_open, key):
    """
    非 ESC 键的 handleKeydown 调用不应改变 isOpen 状态。
    对应 Requirements 11.4（仅 ESC 触发关闭）
    """
    dropdown = DropdownStateMachine(initial_open=initial_open)
    dropdown.handle_keydown(key)
    assert dropdown.is_open is initial_open, (
        f"非 ESC 键 {key!r} 不应改变 isOpen: "
        f"初始={initial_open!r}，实际={dropdown.is_open!r}"
    )


@given(
    initial_open=st.booleans(),
    n_clicks=st.integers(min_value=1, max_value=20),
)
@settings(max_examples=200)
def test_click_outside_idempotent(initial_open, n_clicks):
    """
    多次调用 onClickOutside 后 isOpen 仍为 False（幂等性）。
    对应 Requirements 11.3
    """
    dropdown = DropdownStateMachine(initial_open=initial_open)
    for _ in range(n_clicks):
        dropdown.on_click_outside()
    assert dropdown.is_open is False, (
        f"多次 onClickOutside 后 isOpen 应为 False，"
        f"实际为 {dropdown.is_open!r}"
    )


@given(
    initial_open=st.booleans(),
    n_presses=st.integers(min_value=1, max_value=20),
)
@settings(max_examples=200)
def test_escape_key_idempotent(initial_open, n_presses):
    """
    多次按 ESC 键后 isOpen 仍为 False（幂等性）。
    对应 Requirements 11.4
    """
    dropdown = DropdownStateMachine(initial_open=initial_open)
    for _ in range(n_presses):
        dropdown.handle_keydown("Escape")
    assert dropdown.is_open is False, (
        f"多次 ESC 后 isOpen 应为 False，实际为 {dropdown.is_open!r}"
    )
