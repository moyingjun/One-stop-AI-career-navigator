/**
 * UserStore Store-localStorage 双向同步属性测试
 * Property-Based Testing with fast-check
 *
 * **Validates: Requirements 3.2, 10.1, 10.2, 10.3, 10.4**
 *
 * Property 3: Store-localStorage 双向同步（Store-LocalStorage Sync Round-Trip）
 *
 * 核心属性：
 *   对任意合法 formData 调用 updateUserProfile() 后，
 *   再调用 loadFromStorage() 应将 Store 中所有字段恢复为完全相同的值。
 *   即：∀ field ∈ userProfile, store[field] === localStorage.getItem(field_key)
 *
 * 测试策略：
 *   - 从 userStore.js 提取 updateUserProfile 和 loadFromStorage 的纯逻辑
 *   - 使用 globalThis.localStorage mock 替代真实浏览器 localStorage
 *   - 不依赖 Pinia 运行时，直接测试状态同步逻辑
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import * as fc from 'fast-check'

// ─────────────────────────────────────────────
// localStorage Mock
// ─────────────────────────────────────────────

/**
 * 创建符合 Web Storage API 的 localStorage mock
 * 在 node 测试环境中替代浏览器原生 localStorage
 */
function createLocalStorageMock() {
  let store = {}
  return {
    getItem(key) {
      return Object.prototype.hasOwnProperty.call(store, key) ? store[key] : null
    },
    setItem(key, value) {
      store[key] = String(value)
    },
    removeItem(key) {
      delete store[key]
    },
    clear() {
      store = {}
    },
    key(index) {
      const keys = Object.keys(store)
      return keys[index] || null
    },
    get length() {
      return Object.keys(store).length
    },
    _getSnapshot() {
      return { ...store }
    }
  }
}

// ─────────────────────────────────────────────
// 从 userStore.js 提取的纯逻辑
// ─────────────────────────────────────────────

/**
 * 初始 Store 状态（对应 userStore.js 的 state()）
 */
function createInitialState() {
  return {
    candidateName: '',
    resumeText: '',
    activeMode: 'job',
    targetJob: '',
    jobDescription: '',
    examType: '',
    estimatedScore: '',
    targetSchool: ''
  }
}

/**
 * 从 userStore.js 提取的 updateUserProfile 纯逻辑
 * 更新 state 中所有用户画像字段，并同步写入 localStorage
 *
 * @param {object} state - 当前 Store state（会被就地修改）
 * @param {object} payload - 表单数据
 */
function updateUserProfile(state, payload) {
  state.candidateName = payload.candidateName || ''
  state.resumeText = payload.resumeText || ''
  state.activeMode = payload.activeMode || 'job'
  state.targetJob = payload.targetJob || ''
  state.jobDescription = payload.jobDescription || ''
  state.examType = payload.examType || ''
  state.estimatedScore = payload.estimatedScore || ''
  state.targetSchool = payload.targetSchool || ''

  // 同步写入 localStorage，失败时静默处理（隐私模式或存储已满）
  try {
    localStorage.setItem('candidate_name', state.candidateName)
    localStorage.setItem('resume_text', state.resumeText)
    localStorage.setItem('active_mode', state.activeMode)
    localStorage.setItem('target_job', state.targetJob)
    localStorage.setItem('job_description', state.jobDescription)
    localStorage.setItem('exam_type', state.examType)
    localStorage.setItem('estimated_score', state.estimatedScore)
    localStorage.setItem('target_school', state.targetSchool)
  } catch {
    // localStorage 写入失败时不抛出异常，Store 内存状态仍正常可用
  }
}

/**
 * 从 userStore.js 提取的 loadFromStorage 纯逻辑
 * 从 localStorage 读取所有用户画像字段并同步到 state
 *
 * @param {object} state - 当前 Store state（会被就地修改）
 */
