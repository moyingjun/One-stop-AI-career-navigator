/**
 * hasValidScores 属性测试 — Property-Based Testing with fast-check
 *
 * **Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5**
 *
 * Property 8: hasValidScores 正确性（hasValidScores Correctness）
 *
 * 核心属性：
 *   - 对任意含至少一个正数值的 scores 对象，hasValidScores() 应返回 true
 *   - 对 null/undefined scores，hasValidScores() 应返回 false
 *   - 对空对象 scores，hasValidScores() 应返回 false
 *   - 对全零/全非数值 scores，hasValidScores() 应返回 false
 *   - 对不可解析的 JSON 字符串 scores，hasValidScores() 应返回 false
 *   - 对编码了含正数值对象的合法 JSON 字符串 scores，hasValidScores() 应返回 true
 */
import { describe, it } from 'vitest'
import * as fc from 'fast-check'
import { hasValidScores } from '../utils/dataSourceUtils.js'

// ─────────────────────────────────────────────
// 自定义 Arbitraries（生成器）
// ─────────────────────────────────────────────

/**
 * 生成一个至少含一个正数值的 scores 对象。
 * 策略：先生成 1~6 个键值对，其中至少一个值 > 0。
 *
 * 维度键名从真实业务维度中随机选取，也允许任意字符串键，
 * 以确保函数对任意键名均能正确处理。
 */
const dimensionKeys = ['技术能力', '沟通表达', '项目经验', '学习能力', '团队协作', '职业规划']

const dimensionKeyArb = fc.oneof(
  fc.constantFrom(...dimensionKeys),
  fc.string({ minLength: 1, maxLength: 20 })
)

/**
 * 生成含至少一个正数值的 scores 对象。
 * 保证：Object.values(scores).some(v => Number(v) > 0) === true
 * 使用 fc.integer 避免 fc.float 的 32-bit 约束问题。
 */
const scoresWithAtLeastOnePositiveArb = fc.record({
  positiveKey: dimensionKeyArb,
  positiveValue: fc.integer({ min: 1, max: 1000 }) // 正整数，确保 > 0
}).chain(({ positiveKey, positiveValue }) =>
  // 可选地追加若干额外键（值可以是零或负数）
  fc.array(
    fc.tuple(dimensionKeyArb, fc.oneof(fc.constant(0), fc.integer({ min: -100, max: -1 }))),
    { minLength: 0, maxLength: 5 }
  ).map(extras => {
    const scores = {}
    // 先写入额外的零/负值键
    for (const [k, v] of extras) {
      scores[k] = v
    }
    // 最后写入正数值键（确保至少一个正数值存在）
    scores[positiveKey] = positiveValue
    return scores
  })
)

/**
 * 生成全零或全非数值的 scores 对象（至少一个键，但无正数值）。
 * 保证：Object.values(scores).every(v => !(Number(v) > 0)) === true
 * 使用 fc.integer 避免 fc.float 的 32-bit 约束问题。
 */
const scoresAllZeroOrNonNumericArb = fc.array(
  fc.tuple(
    dimensionKeyArb,
    fc.oneof(
      fc.constant(0),
      fc.constant(''),
      fc.constant('abc'),
      fc.constant(null),
      fc.integer({ min: -1000, max: -1 }) // 负整数
    )
  ),
  { minLength: 1, maxLength: 6 }
).map(entries => {
  const scores = {}
  for (const [k, v] of entries) {
    scores[k] = v
  }
  return scores
})

/**
 * 生成编码了含正数值对象的合法 JSON 字符串。
 */
const validJsonStringWithPositiveArb = scoresWithAtLeastOnePositiveArb.map(
  scores => JSON.stringify(scores)
)

/**
 * 生成不可解析的 JSON 字符串（非空字符串，但 JSON.parse 会抛出异常）。
 * 策略：生成任意字符串，过滤掉可以被 JSON.parse 成功解析的情况。
 */
const invalidJsonStringArb = fc.string({ minLength: 1, maxLength: 50 }).filter(s => {
  try {
    JSON.parse(s)
    return false // 可以解析，排除
  } catch {
    return true  // 解析失败，保留
  }
})

// ─────────────────────────────────────────────
// Property 8 属性测试
// ─────────────────────────────────────────────

