/**
 * SetupModal 无效输入拒绝属性测试 — Property-Based Testing with fast-check
 *
 * **Validates: Requirements 5.7, 5.8**
 *
 * Property 5: SetupModal Invalid Input Rejection
 * 对任意不满足条件的输入（空姓名、姓名超过50字符、或简历 < 20 字符），
 * 提交后 localStorage 不应被修改，且不应触发 complete 事件。
 *
 * 验证规则：
 *   - candidateName.trim() 为空 → 拒绝提交
 *   - candidateName.trim().length > 50 → 拒绝提交
 *   - resumeText.trim().length < 20 → 拒绝提交
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import * as fc from 'fast-check'
import { handleSetupSubmit } from '../components/setupModalLogic.js'

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

// ===== 自定义 Arbitraries =====

/** 生成合法的 localStorage key（非空字符串） */
const localStorageKeyArb = fc.string({ minLength: 1, maxLength: 30 })
  .filter(s => s.trim().length > 0)

/** 生成 localStorage value（任意字符串） */
const localStorageValueArb = fc.string({ minLength: 0, maxLength: 100 })

/** 生成随机 localStorage 初始状态（0~8 个 key-value 对） */
const localStorageStateArb = fc.array(
  fc.tuple(localStorageKeyArb, localStorageValueArb),
  { minLength: 0, maxLength: 8 }
)

/**
 * Case A: 生成 trim 后为空的姓名（空字符串或纯空白字符串）
 */
const emptyNameArb = fc.oneof(
  fc.constant(''),
  fc.array(fc.constantFrom(' ', '\t', '\n', '\r', '\u3000'), { minLength: 1, maxLength: 20 })
    .map(chars => chars.join(''))
)

/**
 * Case B: 生成 trim 后长度 < 20 的简历文本
 * 包括空字符串、短字符串、带前后空白的短字符串
 */
const shortResumeArb = fc.oneof(
  fc.constant(''),
  // 纯空白字符串
  fc.array(fc.constantFrom(' ', '\t', '\n'), { minLength: 1, maxLength: 30 })
    .map(chars => chars.join('')),
  // trim 后长度在 1~19 之间的字符串
  fc.string({ minLength: 1, maxLength: 19 }).map(s => {
    const trimmed = s.trim()
    if (trimmed.length >= 20) {
      return trimmed.slice(0, 19)
    }
    return s
  }).filter(s => s.trim().length < 20)
)

/**
 * Case C: 生成 trim 后长度 > 50 的姓名
 */
const longNameArb = fc.string({ minLength: 51, maxLength: 80 })
  .filter(s => s.trim().length > 50)

/**
 * 生成有效的简历文本（trim 后 >= 20 字符），用于测试姓名无效的场景
 */
const validResumeArb = fc.string({ minLength: 20, maxLength: 200 })
  .filter(s => s.trim().length >= 20)

/**
 * 生成有效的姓名（trim 后非空且 <= 50 字符），用于测试简历无效的场景
 */
const validNameArb = fc.string({ minLength: 1, maxLength: 50 })
  .filter(s => s.trim().length > 0 && s.trim().length <= 50)

// ===== Property Tests =====

describe('SetupModal Invalid Input Rejection (Property 5)', () => {
  let mockLocalStorage

  beforeEach(() => {
    mockLocalStorage = createLocalStorageMock()
    globalThis.localStorage = mockLocalStorage
  })

  afterEach(() => {
    delete globalThis.localStorage
  })

  it('Property: 空姓名（trim 后为空）提交时 localStorage 不变且不触发 complete', () => {
    fc.assert(
      fc.property(
        localStorageStateArb,
        emptyNameArb,
        validResumeArb,
        (initialState, invalidName, validResume) => {
          // 设置 localStorage 初始状态
          mockLocalStorage.clear()
          for (const [key, value] of initialState) {
            mockLocalStorage.setItem(key, value)
          }

          // 记录调用前的快照
          const snapshotBefore = mockLocalStorage._getSnapshot()

          // 调用提交逻辑
          const result = handleSetupSubmit(invalidName, validResume)

          // 记录调用后的快照
          const snapshotAfter = mockLocalStorage._getSnapshot()

          // 验证 localStorage 未被修改
          expect(snapshotAfter).toEqual(snapshotBefore)

          // 验证未触发 complete 事件
          expect(result.emitted).toBeNull()
          expect(result.success).toBe(false)
        }
      ),
      { numRuns: 200 }
    )
  })

  it('Property: 姓名超过 50 字符提交时 localStorage 不变且不触发 complete', () => {
    fc.assert(
      fc.property(
        localStorageStateArb,
        longNameArb,
        validResumeArb,
        (initialState, longName, validResume) => {
          // 设置 localStorage 初始状态
          mockLocalStorage.clear()
          for (const [key, value] of initialState) {
            mockLocalStorage.setItem(key, value)
          }

          // 记录调用前的快照
          const snapshotBefore = mockLocalStorage._getSnapshot()

          // 调用提交逻辑
          const result = handleSetupSubmit(longName, validResume)

          // 记录调用后的快照
          const snapshotAfter = mockLocalStorage._getSnapshot()

          // 验证 localStorage 未被修改
          expect(snapshotAfter).toEqual(snapshotBefore)

          // 验证未触发 complete 事件
          expect(result.emitted).toBeNull()
          expect(result.success).toBe(false)
        }
      ),
      { numRuns: 200 }
    )
  })

  it('Property: 简历不足 20 字符提交时 localStorage 不变且不触发 complete', () => {
    fc.assert(
      fc.property(
        localStorageStateArb,
        validNameArb,
        shortResumeArb,
        (initialState, validName, shortResume) => {
          // 设置 localStorage 初始状态
          mockLocalStorage.clear()
          for (const [key, value] of initialState) {
            mockLocalStorage.setItem(key, value)
          }

          // 记录调用前的快照
          const snapshotBefore = mockLocalStorage._getSnapshot()

          // 调用提交逻辑
          const result = handleSetupSubmit(validName, shortResume)

          // 记录调用后的快照
          const snapshotAfter = mockLocalStorage._getSnapshot()

          // 验证 localStorage 未被修改
          expect(snapshotAfter).toEqual(snapshotBefore)

          // 验证未触发 complete 事件
          expect(result.emitted).toBeNull()
          expect(result.success).toBe(false)
        }
      ),
      { numRuns: 200 }
    )
  })

  it('Property: 任意无效输入组合（空姓名 + 短简历）提交时 localStorage 不变且不触发 complete', () => {
    fc.assert(
      fc.property(
        localStorageStateArb,
        emptyNameArb,
        shortResumeArb,
        (initialState, invalidName, shortResume) => {
          // 设置 localStorage 初始状态
          mockLocalStorage.clear()
          for (const [key, value] of initialState) {
            mockLocalStorage.setItem(key, value)
          }

          // 记录调用前的快照
          const snapshotBefore = mockLocalStorage._getSnapshot()

          // 调用提交逻辑
          const result = handleSetupSubmit(invalidName, shortResume)

          // 记录调用后的快照
          const snapshotAfter = mockLocalStorage._getSnapshot()

          // 验证 localStorage 未被修改
          expect(snapshotAfter).toEqual(snapshotBefore)

          // 验证未触发 complete 事件
          expect(result.emitted).toBeNull()
          expect(result.success).toBe(false)
        }
      ),
      { numRuns: 200 }
    )
  })
})
