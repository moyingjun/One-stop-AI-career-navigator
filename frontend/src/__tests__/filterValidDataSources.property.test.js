/**
 * filterValidDataSources 属性测试（Property-Based Tests）
 *
 * Property 6: 有效数据源筛选（Valid DataSource Filtering）
 *   对任意混合记录数组，filterValidDataSources() 返回的子集中
 *   每条记录均满足 hasValidScores() === true，
 *   且所有满足 hasValidScores() === true 的记录均不被遗漏。
 *
 * Property 7: 筛选不修改原数组（Filter Immutability）
 *   对任意输入数组，调用 filterValidDataSources() 后
 *   原数组的长度和每个元素的引用均保持不变。
 *
 * Validates: Requirements 8.6, 8.7
 */
import { describe, it } from 'vitest'
import * as fc from 'fast-check'
import { hasValidScores, filterValidDataSources } from '../utils/dataSourceUtils.js'

// ─────────────────────────────────────────────
// Arbitraries（生成器）
// ─────────────────────────────────────────────

/**
 * 生成一个"有效"的 scores 对象：至少一个维度值 > 0
 * 使用真实的中文维度 key，贴近生产数据
 */
const DIMENSION_KEYS = ['技术能力', '沟通表达', '项目经验', '学习能力', '团队协作', '职业规划']

const validScoresObjectArb = fc
  .record({
    技术能力: fc.integer({ min: 0, max: 100 }),
    沟通表达: fc.integer({ min: 0, max: 100 }),
    项目经验: fc.integer({ min: 0, max: 100 }),
    学习能力: fc.integer({ min: 0, max: 100 }),
    团队协作: fc.integer({ min: 0, max: 100 }),
    职业规划: fc.integer({ min: 0, max: 100 }),
  })
  .filter(obj => Object.values(obj).some(v => v > 0))

/** 生成一个"无效"的 scores 值（null / 空对象 / 全零对象 / 非法 JSON 字符串） */
const invalidScoresArb = fc.oneof(
  fc.constant(null),
  fc.constant(undefined),
  fc.constant({}),
  fc.constant({ 技术能力: 0, 沟通表达: 0, 项目经验: 0 }),
  fc.constant('{invalid json'),
  fc.constant(''),
  fc.constant('{}'),
)

/** 生成一个含有效 scores 的历史记录对象 */
const validRecordArb = fc.record({
  id: fc.integer({ min: 1, max: 100000 }),
  scores: fc.oneof(
    validScoresObjectArb,
    // 也可以是合法 JSON 字符串形式的有效 scores
    validScoresObjectArb.map(obj => JSON.stringify(obj)),
  ),
  category: fc.constantFrom('resume_diagnosis', 'interview_mock', 'career_planning'),
  user_input: fc.string({ minLength: 1, maxLength: 200 }),
  created_at: fc.string({ minLength: 1, maxLength: 30 }),
})

/** 生成一个含无效 scores 的历史记录对象 */
const invalidRecordArb = fc.record({
  id: fc.integer({ min: 100001, max: 200000 }),
  scores: invalidScoresArb,
  category: fc.constantFrom('resume_diagnosis', 'interview_mock', 'career_planning'),
  user_input: fc.string({ minLength: 0, maxLength: 200 }),
  created_at: fc.string({ minLength: 0, maxLength: 30 }),
})

/**
 * 生成一个混合数组：包含任意数量的有效记录和无效记录
 * 使用 fc.array + fc.oneof 模拟真实场景
 */
const mixedRecordsArb = fc.array(
  fc.oneof(validRecordArb, invalidRecordArb),
  { minLength: 0, maxLength: 30 },
)

// ─────────────────────────────────────────────
// Property 6: 有效数据源筛选（Valid DataSource Filtering）
// Validates: Requirements 8.6
// ─────────────────────────────────────────────

