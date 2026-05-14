/**
 * SetupModal 数据持久化和验证的单元测试 + 属性测试
 *
 * **Validates: Requirements 2.1, 2.2, 2.4, 2.5, 2.6**
 *
 * **Property 2: SetupModal 数据持久化 round-trip**
 * 对任意合法输入（name 1-50 chars, resume 20-10000 chars），
 * 写入 localStorage 后可正确读回完全相同的值。
 *
 * **Property 3: 表单验证拒绝无效输入**
 * 对任意非法输入（空姓名、姓名>50字符、简历<20字符、简历>10000字符），
 * localStorage 保持不变且提交被拒绝。
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import * as fc from 'fast-check'
import { handleSetupSubmit } from '../components/setupModalLogic.js'

// ===== localStorage Mock =====

/**
 * 创建符合 Web Storage API 的 localStorage mock
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

// ===== Unit Tests =====

describe('SetupModal 数据持久化 — 单元测试', () => {
  let mockLocalStorage

  beforeEach(() => {
    mockLocalStorage = createLocalStorageMock()
    globalThis.localStorage = mockLocalStorage
  })

  afterEach(() => {
    delete globalThis.localStorage
  })

  it('合法输入写入 localStorage 后可正确读回', () => {
    const name = '张三'
    const resume = '这是一段足够长的简历文本，用于测试数据持久化功能是否正常工作。'

    const result = handleSetupSubmit(name, resume)

    expect(result.success).toBe(true)
    expect(result.emitted).toBe('complete')
    expect(mockLocalStorage.getItem('candidate_name')).toBe(name)
    expect(mockLocalStorage.getItem('resume_text')).toBe(resume)
  })

  it('空姓名被拒绝且 localStorage 不变', () => {
    mockLocalStorage.setItem('existing_key', 'existing_value')
    const snapshotBefore = mockLocalStorage._getSnapshot()

    const result = handleSetupSubmit('', '这是一段足够长的简历文本，用于测试验证逻辑。')

    expect(result.success).toBe(false)
    expect(result.errors.nameError).toBeTruthy()
    expect(result.emitted).toBeNull()
    expect(mockLocalStorage._getSnapshot()).toEqual(snapshotBefore)
  })

  it('姓名超过 50 字符被拒绝', () => {
    const longName = 'A'.repeat(51)
    const validResume = '这是一段足够长的简历文本，用于测试姓名超长时的验证逻辑。'
    const snapshotBefore = mockLocalStorage._getSnapshot()

    const result = handleSetupSubmit(longName, validResume)

    expect(result.success).toBe(false)
    expect(result.errors.nameError).toBeTruthy()
    expect(result.emitted).toBeNull()
    expect(mockLocalStorage._getSnapshot()).toEqual(snapshotBefore)
  })

  it('简历少于 20 字符被拒绝', () => {
    const snapshotBefore = mockLocalStorage._getSnapshot()

    const result = handleSetupSubmit('张三', '太短了')

    expect(result.success).toBe(false)
    expect(result.errors.resumeError).toBeTruthy()
    expect(result.emitted).toBeNull()
    expect(mockLocalStorage._getSnapshot()).toEqual(snapshotBefore)
  })

  it('简历超过 10000 字符被拒绝', () => {
    const longResume = '字'.repeat(10001)
    const snapshotBefore = mockLocalStorage._getSnapshot()

    const result = handleSetupSubmit('张三', longResume)

    expect(result.success).toBe(false)
    expect(result.errors.resumeError).toBeTruthy()
    expect(result.emitted).toBeNull()
    expect(mockLocalStorage._getSnapshot()).toEqual(snapshotBefore)
  })
})

// ===== Property-Based Tests =====

// 自定义 Arbitraries

/**
 * 生成有效姓名：trim 后 1-50 字符
 */
const validNameArb = fc.string({ minLength: 1, maxLength: 50 })
  .filter(s => s.trim().length > 0 && s.trim().length <= 50)

/**
 * 生成有效简历：trim 后 20-10000 字符
 * 限制生成上限为 500 以保持测试性能
 */
const validResumeArb = fc.string({ minLength: 20, maxLength: 500 })
  .filter(s => s.trim().length >= 20 && s.length <= 10000)

/**
 * 生成无效姓名：空字符串、纯空白、或 trim 后超过 50 字符
 */
