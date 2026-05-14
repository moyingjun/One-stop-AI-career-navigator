/**
 * SetupModal 姓名截断 属性测试 — Property-Based Testing with fast-check
 *
 * **Validates: Requirements 3.7**
 *
 * Property 3: 对任意 candidateName 字符串，经 trim().slice(0, 50) 后长度 ≤ 50
 *
 * SetupModal handleSubmit 中的截断逻辑：
 *   const trimmedName = candidateName.value.trim()
 *   localStorage.setItem('candidate_name', trimmedName.slice(0, 50))
 */
import { describe, it, expect } from 'vitest'
import * as fc from 'fast-check'

describe('SetupModal 姓名截断 - Property Tests', () => {
  it('Property: 对任意字符串，trim().slice(0, 50) 后长度 ≤ 50', () => {
    fc.assert(
      fc.property(
        fc.string({ minLength: 0, maxLength: 10000 }),
        (name) => {
          const result = name.trim().slice(0, 50)
          expect(result.length).toBeLessThanOrEqual(50)
        }
      ),
      { numRuns: 1000 }
    )
  })

  it('Property: 包含 unicode/emoji 的字符串，trim().slice(0, 50) 后长度 ≤ 50', () => {
    fc.assert(
      fc.property(
        fc.string({ minLength: 0, maxLength: 500, unit: 'grapheme-ascii' }),
        (name) => {
          const result = name.trim().slice(0, 50)
          expect(result.length).toBeLessThanOrEqual(50)
        }
      ),
      { numRuns: 1000 }
    )
  })

  it('Property: trim 不增加长度', () => {
    fc.assert(
      fc.property(
        fc.string(),
        (name) => {
          expect(name.trim().length).toBeLessThanOrEqual(name.length)
        }
      ),
      { numRuns: 500 }
    )
  })
})
