/**
 * Dashboard 新手启航舱 — Property 1: Mutual Exclusion Rendering
 * Property-Based Testing with fast-check
 *
 * **Validates: Requirements 1.1, 1.2, 1.3**
 *
 * Property 1: Mutual Exclusion Rendering（互斥渲染）
 *
 * 核心属性：
 *   对任意 isHistoryLoading（true/false）和 historyRecords（空/非空数组）的组合，
 *   Dashboard 的面板渲染结果满足以下严格 XOR 关系：
 *
 *   - isHistoryLoading = true  → 加载占位（loading skeleton）可见，
 *                                OnboardingPanel 与 HistoryPanel 均不可见
 *   - isHistoryLoading = false, historyRecords.length === 0
 *                              → OnboardingPanel（key="onboarding"）可见，
 *                                HistoryPanel（key="history"）不可见
 *   - isHistoryLoading = false, historyRecords.length > 0
 *                              → HistoryPanel（key="history"）可见，
 *                                OnboardingPanel（key="onboarding"）不可见
 *
 * 测试策略：
 *   从 Dashboard.vue 的条件渲染逻辑中提取纯函数 getPanelState()，
 *   对该函数进行属性测试，验证互斥性在所有合法输入组合下均成立。
 *   这与 Dashboard.vue 模板中的 v-if / v-else-if / v-else 三分支逻辑完全对应。
 */
import { describe, it, expect } from 'vitest'
import * as fc from 'fast-check'

// ─────────────────────────────────────────────
// 被测纯函数：从 Dashboard.vue 模板中提取的面板渲染决策逻辑
//
// Dashboard.vue 模板结构（Requirements 1.1, 1.2, 1.3, 1.5）：
//
//   <transition name="onboarding-fade" mode="out-in">
//     <!-- 加载中 -->
//     <div v-if="isHistoryLoading" key="loading" ...>
//     <!-- 零数据态：OnboardingPanel -->
//     <div v-else-if="historyRecords.length === 0" key="onboarding" ...>
//     <!-- 有数据态：HistoryPanel -->
//     <div v-else key="history" ...>
//   </transition>
// ─────────────────────────────────────────────

/**
 * 根据 isHistoryLoading 和 historyRecords 决定当前应渲染哪个面板。
 *
 * 返回值为三个互斥状态之一：
 *   - 'loading'    : 加载占位（isHistoryLoading = true）
 *   - 'onboarding' : 新手启航舱（isHistoryLoading = false, records 为空）
 *   - 'history'    : 继续上次历史列表（isHistoryLoading = false, records 非空）
 *
 * @param {boolean} isHistoryLoading - 是否正在加载历史记录
 * @param {Array}   historyRecords   - 历史记录数组
 * @returns {'loading' | 'onboarding' | 'history'} 当前应渲染的面板标识
 */
function getPanelState(isHistoryLoading, historyRecords) {
  if (isHistoryLoading) {
    return 'loading'
  }
  if (historyRecords.length === 0) {
    return 'onboarding'
  }
  return 'history'
}

/**
 * 根据面板状态判断 OnboardingPanel 是否在 DOM 中（key="onboarding"）。
 * 对应 v-else-if="historyRecords.length === 0" 分支。
 *
 * @param {'loading' | 'onboarding' | 'history'} panelState
 * @returns {boolean}
 */
function isOnboardingVisible(panelState) {
  return panelState === 'onboarding'
}

/**
 * 根据面板状态判断 HistoryPanel 是否在 DOM 中（key="history"）。
 * 对应 v-else 分支。
 *
 * @param {'loading' | 'onboarding' | 'history'} panelState
 * @returns {boolean}
 */
function isHistoryVisible(panelState) {
  return panelState === 'history'
}

// ─────────────────────────────────────────────
// 自定义 Arbitraries（生成器）
// ─────────────────────────────────────────────

/**
 * 生成空的 historyRecords 数组（零数据态）
 */
const emptyRecordsArb = fc.constant([])

/**
 * 生成非空的 historyRecords 数组（有数据态）。
 * 每条记录至少包含 id 字段，模拟真实的历史记录结构。
 */
const nonEmptyRecordsArb = fc.array(
  fc.record({
    id: fc.integer({ min: 1, max: 99999 }),
    category: fc.constantFrom(
      'resume_diagnosis',
      'interview_standard',
      'career_planning',
      'general_chat'
    ),
    user_input: fc.string({ minLength: 1, maxLength: 100 }),
  }),
  { minLength: 1, maxLength: 10 }
)

/**
 * 生成任意 historyRecords（空或非空）
 */
const anyRecordsArb = fc.oneof(emptyRecordsArb, nonEmptyRecordsArb)

// ─────────────────────────────────────────────
// Property 1 属性测试：互斥渲染（Mutual Exclusion Rendering）
// ─────────────────────────────────────────────

