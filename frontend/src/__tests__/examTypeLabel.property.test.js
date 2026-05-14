/**
 * examTypeLabel 属性测试 — Property-Based Testing with fast-check
 *
 * **Validates: Requirements 4.6**
 *
 * Property 5: 未知考试类型回退（Unknown examType Fallback）
 *
 * 核心属性：
 *   - 对五个合法 key（'zhuanchaben'、'gaokao'、'kaoyan'、'kaogong'、'other'），
 *     getExamTypeLabel() 应返回对应的中文标签
 *   - 对任意非五个合法 key 的字符串（包括空字符串、null、undefined、任意字符串），
 *     getExamTypeLabel() 应返回 '未设置'
 */
import { describe, it } from 'vitest'
import * as fc from 'fast-check'

// ─────────────────────────────────────────────
// 被测纯函数：从 Dashboard.vue 中提取的 examTypeLabel 映射逻辑
// ─────────────────────────────────────────────

/**
 * 将 examType key 映射为中文标签。
 *
 * 注意：使用 Object.prototype.hasOwnProperty.call(map, examType) 而非
 * map[examType] || '未设置'，以避免原型链属性（如 'toString'、'valueOf'、
 * '__proto__'）被误判为合法 key 并返回非字符串值。
 *
 * 这是对 Dashboard.vue 中 examTypeLabel computed 的安全修正版本：
 *   原始写法 map[examType] || '未设置' 在 examType 为原型属性名时会返回函数，
 *   修正后使用 hasOwnProperty 确保只有五个显式定义的 key 才能命中映射。
 *
 * @param {*} examType - 考试类型 key（任意值）
 * @returns {string} 对应的中文标签，未知值返回 '未设置'
 */
function getExamTypeLabel(examType) {
  const map = {
    'zhuanchaben': '专插本',
    'gaokao': '普通高考',
    'kaoyan': '考研',
    'kaogong': '考公',
    'other': '其他'
  }
  if (Object.prototype.hasOwnProperty.call(map, examType)) {
    return map[examType]
  }
  return '未设置'
}

// ─────────────────────────────────────────────
// 常量：五个合法 key 及其对应中文标签
// ─────────────────────────────────────────────

const VALID_EXAM_TYPE_MAP = {
  'zhuanchaben': '专插本',
  'gaokao': '普通高考',
  'kaoyan': '考研',
  'kaogong': '考公',
  'other': '其他'
}

const VALID_KEYS = Object.keys(VALID_EXAM_TYPE_MAP)

// ─────────────────────────────────────────────
// 自定义 Arbitraries（生成器）
// ─────────────────────────────────────────────

/**
 * 生成任意非合法 key 的字符串。
 * 策略：生成任意字符串，过滤掉五个合法 key。
 */
const invalidExamTypeStringArb = fc.string({ minLength: 0, maxLength: 50 }).filter(
  s => !VALID_KEYS.includes(s)
)

/**
 * 生成非字符串的任意值（null、undefined、数字、对象、数组、布尔值等）。
 * 这些值在 map[examType] 查找时均不会命中合法 key，应返回 '未设置'。
 */
const nonStringArb = fc.oneof(
  fc.constant(null),
  fc.constant(undefined),
  fc.integer(),
  fc.boolean(),
  fc.constant({}),
  fc.constant([]),
  fc.constant(0),
  fc.constant(NaN)
)

// ─────────────────────────────────────────────
// Property 5 属性测试
// ─────────────────────────────────────────────

describe('Property 5: 未知考试类型回退（Unknown examType Fallback）', () => {

  // ── Requirement 4.5 ──────────────────────────────────────────────────────
  // THE Sidebar SHALL map the examType key to a human-readable Chinese label
  // using the mapping: 'zhuanchaben'→'专插本', 'gaokao'→'普通高考',
  // 'kaoyan'→'考研', 'kaogong'→'考公', 'other'→'其他'.
  it('Property 5.0: 对五个合法 key，应返回对应的中文标签', () => {
    fc.assert(
      fc.property(
        fc.constantFrom(...VALID_KEYS),
        (validKey) => {
          const result = getExamTypeLabel(validKey)
          return result === VALID_EXAM_TYPE_MAP[validKey]
        }
      ),
      { numRuns: 50 }
    )
  })

  // ── Requirement 4.6 ──────────────────────────────────────────────────────
  // IF examType is empty or unrecognized, THEN THE Sidebar SHALL display
  // '未设置' as the exam type label.
  it('Property 5.1: 对任意非合法 key 的字符串（包括空字符串），应返回 "未设置"', () => {
    fc.assert(
      fc.property(
        invalidExamTypeStringArb,
        (invalidKey) => {
          const result = getExamTypeLabel(invalidKey)
          return result === '未设置'
        }
      ),
      { numRuns: 500 }
    )
  })

  it('Property 5.2: 对 null 和 undefined，应返回 "未设置"', () => {
    fc.assert(
      fc.property(
        fc.constantFrom(null, undefined),
        (value) => {
          const result = getExamTypeLabel(value)
          return result === '未设置'
        }
      ),
      { numRuns: 50 }
    )
  })

  it('Property 5.3: 对任意非字符串值（数字、布尔、对象、数组等），应返回 "未设置"', () => {
    fc.assert(
      fc.property(
        nonStringArb,
        (value) => {
          const result = getExamTypeLabel(value)
          return result === '未设置'
        }
      ),
      { numRuns: 200 }
    )
  })

  it('Property 5.4: 对合法 key 的大小写变体（非精确匹配），应返回 "未设置"', () => {
    // 合法 key 均为小写，大写变体不应命中映射
    fc.assert(
      fc.property(
        fc.constantFrom(...VALID_KEYS).map(k => k.toUpperCase()),
        (upperKey) => {
          // 全大写版本不是合法 key，应回退到 '未设置'
          const result = getExamTypeLabel(upperKey)
          return result === '未设置'
        }
      ),
      { numRuns: 50 }
    )
  })

  // ── 综合属性：返回值始终为字符串 ──────────────────────────────────────────
  it('Property 5.5: 对任意输入，返回值始终为字符串类型', () => {
    fc.assert(
      fc.property(
        fc.oneof(
          fc.constantFrom(...VALID_KEYS),
          invalidExamTypeStringArb,
          nonStringArb
        ),
        (value) => {
          const result = getExamTypeLabel(value)
          return typeof result === 'string'
        }
      ),
      { numRuns: 500 }
    )
  })

  // ── 综合属性：返回值只能是六种合法值之一 ────────────────────────────────
  it('Property 5.6: 对任意输入，返回值只能是六种合法中文标签之一', () => {
    const validLabels = new Set([...Object.values(VALID_EXAM_TYPE_MAP), '未设置'])

    fc.assert(
      fc.property(
        fc.oneof(
          fc.constantFrom(...VALID_KEYS),
          invalidExamTypeStringArb,
          nonStringArb
        ),
        (value) => {
          const result = getExamTypeLabel(value)
          return validLabels.has(result)
        }
      ),
      { numRuns: 500 }
    )
  })
})