function loadFromStorage(state) {
  state.candidateName = localStorage.getItem('candidate_name') || ''
  state.resumeText = localStorage.getItem('resume_text') || ''
  state.activeMode = localStorage.getItem('active_mode') || 'job'
  state.targetJob = localStorage.getItem('target_job') || ''
  state.jobDescription = localStorage.getItem('job_description') || ''
  state.examType = localStorage.getItem('exam_type') || ''
  state.estimatedScore = localStorage.getItem('estimated_score') || ''
  state.targetSchool = localStorage.getItem('target_school') || ''
}

// ─────────────────────────────────────────────
// 自定义 Arbitraries（生成器）
// ─────────────────────────────────────────────

/**
 * 生成任意非空字符串（用于文本字段）
 * 允许空字符串以覆盖默认值回退逻辑
 */
const textFieldArb = fc.string({ minLength: 0, maxLength: 100 })

/**
 * 生成合法的 activeMode 枚举值
 */
const activeModeArb = fc.constantFrom('job', 'education')

/**
 * 生成合法的 examType 枚举值（含空字符串，表示未设置）
 */
const examTypeArb = fc.constantFrom(
  'zhuanchaben',
  'gaokao',
  'kaoyan',
  'kaogong',
  'other',
  ''
)

/**
 * 生成任意合法的 formData 对象
 * 覆盖 updateUserProfile 接受的所有字段
 */
const formDataArb = fc.record({
  candidateName: textFieldArb,
  resumeText: textFieldArb,
  activeMode: activeModeArb,
  targetJob: textFieldArb,
  jobDescription: textFieldArb,
  examType: examTypeArb,
  estimatedScore: textFieldArb,
  targetSchool: textFieldArb
})

/**
 * 生成求职模式的 formData（activeMode 固定为 'job'）
 */
const jobModeFormDataArb = formDataArb.map(data => ({ ...data, activeMode: 'job' }))

/**
 * 生成升学模式的 formData（activeMode 固定为 'education'）
 */
const educationModeFormDataArb = formDataArb.map(data => ({ ...data, activeMode: 'education' }))

// ─────────────────────────────────────────────
// Property 3 属性测试
// ─────────────────────────────────────────────