describe('Property 8: hasValidScores 正确性（hasValidScores Correctness）', () => {

  // ── Requirement 8.1 ──────────────────────────────────────────────────────
  // THE hasValidScores function SHALL return true when the record's scores
  // field is an object with at least one key whose numeric value is > 0.
  it('Property 8.1: 对任意含至少一个正数值的 scores 对象，应返回 true', () => {
    fc.assert(
      fc.property(
        scoresWithAtLeastOnePositiveArb,
        (scores) => {
          const record = { scores }
          return hasValidScores(record) === true
        }
      ),
      { numRuns: 300 }
    )
  })

  // ── Requirement 8.2 ──────────────────────────────────────────────────────
  // THE hasValidScores function SHALL return false when the record's scores
  // field is null or undefined.
  it('Property 8.2a: record.scores 为 null 时，对任意其他字段的 record，应返回 false', () => {
    fc.assert(
      fc.property(
        // 生成任意额外字段的 record，但 scores 固定为 null
        fc.record({
          id: fc.integer(),
          category: fc.string(),
          user_input: fc.string()
        }),
        (extraFields) => {
          const record = { ...extraFields, scores: null }
          return hasValidScores(record) === false
        }
      ),
      { numRuns: 200 }
    )
  })

  it('Property 8.2b: record.scores 为 undefined 时，应返回 false', () => {
    fc.assert(
      fc.property(
        fc.record({
          id: fc.integer(),
          category: fc.string()
        }),
        (extraFields) => {
          const record = { ...extraFields, scores: undefined }
          return hasValidScores(record) === false
        }
      ),
      { numRuns: 200 }
    )
  })

  it('Property 8.2c: record 本身为 null 或 undefined 时，应返回 false', () => {
    fc.assert(
      fc.property(
        fc.constantFrom(null, undefined),
        (record) => {
          return hasValidScores(record) === false
        }
      ),
      { numRuns: 50 }
    )
  })

  // ── Requirement 8.3 ──────────────────────────────────────────────────────
  // THE hasValidScores function SHALL return false when the record's scores
  // field is an empty object.
  it('Property 8.3: record.scores 为空对象时，对任意其他字段的 record，应返回 false', () => {
    fc.assert(
      fc.property(
        fc.record({
          id: fc.integer(),
          category: fc.string()
        }),
        (extraFields) => {
          const record = { ...extraFields, scores: {} }
          return hasValidScores(record) === false
        }
      ),
      { numRuns: 200 }
    )
  })

  // ── Requirement 8.4 ──────────────────────────────────────────────────────
  // WHEN the record's scores field is a JSON string, THE hasValidScores
  // function SHALL parse it before evaluation; IF parsing fails, SHALL return false.
  it('Property 8.4a: scores 为编码了含正数值对象的合法 JSON 字符串时，应返回 true', () => {
    fc.assert(
      fc.property(
        validJsonStringWithPositiveArb,
        (jsonString) => {
          const record = { scores: jsonString }
          return hasValidScores(record) === true
        }
      ),
      { numRuns: 300 }
    )
  })

  it('Property 8.4b: scores 为不可解析的 JSON 字符串时，应返回 false', () => {
    fc.assert(
      fc.property(
        invalidJsonStringArb,
        (invalidJson) => {
          const record = { scores: invalidJson }
          return hasValidScores(record) === false
        }
      ),
      { numRuns: 200 }
    )
  })

  // ── Requirement 8.5 ──────────────────────────────────────────────────────
  // THE hasValidScores function SHALL return false when all dimension values
  // in scores are 0 or non-numeric.
  it('Property 8.5: scores 所有值均为零或非数值时，应返回 false', () => {
    fc.assert(
      fc.property(
        scoresAllZeroOrNonNumericArb,
        (scores) => {
          const record = { scores }
          return hasValidScores(record) === false
        }
      ),
      { numRuns: 300 }
    )
  })

  // ── 综合属性：无副作用 ────────────────────────────────────────────────────
  // hasValidScores 不应修改传入的 record 对象（无副作用）
  it('Property: hasValidScores 不修改传入的 record 对象（无副作用）', () => {
    fc.assert(
      fc.property(
        fc.oneof(
          scoresWithAtLeastOnePositiveArb.map(scores => ({ scores })),
          fc.constant({ scores: null }),
          fc.constant({ scores: {} }),
          scoresAllZeroOrNonNumericArb.map(scores => ({ scores }))
        ),
        (record) => {
          // 记录调用前的 scores 引用
          const scoresBefore = record.scores
          hasValidScores(record)
          // scores 引用不应改变
          return record.scores === scoresBefore
        }
      ),
      { numRuns: 300 }
    )
  })

  // ── 综合属性：返回值始终为布尔类型 ──────────────────────────────────────
  it('Property: hasValidScores 对任意输入始终返回布尔类型', () => {
    fc.assert(
      fc.property(
        fc.oneof(
          scoresWithAtLeastOnePositiveArb.map(scores => ({ scores })),
          fc.constant(null),
          fc.constant(undefined),
          fc.constant({ scores: null }),
          fc.constant({ scores: {} }),
          scoresAllZeroOrNonNumericArb.map(scores => ({ scores })),
          validJsonStringWithPositiveArb.map(s => ({ scores: s })),
          invalidJsonStringArb.map(s => ({ scores: s }))
        ),
        (record) => {
          const result = hasValidScores(record)
          return typeof result === 'boolean'
        }
      ),
      { numRuns: 300 }
    )
  })
})