const invalidNameArb = fc.oneof(
  // 空字符串
  fc.constant(''),
  // 纯空白字符串
  fc.array(fc.constantFrom(' ', '\t', '\n', '\r'), { minLength: 1, maxLength: 10 })
    .map(chars => chars.join('')),
  // trim 后超过 50 字符
  fc.string({ minLength: 51, maxLength: 80 })
    .filter(s => s.trim().length > 50)
)

/**
 * 生成无效简历：trim 后少于 20 字符或超过 10000 字符
 */
const invalidResumeShortArb = fc.oneof(
  fc.constant(''),
  fc.string({ minLength: 1, maxLength: 19 })
    .filter(s => s.trim().length < 20)
)

const invalidResumeLongArb = fc.string({ minLength: 10001, maxLength: 10050 })

describe('Property 2: SetupModal 数据持久化 round-trip', () => {
  let mockLocalStorage

  beforeEach(() => {
    mockLocalStorage = createLocalStorageMock()
    globalThis.localStorage = mockLocalStorage
  })

  afterEach(() => {
    delete globalThis.localStorage
  })

  it('对任意合法输入，round-trip 通过 localStorage 保持数据不变', () => {
    fc.assert(
      fc.property(
        validNameArb,
        validResumeArb,
        (name, resume) => {
          mockLocalStorage.clear()

          const result = handleSetupSubmit(name, resume)

          // 提交成功
          expect(result.success).toBe(true)
          expect(result.emitted).toBe('complete')

          // round-trip: 读回的值与写入的值一致
          const storedName = mockLocalStorage.getItem('candidate_name')
          const storedResume = mockLocalStorage.getItem('resume_text')

          expect(storedName).toBe(name.trim().slice(0, 50))
          expect(storedResume).toBe(resume.trim().slice(0, 10000))

          // 验证读回的值非空
          expect(storedName.length).toBeGreaterThan(0)
          expect(storedResume.length).toBeGreaterThanOrEqual(20)
        }
      ),
      { numRuns: 300 }
    )
  })
})

describe('Property 3: 表单验证拒绝无效输入', () => {
  let mockLocalStorage

  beforeEach(() => {
    mockLocalStorage = createLocalStorageMock()
    globalThis.localStorage = mockLocalStorage
  })

  afterEach(() => {
    delete globalThis.localStorage
  })

  it('对任意无效姓名 + 合法简历，localStorage 保持不变', () => {
    fc.assert(
      fc.property(
        invalidNameArb,
        validResumeArb,
        (invalidName, validResume) => {
          mockLocalStorage.clear()
          mockLocalStorage.setItem('pre_existing', 'value')
          const snapshotBefore = mockLocalStorage._getSnapshot()

          const result = handleSetupSubmit(invalidName, validResume)

          expect(result.success).toBe(false)
          expect(result.emitted).toBeNull()
          expect(mockLocalStorage._getSnapshot()).toEqual(snapshotBefore)
        }
      ),
      { numRuns: 300 }
    )
  })

  it('对合法姓名 + 过短简历，localStorage 保持不变', () => {
    fc.assert(
      fc.property(
        validNameArb,
        invalidResumeShortArb,
        (validName, shortResume) => {
          mockLocalStorage.clear()
          mockLocalStorage.setItem('pre_existing', 'value')
          const snapshotBefore = mockLocalStorage._getSnapshot()

          const result = handleSetupSubmit(validName, shortResume)

          expect(result.success).toBe(false)
          expect(result.emitted).toBeNull()
          expect(mockLocalStorage._getSnapshot()).toEqual(snapshotBefore)
        }
      ),
      { numRuns: 300 }
    )
  })

  it('对合法姓名 + 过长简历，localStorage 保持不变', () => {
    fc.assert(
      fc.property(
        validNameArb,
        invalidResumeLongArb,
        (validName, longResume) => {
          mockLocalStorage.clear()
          mockLocalStorage.setItem('pre_existing', 'value')
          const snapshotBefore = mockLocalStorage._getSnapshot()

          const result = handleSetupSubmit(validName, longResume)

          expect(result.success).toBe(false)
          expect(result.emitted).toBeNull()
          expect(mockLocalStorage._getSnapshot()).toEqual(snapshotBefore)
        }
      ),
      { numRuns: 300 }
    )
  })
})
