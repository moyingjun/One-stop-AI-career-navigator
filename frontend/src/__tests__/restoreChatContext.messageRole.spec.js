/**
 * restoreChatContext 消息角色 属性测试 — Property-Based Testing with fast-check
 *
 * **Validates: Requirements 5.3**
 *
 * Property 2: Chat history role normalization
 * 对任意 chatHistory 数组，restoreChatContext 解析后每条消息的 role 仅为 'user' 或 'ai'
 *
 * 从 Dashboard.vue restoreChatContext 提取的角色规范化逻辑：
 *   chatMessages = chatHistory.map(msg => ({
 *     role: msg.role === 'user' ? 'user' : 'ai',
 *     content: msg.content || '',
 *     timestamp: record.created_at,
 *     isNew: false
 *   }))
 */
import { describe, it, expect } from 'vitest'
import * as fc from 'fast-check'

// ===== restoreChatContext 角色规范化逻辑提取 =====

/**
 * 从 Dashboard.vue restoreChatContext 提取的角色规范化纯逻辑
 * @param {Array} chatHistory - 任意 chatHistory 数组
 * @returns {Array} 规范化后的消息数组
 */
function normalizeMessages(chatHistory) {
  return chatHistory.map(msg => ({
    role: msg.role === 'user' ? 'user' : 'ai',
    content: msg.content || '',
    isNew: false
  }))
}

// ===== 自定义 Arbitraries =====

/**
 * 生成任意 chatHistory 消息对象
 * role 可以是各种值：'user', 'assistant', 'system', 'ai', null, undefined, 随机字符串
 * content 可以是字符串、null、undefined、空字符串
 */
const chatMessageArb = fc.record({
  role: fc.oneof(
    fc.constant('user'),
    fc.constant('assistant'),
    fc.constant('system'),
    fc.constant('ai'),
    fc.constant(null),
    fc.constant(undefined),
    fc.string()
  ),
  content: fc.oneof(fc.string(), fc.constant(null), fc.constant(undefined), fc.constant(''))
})

// ===== Property Tests =====

describe('restoreChatContext 消息角色 - Property Tests', () => {
  it('Property 2: 对任意 chatHistory 数组，解析后每条消息的 role 仅为 "user" 或 "ai"', () => {
    fc.assert(
      fc.property(
        fc.array(chatMessageArb, { minLength: 0, maxLength: 50 }),
        (chatHistory) => {
          const result = normalizeMessages(chatHistory)

          for (const msg of result) {
            expect(msg.role === 'user' || msg.role === 'ai').toBe(true)
          }
        }
      ),
      { numRuns: 1000 }
    )
  })

  it('Property: user role 保持为 user', () => {
    fc.assert(
      fc.property(
        fc.array(fc.record({ role: fc.constant('user'), content: fc.string() }), { minLength: 1, maxLength: 20 }),
        (chatHistory) => {
          const result = normalizeMessages(chatHistory)
          for (const msg of result) {
            expect(msg.role).toBe('user')
          }
        }
      ),
      { numRuns: 200 }
    )
  })

  it('Property: 非 user role 全部映射为 ai', () => {
    const nonUserRoleArb = fc.oneof(
      fc.constant('assistant'),
      fc.constant('system'),
      fc.constant('bot'),
      fc.constant(null),
      fc.constant(undefined),
      fc.string().filter(s => s !== 'user')
    )

    fc.assert(
      fc.property(
        fc.array(fc.record({ role: nonUserRoleArb, content: fc.string() }), { minLength: 1, maxLength: 20 }),
        (chatHistory) => {
          const result = normalizeMessages(chatHistory)
          for (const msg of result) {
            expect(msg.role).toBe('ai')
          }
        }
      ),
      { numRuns: 500 }
    )
  })
})