describe('Property 6: filterValidDataSources — 有效数据源筛选', () => {
  /**
   * 子属性 6a：返回子集中每条记录均满足 hasValidScores() === true
   *
   * 对任意混合记录数组，filterValidDataSources() 的每个返回元素
   * 都必须通过 hasValidScores() 检验。
   *
   * Validates: Requirements 8.6
   */
  it('返回子集中每条记录均满足 hasValidScores() === true', () => {
    fc.assert(
      fc.property(mixedRecordsArb, (records) => {
        const result = filterValidDataSources(records)
        return result.every(record => hasValidScores(record) === true)
      }),
      { numRuns: 200 },
    )
  })

  /**
   * 子属性 6b：所有满足 hasValidScores() 的记录均不被遗漏（完整性）
   *
   * 对任意混合记录数组，原数组中每条满足 hasValidScores() 的记录
   * 都必须出现在 filterValidDataSources() 的返回结果中。
   *
   * Validates: Requirements 8.6
   */
  it('原数组中所有满足 hasValidScores() 的记录均出现在结果中', () => {
    fc.assert(
      fc.property(mixedRecordsArb, (records) => {
        const result = filterValidDataSources(records)
        const expectedValidRecords = records.filter(r => hasValidScores(r))
        // 结果长度应等于原数组中有效记录的数量
        if (result.length !== expectedValidRecords.length) return false
        // 结果中的每个元素应与原数组中对应的有效记录是同一引用
        return expectedValidRecords.every((r, i) => result[i] === r)
      }),
      { numRuns: 200 },
    )
  })

  /**
   * 子属性 6c：纯有效记录数组 → 返回全部记录
   *
   * 当输入数组中所有记录均有效时，filterValidDataSources() 应返回
   * 与原数组等长且元素引用相同的数组。
   *
   * Validates: Requirements 8.6
   */
  it('纯有效记录数组时返回全部记录', () => {
    fc.assert(
      fc.property(fc.array(validRecordArb, { minLength: 1, maxLength: 20 }), (records) => {
        const result = filterValidDataSources(records)
        return result.length === records.length
      }),
      { numRuns: 200 },
    )
  })

  /**
   * 子属性 6d：纯无效记录数组 → 返回空数组
   *
   * 当输入数组中所有记录均无效时，filterValidDataSources() 应返回空数组。
   *
   * Validates: Requirements 8.6
   */
  it('纯无效记录数组时返回空数组', () => {
    fc.assert(
      fc.property(fc.array(invalidRecordArb, { minLength: 1, maxLength: 20 }), (records) => {
        const result = filterValidDataSources(records)
        return result.length === 0
      }),
      { numRuns: 200 },
    )
  })
})

// ─────────────────────────────────────────────
// Property 7: 筛选不修改原数组（Filter Immutability）
// Validates: Requirements 8.7
// ─────────────────────────────────────────────

describe('Property 7: filterValidDataSources — 筛选不修改原数组', () => {
  /**
   * 子属性 7a：调用后原数组长度不变
   *
   * 对任意混合记录数组，调用 filterValidDataSources() 后
   * 原数组的 length 属性应与调用前完全相同。
   *
   * Validates: Requirements 8.7
   */
  it('调用后原数组长度不变', () => {
    fc.assert(
      fc.property(mixedRecordsArb, (records) => {
        const originalLength = records.length
        filterValidDataSources(records)
        return records.length === originalLength
      }),
      { numRuns: 200 },
    )
  })

  /**
   * 子属性 7b：调用后原数组每个元素的引用不变
   *
   * 对任意混合记录数组，调用 filterValidDataSources() 后
   * 原数组中每个位置的元素引用应与调用前完全相同（严格相等 ===）。
   *
   * Validates: Requirements 8.7
   */
  it('调用后原数组每个元素的引用不变', () => {
    fc.assert(
      fc.property(mixedRecordsArb, (records) => {
        // 记录调用前每个元素的引用快照
        const snapshotRefs = records.map(r => r)
        filterValidDataSources(records)
        // 逐一比较引用
        return snapshotRefs.every((ref, i) => records[i] === ref)
      }),
      { numRuns: 200 },
    )
  })

  /**
   * 子属性 7c：返回数组中的元素与原数组中的元素是同一引用（无深拷贝）
   *
   * filterValidDataSources() 不应对记录对象进行深拷贝，
   * 返回的每个元素应与原数组中对应元素严格相等（===）。
   *
   * Validates: Requirements 8.7
   */
  it('返回数组中的元素与原数组中的元素是同一引用', () => {
    fc.assert(
      fc.property(fc.array(validRecordArb, { minLength: 1, maxLength: 20 }), (records) => {
        const result = filterValidDataSources(records)
        // 所有有效记录都应以原始引用出现在结果中
        return result.every(resultRecord =>
          records.some(originalRecord => originalRecord === resultRecord)
        )
      }),
      { numRuns: 200 },
    )
  })
})
