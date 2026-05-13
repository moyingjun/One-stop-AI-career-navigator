/**
 * 路由守卫属性测试 — Property-Based Testing with fast-check
 *
 * **Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.6**
 *
 * Property 1: Router Guard Access Decision Correctness
 * 对任意 route 对象和任意 localStorage 状态（token 和 userRole 组合），
 * Router_Guard 应当在以下情况返回 true（放行）：
 *   (a) 路由 meta 中 requiresAuth 不为 true
 *   (b) localStorage 中存在非空非纯空白 token
 *   (c) localStorage 中 userRole 等于 'guest'
 * 其余情况返回 '/'（重定向）。
 */
import { describe, it, expect } from 'vitest'
import * as fc from 'fast-check'
import { routerGuardDecision } from '../router/guardLogic.js'

// ===== 自定义 Arbitraries =====

/** 生成 token 值：null、空字符串、纯空白字符串、有效非空白字符串 */
const tokenArb = fc.oneof(
  fc.constant(null),
  fc.constant(''),
  // 纯空白字符串（至少 1 个空白字符）
  fc.array(fc.constantFrom(' ', '\t', '\n', '\r'), { minLength: 1, maxLength: 10 }).map(arr => arr.join('')),
  // 有效 token：至少包含一个非空白字符
  fc.string({ minLength: 1, maxLength: 50 }).filter(s => s.trim().length > 0)
)

/** 生成 userRole 值：null、'guest'、'registered'、随机字符串 */
const userRoleArb = fc.oneof(
  fc.constant(null),
  fc.constant('guest'),
  fc.constant('registered'),
  fc.string({ minLength: 0, maxLength: 20 })
)

/** 生成 requiresAuth 值：true、false、undefined */
const requiresAuthArb = fc.oneof(
  fc.constant(true),
  fc.constant(false),
  fc.constant(undefined)
)

// ===== 辅助判断函数 =====

function isValidToken(token) {
  return token !== null && token !== undefined && token.trim().length > 0
}

function isGuestRole(userRole) {
  return userRole === 'guest'
}

// ===== Property Tests =====

describe('Router Guard Access Decision Correctness', () => {
  it('Property: requiresAuth 为 false/undefined 时始终放行', () => {
    fc.assert(
      fc.property(
        tokenArb,
        userRoleArb,
        fc.oneof(fc.constant(false), fc.constant(undefined)),
        (token, userRole, requiresAuth) => {
          const result = routerGuardDecision({ requiresAuth, token, userRole })
          expect(result).toBe(true)
        }
      ),
      { numRuns: 200 }
    )
  })

  it('Property: requiresAuth 为 true 且 token 有效时放行', () => {
    fc.assert(
      fc.property(
        // 有效 token：非 null 且 trim 后非空
        fc.string({ minLength: 1, maxLength: 50 }).filter(s => s.trim().length > 0),
        userRoleArb,
        (token, userRole) => {
          const result = routerGuardDecision({ requiresAuth: true, token, userRole })
          expect(result).toBe(true)
        }
      ),
      { numRuns: 200 }
    )
  })

  it('Property: requiresAuth 为 true 且 userRole 为 guest 时放行', () => {
    fc.assert(
      fc.property(
        tokenArb,
        (token) => {
          const result = routerGuardDecision({ requiresAuth: true, token, userRole: 'guest' })
          expect(result).toBe(true)
        }
      ),
      { numRuns: 200 }
    )
  })

  it('Property: requiresAuth 为 true 且 token 无效且 userRole 非 guest 时重定向至 /', () => {
    // 无效 token：null、空字符串、纯空白字符串
    const invalidTokenArb = fc.oneof(
      fc.constant(null),
      fc.constant(''),
      fc.array(fc.constantFrom(' ', '\t', '\n', '\r'), { minLength: 1, maxLength: 10 }).map(arr => arr.join(''))
    )

    // 非 guest 的 userRole
    const nonGuestRoleArb = fc.oneof(
      fc.constant(null),
      fc.constant('registered'),
      fc.string({ minLength: 0, maxLength: 20 }).filter(s => s !== 'guest')
    )

    fc.assert(
      fc.property(
        invalidTokenArb,
        nonGuestRoleArb,
        (token, userRole) => {
          const result = routerGuardDecision({ requiresAuth: true, token, userRole })
          expect(result).toBe('/')
        }
      ),
      { numRuns: 200 }
    )
  })

  it('Property: 完整决策正确性 — 对任意输入组合验证决策逻辑', () => {
    fc.assert(
      fc.property(
        requiresAuthArb,
        tokenArb,
        userRoleArb,
        (requiresAuth, token, userRole) => {
          const result = routerGuardDecision({ requiresAuth, token, userRole })

          if (!requiresAuth) {
            // 不需要认证 → 放行
            expect(result).toBe(true)
          } else if (isValidToken(token)) {
            // 有效 token → 放行
            expect(result).toBe(true)
          } else if (isGuestRole(userRole)) {
            // guest 角色 → 放行
            expect(result).toBe(true)
          } else {
            // 其余情况 → 重定向
            expect(result).toBe('/')
          }
        }
      ),
      { numRuns: 500 }
    )
  })
})