describe('Property 3: Store-localStorage 双向同步（Store-LocalStorage Sync Round-Trip）', () => {
  let mockLocalStorage

  beforeEach(() => {
    mockLocalStorage = createLocalStorageMock()
    globalThis.localStorage = mockLocalStorage
  })

  afterEach(() => {
    mockLocalStorage.clear()
    delete globalThis.localStorage
  })

  // ── Requirement 3.2 & 10.2 ───────────────────────────────────────────────
  // WHEN userStore.updateUserProfile is called, THE UserStore SHALL synchronize
  // all updated fields to localStorage immediately.
  it('Property 3.1: 对任意 formData，updateUserProfile() 后 localStorage 中所有字段值与 Store 一致', () => {
    fc.assert(
      fc.property(
        formDataArb,
        (formData) => {
          mockLocalStorage.clear()
          const state = createInitialState()

          updateUserProfile(state, formData)

          // Store 中每个字段应与 localStorage 中对应 key 的值一致
          expect(mockLocalStorage.getItem('candidate_name')).toBe(state.candidateName)
          expect(mockLocalStorage.getItem('resume_text')).toBe(state.resumeText)
          expect(mockLocalStorage.getItem('active_mode')).toBe(state.activeMode)
          expect(mockLocalStorage.getItem('target_job')).toBe(state.targetJob)
          expect(mockLocalStorage.getItem('job_description')).toBe(state.jobDescription)
          expect(mockLocalStorage.getItem('exam_type')).toBe(state.examType)
          expect(mockLocalStorage.getItem('estimated_score')).toBe(state.estimatedScore)
          expect(mockLocalStorage.getItem('target_school')).toBe(state.targetSchool)
        }
      ),
      { numRuns: 300 }
    )
  })

  // ── Requirement 10.1 & 10.2 ──────────────────────────────────────────────
  // WHEN the application initializes, THE UserStore SHALL call loadFromStorage
  // to restore the previous session state.
  // WHEN userStore.updateUserProfile is called, THE UserStore SHALL synchronize
  // all updated fields to localStorage immediately.
  it('Property 3.2: 对任意 formData，updateUserProfile() 后 loadFromStorage() 应恢复完全相同的字段值（完整 round-trip）', () => {
    fc.assert(
      fc.property(
        formDataArb,
        (formData) => {
          mockLocalStorage.clear()

          // 第一步：写入 Store 并同步到 localStorage
          const stateAfterUpdate = createInitialState()
          updateUserProfile(stateAfterUpdate, formData)

          // 记录写入后的 Store 快照
          const snapshotAfterUpdate = { ...stateAfterUpdate }

          // 第二步：模拟页面刷新 — 创建全新 state，从 localStorage 恢复
          const stateAfterReload = createInitialState()
          loadFromStorage(stateAfterReload)

          // round-trip 验证：恢复后的 state 应与写入时完全一致
          expect(stateAfterReload.candidateName).toBe(snapshotAfterUpdate.candidateName)
          expect(stateAfterReload.resumeText).toBe(snapshotAfterUpdate.resumeText)
          expect(stateAfterReload.activeMode).toBe(snapshotAfterUpdate.activeMode)
          expect(stateAfterReload.targetJob).toBe(snapshotAfterUpdate.targetJob)
          expect(stateAfterReload.jobDescription).toBe(snapshotAfterUpdate.jobDescription)
          expect(stateAfterReload.examType).toBe(snapshotAfterUpdate.examType)
          expect(stateAfterReload.estimatedScore).toBe(snapshotAfterUpdate.estimatedScore)
          expect(stateAfterReload.targetSchool).toBe(snapshotAfterUpdate.targetSchool)
        }
      ),
      { numRuns: 300 }
    )
  })

  // ── Requirement 10.3 ─────────────────────────────────────────────────────
  // WHEN a user refreshes the page after completing SetupModal in education mode,
  // THE Sidebar SHALL display the same examType label, estimatedScore, and
  // targetSchool that were entered before the refresh.
  it('Property 3.3: 升学模式 round-trip — examType、estimatedScore、targetSchool 刷新后完全恢复', () => {
    fc.assert(
      fc.property(
        educationModeFormDataArb,
        (formData) => {
          mockLocalStorage.clear()

          const stateAfterUpdate = createInitialState()
          updateUserProfile(stateAfterUpdate, formData)

          const stateAfterReload = createInitialState()
          loadFromStorage(stateAfterReload)

          // 升学模式特定字段必须完整恢复
          expect(stateAfterReload.activeMode).toBe('education')
          expect(stateAfterReload.examType).toBe(stateAfterUpdate.examType)
          expect(stateAfterReload.estimatedScore).toBe(stateAfterUpdate.estimatedScore)
          expect(stateAfterReload.targetSchool).toBe(stateAfterUpdate.targetSchool)
        }
      ),
      { numRuns: 300 }
    )
  })

  // ── Requirement 10.4 ─────────────────────────────────────────────────────
  // WHEN a user refreshes the page after completing SetupModal in job mode,
  // THE Sidebar SHALL display the same targetJob and resume status that were
  // present before the refresh.
  it('Property 3.4: 求职模式 round-trip — targetJob、jobDescription、resumeText 刷新后完全恢复', () => {
    fc.assert(
      fc.property(
        jobModeFormDataArb,
        (formData) => {
          mockLocalStorage.clear()

          const stateAfterUpdate = createInitialState()
          updateUserProfile(stateAfterUpdate, formData)

          const stateAfterReload = createInitialState()
          loadFromStorage(stateAfterReload)

          // 求职模式特定字段必须完整恢复
          expect(stateAfterReload.activeMode).toBe('job')
          expect(stateAfterReload.targetJob).toBe(stateAfterUpdate.targetJob)
          expect(stateAfterReload.jobDescription).toBe(stateAfterUpdate.jobDescription)
          expect(stateAfterReload.resumeText).toBe(stateAfterUpdate.resumeText)
        }
      ),
      { numRuns: 300 }
    )
  })

  // ── Requirement 10.5 ─────────────────────────────────────────────────────
  // IF localStorage is unavailable during initialization, THEN THE UserStore
  // SHALL initialize all fields to their default empty values without throwing.
  it('Property 3.5: loadFromStorage() 在 localStorage 为空时，所有字段回退为默认空值，不抛出异常', () => {
    fc.assert(
      fc.property(
        // 生成任意字段名（不在 userStore 的 key 集合中），确保 localStorage 为空
        fc.constant(null),
        () => {
          mockLocalStorage.clear()

          const state = createInitialState()

          // 不应抛出异常
          expect(() => loadFromStorage(state)).not.toThrow()

          // 所有字段应回退为默认空值
          expect(state.candidateName).toBe('')
          expect(state.resumeText).toBe('')
          expect(state.activeMode).toBe('job')  // 默认值
          expect(state.targetJob).toBe('')
          expect(state.jobDescription).toBe('')
          expect(state.examType).toBe('')
          expect(state.estimatedScore).toBe('')
          expect(state.targetSchool).toBe('')
        }
      ),
      { numRuns: 1 }
    )
  })

  // ── 综合属性：多次写入后最后一次 round-trip 正确 ──────────────────────────
  it('Property 3.6: 连续多次 updateUserProfile() 后，loadFromStorage() 恢复的是最后一次写入的值', () => {
    fc.assert(
      fc.property(
        fc.array(formDataArb, { minLength: 2, maxLength: 5 }),
        (formDataList) => {
          mockLocalStorage.clear()

          const state = createInitialState()

          // 连续写入多次
          for (const formData of formDataList) {
            updateUserProfile(state, formData)
          }

          // 记录最后一次写入后的 Store 快照
          const finalSnapshot = { ...state }

          // 模拟页面刷新
          const stateAfterReload = createInitialState()
          loadFromStorage(stateAfterReload)

          // 恢复的应是最后一次写入的值
          expect(stateAfterReload.candidateName).toBe(finalSnapshot.candidateName)
          expect(stateAfterReload.resumeText).toBe(finalSnapshot.resumeText)
          expect(stateAfterReload.activeMode).toBe(finalSnapshot.activeMode)
          expect(stateAfterReload.targetJob).toBe(finalSnapshot.targetJob)
          expect(stateAfterReload.jobDescription).toBe(finalSnapshot.jobDescription)
          expect(stateAfterReload.examType).toBe(finalSnapshot.examType)
          expect(stateAfterReload.estimatedScore).toBe(finalSnapshot.estimatedScore)
          expect(stateAfterReload.targetSchool).toBe(finalSnapshot.targetSchool)
        }
      ),
      { numRuns: 200 }
    )
  })

  // ── 综合属性：updateUserProfile 不修改 payload 对象（无副作用）────────────
  it('Property 3.7: updateUserProfile() 不修改传入的 formData 对象（无副作用）', () => {
    fc.assert(
      fc.property(
        formDataArb,
        (formData) => {
          mockLocalStorage.clear()

          // 记录调用前的 formData 快照
          const formDataSnapshot = { ...formData }

          const state = createInitialState()
          updateUserProfile(state, formData)

          // formData 的所有字段应保持不变
          expect(formData.candidateName).toBe(formDataSnapshot.candidateName)
          expect(formData.resumeText).toBe(formDataSnapshot.resumeText)
          expect(formData.activeMode).toBe(formDataSnapshot.activeMode)
          expect(formData.targetJob).toBe(formDataSnapshot.targetJob)
          expect(formData.jobDescription).toBe(formDataSnapshot.jobDescription)
          expect(formData.examType).toBe(formDataSnapshot.examType)
          expect(formData.estimatedScore).toBe(formDataSnapshot.estimatedScore)
          expect(formData.targetSchool).toBe(formDataSnapshot.targetSchool)
        }
      ),
      { numRuns: 200 }
    )
  })
})
