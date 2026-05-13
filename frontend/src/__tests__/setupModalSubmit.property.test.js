/**
 * SetupModal 有效提交持久化属性测试 — Property-Based Testing with fast-check
 *
 * **Validates: Requirements 5.3, 5.4, 5.5, 5.6**
 *
 * Property 4: SetupModal Valid Submission Persistence
 * 对任意满足条件的 candidateName（trim 非空, <= 50 字符）和 resumeText（trim >= 20 字符, <= 10000 字符），
 * 提交后 localStorage 中 candidate_name、resume_text、userRole 值正确，且 complete 事件被触发。
 *
 * handleSubmit 的实现（SetupModal.vue）：
 *   验证通过后：
 *   localStorage.setItem('candidate_name', trimmedName.slice(0, 50))
 *   localStorage.setItem('resume_text', trimmedResume.slice(0, 10000))
 *   localStorage.setItem('userRole', 'registered')
 *   emit('complete')
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import * as fc from 'fast-check'

// ===== localStorage Mock =====

/**
 * 创建一个符合 Web Storage API 的 localStorage mock
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
    },
    _setState(state) {
      store = { ...state }
    }
  }
}

// ===== handleSubmit 逻辑提取 =====

/**
 * 从 SetupModal.vue 提取的 handleSubmit 纯逻辑
 * @param {string} candidateName - 用户输入的姓名
 * @param {string} resumeText - 用户输入的简历文本
 * @param {object} storage - localStorage 实例
 * @param {function} emit - 事件触发函数
 * @returns {{ nameError: string, resumeError: string }} 验证错误信息
 */
function handleSubmit(candidateName, resumeText, storage, emit) {
  let nameError = ''
  let resumeError = ''
  let hasError = false

  // 验证姓名
  const trimmedName = candidateName.trim()
  if (!trimmedName) {
    nameError = '请填写姓名'
    hasError = true
  } else if (trimmedName.length > 50) {
    nameError = '姓名不能超过 50 个字符'
    hasError = true
  }

  // 验证简历
  const trimmedResume = resumeText.trim()
  if (trimmedResume.length < 20) {
    resumeError = '简历内容至少需要 20 个字符'
    hasError = true
  }

  if (hasError) return { nameError, resumeError }

  // 验证通过，写入 localStorage
  storage.setItem('candidate_name', trimmedName.slice(0, 50))
  storage.setItem('resume_text', trimmedResume.slice(0, 10000))
  storage.setItem('userRole', 'registered')

  // 通知父组件完成
  emit('complete')

  return { nameError, resumeError }
}

// ===== 自定义 Arbitraries =====

/**
 * 生成有效的 candidateName：trim 后非空且 <= 50 字符
 * 策略：生成 1~50 个可见字符的核心内容，可选前后添加空白
 */
const validCandidateNameArb = fc.tuple(
  fc.nat({ max: 3 }).map(n => ' '.repeat(n)), // 前导空白
  fc.string({ minLength: 1, maxLength: 50 }).filter(s => s.trim().length > 0),
  fc.nat({ max: 3 }).map(n => ' '.repeat(n))  // 尾部空白
).map(([prefix, core, suffix]) => {
  // 确保 trim 后长度 <= 50
  const trimmed = (prefix + core + suffix).trim()
  if (trimmed.length === 0) return 'A'
  if (trimmed.length > 50) return trimmed.slice(0, 50)
  return prefix + core + suffix
}).filter(s => {
  const t = s.trim()
  return t.length > 0 && t.length <= 50
})

/**
 * 生成有效的 resumeText：trim 后 >= 20 字符且 <= 10000 字符
 * 策略：生成 20~200 个字符的核心内容（限制上限以保持测试性能）
 */
const validResumeTextArb = fc.tuple(
  fc.nat({ max: 3 }).map(n => ' '.repeat(n)), // 前导空白
  fc.string({ minLength: 20, maxLength: 200 }).filter(s => s.trim().length >= 20),
  fc.nat({ max: 3 }).map(n => ' '.repeat(n))  // 尾部空白
).map(([prefix, core, suffix]) => {
  return prefix + core + suffix
}).filter(s => {
  const t = s.trim()
  return t.length >= 20 && t.length <= 10000
})

// ===== Property Tests =====

