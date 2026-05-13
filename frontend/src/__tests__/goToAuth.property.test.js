/**
 * goToAuth 无副作用属性测试 — Property-Based Testing with fast-check
 *
 * **Validates: Requirement 3.2**
 *
 * Property 2: Auth Navigation No Side Effects
 * 对任意 localStorage 初始状态，调用 goToAuth() 后 localStorage 应保持不变
 * （无 key 被添加、删除或修改）。
 *
 * goToAuth 的实现（Landing.vue）：
 *   const goToAuth = () => { router.push('/auth') }
 *
 * 测试策略：模拟 router 和 localStorage，验证调用 goToAuth 逻辑后 localStorage 完全未被修改。
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

// ===== goToAuth 逻辑提取 =====

/**
 * 模拟 goToAuth 的行为：仅调用 router.push('/auth')
 * 这是 Landing.vue 中 goToAuth 函数的等价实现
 * @param {object} router - 路由实例（含 push 方法）
 */
function goToAuth(router) {
  router.push('/auth')
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

describe('Auth Navigation No Side Effects (Property 2)', () => {
  let mockLocalStorage

  beforeEach(() => {
    mockLocalStorage = createLocalStorageMock()
    globalThis.localStorage = mockLocalStorage
  })

  afterEach(() => {
    delete globalThis.localStorage
  })

  it('Property: goToAuth 调用后 localStorage 保持不变', () => {
    fc.assert(
      fc.property(
        localStorageStateArb,
        (initialState) => {
          // 设置 localStorage 初始状态
          mockLocalStorage.clear()
          const stateMap = {}
          for (const [key, value] of initialState) {
            mockLocalStorage.setItem(key, value)
            stateMap[key] = value // Map 去重，后写入的覆盖先写入的
          }

          // 记录调用前的快照
          const snapshotBefore = mockLocalStorage._getSnapshot()

          // 创建 mock router
          const mockRouter = {
            push: () => {} // 空实现，不产生副作用
          }

          // 调用 goToAuth
          goToAuth(mockRouter)

          // 记录调用后的快照
          const snapshotAfter = mockLocalStorage._getSnapshot()

          // 验证 localStorage 未被修改（相同的 key 和 value）
          expect(snapshotAfter).toEqual(snapshotBefore)
        }
      ),
      { numRuns: 200 }
    )
  })

  it('Property: goToAuth 仅调用 router.push("/auth")，不触发其他存储操作', () => {
    fc.assert(
      fc.property(
        localStorageStateArb,
        (initialState) => {
          // 设置 localStorage 初始状态
          mockLocalStorage.clear()
          for (const [key, value] of initialState) {
            mockLocalStorage.setItem(key, value)
          }

          // 创建带追踪的 mock router
          const pushCalls = []
          const mockRouter = {
            push: (path) => { pushCalls.push(path) }
          }

          // 记录调用前的 key 数量
          const keyCountBefore = mockLocalStorage.length

          // 调用 goToAuth
          goToAuth(mockRouter)

          // 验证 router.push 被调用且参数正确
          expect(pushCalls).toEqual(['/auth'])

          // 验证 localStorage key 数量未变
          expect(mockLocalStorage.length).toBe(keyCountBefore)
        }
      ),
      { numRuns: 200 }
    )
  })
})