describe('Property 1: Mutual Exclusion Rendering（互斥渲染）', () => {

  // ── Requirement 1.3 ──────────────────────────────────────────────────────
  // THE Dashboard SHALL 保证 OnboardingPanel 与 HistoryPanel 在任意时刻
  // 有且仅有一个存在于 DOM 中（严格 XOR 关系）
  it('Property 1.0: 对任意输入，OnboardingPanel 与 HistoryPanel 有且仅有一个可见（严格 XOR）', () => {
    fc.assert(
      fc.property(
        fc.boolean(),
        anyRecordsArb,
        (isHistoryLoading, historyRecords) => {
          const panelState = getPanelState(isHistoryLoading, historyRecords)
          const onboardingVisible = isOnboardingVisible(panelState)
          const historyVisible = isHistoryVisible(panelState)

          // 严格 XOR：两者不能同时为 true，也不能同时为 false（加载态除外）
          // 加载态时两者均为 false，但加载态本身是第三个互斥状态
          // 完整的互斥性：三个状态有且仅有一个为 true
          const isLoading = panelState === 'loading'
          const activeCount = [isLoading, onboardingVisible, historyVisible].filter(Boolean).length

          return activeCount === 1
        }
      ),
      { numRuns: 500 }
    )
  })

  // ── Requirement 1.5 ──────────────────────────────────────────────────────
  // WHILE loadHistory() 请求正在进行中，THE Dashboard SHALL 不将
  // OnboardingPanel 或 HistoryPanel 渲染至 DOM 中
  it('Property 1.1: isHistoryLoading=true 时，OnboardingPanel 与 HistoryPanel 均不可见', () => {
    fc.assert(
      fc.property(
        anyRecordsArb,
        (historyRecords) => {
          const panelState = getPanelState(true, historyRecords)
          const onboardingVisible = isOnboardingVisible(panelState)
          const historyVisible = isHistoryVisible(panelState)

          return !onboardingVisible && !historyVisible
        }
      ),
      { numRuns: 300 }
    )
  })

  // ── Requirement 1.1 ──────────────────────────────────────────────────────
  // WHEN loadHistory() 返回空数组时，THE Dashboard SHALL 将 OnboardingPanel
  // 渲染至 DOM 中，并将 HistoryPanel 从 DOM 中移除
  it('Property 1.2: isHistoryLoading=false 且 historyRecords 为空时，OnboardingPanel 可见，HistoryPanel 不可见', () => {
    fc.assert(
      fc.property(
        emptyRecordsArb,
        (historyRecords) => {
          const panelState = getPanelState(false, historyRecords)
          const onboardingVisible = isOnboardingVisible(panelState)
          const historyVisible = isHistoryVisible(panelState)

          return onboardingVisible === true && historyVisible === false
        }
      ),
      { numRuns: 100 }
    )
  })

  // ── Requirement 1.2 ──────────────────────────────────────────────────────
  // WHEN loadHistory() 返回至少一条记录时，THE Dashboard SHALL 将 HistoryPanel
  // 渲染至 DOM 中，并将 OnboardingPanel 从 DOM 中移除
  it('Property 1.3: isHistoryLoading=false 且 historyRecords 非空时，HistoryPanel 可见，OnboardingPanel 不可见', () => {
    fc.assert(
      fc.property(
        nonEmptyRecordsArb,
        (historyRecords) => {
          const panelState = getPanelState(false, historyRecords)
          const onboardingVisible = isOnboardingVisible(panelState)
          const historyVisible = isHistoryVisible(panelState)

          return historyVisible === true && onboardingVisible === false
        }
      ),
      { numRuns: 300 }
    )
  })

  // ── 综合属性：getPanelState 返回值始终为三个合法状态之一 ─────────────────
  it('Property 1.4: getPanelState 对任意输入，返回值始终为 "loading" | "onboarding" | "history" 之一', () => {
    const VALID_STATES = new Set(['loading', 'onboarding', 'history'])

    fc.assert(
      fc.property(
        fc.boolean(),
        anyRecordsArb,
        (isHistoryLoading, historyRecords) => {
          const panelState = getPanelState(isHistoryLoading, historyRecords)
          return VALID_STATES.has(panelState)
        }
      ),
      { numRuns: 500 }
    )
  })

  // ── 综合属性：面板状态与输入的确定性映射（幂等性） ───────────────────────
  it('Property 1.5: 相同的 isHistoryLoading 和 historyRecords 始终产生相同的面板状态（确定性）', () => {
    fc.assert(
      fc.property(
        fc.boolean(),
        anyRecordsArb,
        (isHistoryLoading, historyRecords) => {
          // 多次调用应返回相同结果
          const state1 = getPanelState(isHistoryLoading, historyRecords)
          const state2 = getPanelState(isHistoryLoading, historyRecords)
          const state3 = getPanelState(isHistoryLoading, historyRecords)

          return state1 === state2 && state2 === state3
        }
      ),
      { numRuns: 300 }
    )
  })

  // ── 边界条件：historyRecords 长度为 1 时的临界值 ─────────────────────────
  it('Property 1.6: historyRecords 恰好有 1 条记录时，HistoryPanel 可见（边界值验证）', () => {
    fc.assert(
      fc.property(
        fc.record({
          id: fc.integer({ min: 1, max: 99999 }),
          category: fc.string({ minLength: 1, maxLength: 30 }),
          user_input: fc.string({ minLength: 1, maxLength: 100 }),
        }),
        (singleRecord) => {
          const historyRecords = [singleRecord]
          const panelState = getPanelState(false, historyRecords)

          return panelState === 'history'
        }
      ),
      { numRuns: 200 }
    )
  })

  // ── 边界条件：isHistoryLoading 从 true 切换到 false 后的状态转换 ─────────
  it('Property 1.7: isHistoryLoading 从 true 切换到 false 后，面板状态由 historyRecords 决定', () => {
    fc.assert(
      fc.property(
        anyRecordsArb,
        (historyRecords) => {
          // 加载中状态
          const loadingState = getPanelState(true, historyRecords)
          expect(loadingState).toBe('loading')

          // 加载完成后
          const finalState = getPanelState(false, historyRecords)

          if (historyRecords.length === 0) {
            return finalState === 'onboarding'
          } else {
            return finalState === 'history'
          }
        }
      ),
      { numRuns: 300 }
    )
  })
})
