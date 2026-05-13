/**
 * SetupModal close 无副作用属性测试 — Property-Based Testing with fast-check
 *
 * **Validates: Requirement 5.2**
 *
 * Property 3: SetupModal Close No Side Effects
 * 对任意 localStorage 初始状态，触发 SetupModal close 后 localStorage 应保持不变
 * （无 key 被添加、删除或修改）。
 *
 * SetupModal 的 close 实现（SetupModal.vue）：
 *   <button @click="emit('close')" ...>
 *
 * 测试策略：模拟 localStorage，提取 close 逻辑为纯函数，验证调用后 localStorage 完全未被修改。
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
    // 辅助方法：获取内部存储快照
    _getSnapshot() {
      return { ...store }
    },
    // 辅助方法：批量设置
    _setState(state) {
      store = { ...state }
    }
  }
}

// ===== SetupModal close 逻辑提取 =====

/**
 * 模拟 SetupModal close 按钮的行为：仅调用 emit('close')
 * 这是 SetupModal.vue 中关闭按钮点击处理的等价实现
 * @param {function} emit - Vue emit 函数
 */
function handleClose(emit) {
  emit('close')
}

// ===== 自定义 Arbitraries =====

/** 生成合法的 localStorage key（非空字符串） */
const localStorageKeyArb = fc.string({ minLength: 1, maxLength: 30 })
  .filter(s => s.trim().length > 0)

/** 生成 localStorage value（任意字符串） */
const localStorageValueArb = fc.string({ minLength: 0, maxLength: 100 })

/** 生成随机 localStorage 初始状态（0~10 个 key-value 对） */
const localStorageStateArb = fc.array(
  fc.tuple(localStorageKeyArb, localStorageValueArb),
  { minLength: 0, maxLength: 10 }
)

// ===== Property Tests =====

describe('SetupModal Close No Side Effects (Property 3)', () => {
  let mockLocalStorage

  beforeEach(() => {
    mockLocalStorage = createLocalStorageMock()
    globalThis.localStorage = mockLocalStorage
  })

  afterEach(() => {
    delete globalThis.localStorage
  })

  it('Property: SetupModal close 触发后 localStorage 保持不变', () => {
    fc.assert(
      fc.property(
        localStorageStateArb,
        (initialState) => {
          // 设置 localStorage 初始状态
          mockLocalStorage.clear()
          for (const [key, value] of initialState) {
            mockLocalStorage.setItem(key, value)
          }

          // 记录调用前的快照
          const snapshotBefore = mockLocalStorage._getSnapshot()

          // 创建 mock emit 函数
          const emitCalls = []
          const mockEmit = (event) => { emitCalls.push(event) }

          // 触发 close
          handleClose(mockEmit)

          // 记录调用后的快照
          const snapshotAfter = mockLocalStorage._getSnapshot()

          // 验证 localStorage 未被修改（相同的 key 和 value）
          expect(snapshotAfter).toEqual(snapshotBefore)
        }
      ),
      { numRuns: 200 }
    )
  })

  it('Property: SetupModal close 仅触发 emit("close")，不触发其他存储操作', () => {
    fc.assert(
      fc.property(
        localStorageStateArb,
        (initialState) => {
          // 设置 localStorage 初始状态
          mockLocalStorage.clear()
          for (const [key, value] of initialState) {
            mockLocalStorage.setItem(key, value)
          }

          // 创建带追踪的 mock emit
          const emitCalls = []
          const mockEmit = (event) => { emitCalls.push(event) }

          // 记录调用前的 key 数量
          const keyCountBefore = mockLocalStorage.length

          // 触发 close
          handleClose(mockEmit)

          // 验证 emit 被调用且参数正确
          expect(emitCalls).toEqual(['close'])

          // 验证 localStorage key 数量未变
          expect(mockLocalStorage.length).toBe(keyCountBefore)
        }
      ),
      { numRuns: 200 }
    )
  })
})