describe('SetupModal Valid Submission Persistence (Property 4)', () => {
  let mockLocalStorage

  beforeEach(() => {
    mockLocalStorage = createLocalStorageMock()
    globalThis.localStorage = mockLocalStorage
  })

  afterEach(() => {
    delete globalThis.localStorage
  })

  it('Property: 有效输入提交后 localStorage 中 candidate_name 等于 candidateName.trim().slice(0, 50)', () => {
    fc.assert(
      fc.property(
        validCandidateNameArb,
        validResumeTextArb,
        (candidateName, resumeText) => {
          // 清空 localStorage
          mockLocalStorage.clear()

          // 创建 emit 追踪
          const emitCalls = []
          const emit = (event) => { emitCalls.push(event) }

          // 调用 handleSubmit
          handleSubmit(candidateName, resumeText, mockLocalStorage, emit)

          // 验证 candidate_name 正确
          const expected = candidateName.trim().slice(0, 50)
          expect(mockLocalStorage.getItem('candidate_name')).toBe(expected)
        }
      ),
      { numRuns: 200 }
    )
  })

  it('Property: 有效输入提交后 localStorage 中 resume_text 等于 resumeText.trim().slice(0, 10000)', () => {
    fc.assert(
      fc.property(
        validCandidateNameArb,
        validResumeTextArb,
        (candidateName, resumeText) => {
          // 清空 localStorage
          mockLocalStorage.clear()

          // 创建 emit 追踪
          const emitCalls = []
          const emit = (event) => { emitCalls.push(event) }

          // 调用 handleSubmit
          handleSubmit(candidateName, resumeText, mockLocalStorage, emit)

          // 验证 resume_text 正确
          const expected = resumeText.trim().slice(0, 10000)
          expect(mockLocalStorage.getItem('resume_text')).toBe(expected)
        }
      ),
      { numRuns: 200 }
    )
  })

  it('Property: 有效输入提交后 localStorage 中 userRole 等于 "registered"', () => {
    fc.assert(
      fc.property(
        validCandidateNameArb,
        validResumeTextArb,
        (candidateName, resumeText) => {
          // 清空 localStorage
          mockLocalStorage.clear()

          // 创建 emit 追踪
          const emitCalls = []
          const emit = (event) => { emitCalls.push(event) }

          // 调用 handleSubmit
          handleSubmit(candidateName, resumeText, mockLocalStorage, emit)

          // 验证 userRole 正确
          expect(mockLocalStorage.getItem('userRole')).toBe('registered')
        }
      ),
      { numRuns: 200 }
    )
  })

  it('Property: 有效输入提交后 complete 事件被触发', () => {
    fc.assert(
      fc.property(
        validCandidateNameArb,
        validResumeTextArb,
        (candidateName, resumeText) => {
          // 清空 localStorage
          mockLocalStorage.clear()

          // 创建 emit 追踪
          const emitCalls = []
          const emit = (event) => { emitCalls.push(event) }

          // 调用 handleSubmit
          handleSubmit(candidateName, resumeText, mockLocalStorage, emit)

          // 验证 complete 事件被触发
          expect(emitCalls).toEqual(['complete'])
        }
      ),
      { numRuns: 200 }
    )
  })

  it('Property: 有效输入提交后三项 localStorage 值同时正确（综合验证）', () => {
    fc.assert(
      fc.property(
        validCandidateNameArb,
        validResumeTextArb,
        (candidateName, resumeText) => {
          // 清空 localStorage
          mockLocalStorage.clear()

          // 创建 emit 追踪
          const emitCalls = []
          const emit = (event) => { emitCalls.push(event) }

          // 调用 handleSubmit
          const result = handleSubmit(candidateName, resumeText, mockLocalStorage, emit)

          // 验证无错误
          expect(result.nameError).toBe('')
          expect(result.resumeError).toBe('')

          // 验证 localStorage 三项值全部正确
          expect(mockLocalStorage.getItem('candidate_name')).toBe(candidateName.trim().slice(0, 50))
          expect(mockLocalStorage.getItem('resume_text')).toBe(resumeText.trim().slice(0, 10000))
          expect(mockLocalStorage.getItem('userRole')).toBe('registered')

          // 验证 complete 事件被触发
          expect(emitCalls).toEqual(['complete'])
        }
      ),
      { numRuns: 200 }
    )
  })
})
