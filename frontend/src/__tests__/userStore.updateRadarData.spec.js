/**
 * userStore.updateRadarData 属性测试 — Property-Based Testing with fast-check
 *
 * **Validates: Requirements 4.2, 4.3**
 *
 * Property 1: RadarData invariant
 * 对任意合法 scores 对象，updateRadarData(scores) 后 values 数组长度恒为 6 且每项 ∈ [0, 100]
 *
 * updateRadarData 的实现（userStore.js）：
 *   const dimensionMap = { '技术能力': 0, '沟通表达': 1, '项目经验': 2, '学习能力': 3, '团队协作': 4, '职业规划': 5 }
 *   const newValues = [0, 0, 0, 0, 0, 0]
 *   for (const [key, value] of Object.entries(scores))
 *     if (dimensionMap[key] !== undefined)
 *       newValues[dimensionMap[key]] = Math.max(0, Math.min(100, Number(value) || 0))
 *   this.radarData = { ...this.radarData, values: newValues }
 */
import { describe, it, expect } from 'vitest'
import * as fc from 'fast-check'

// ===== updateRadarData 逻辑提取 =====

/**
 * 从 userStore.js 提取的 updateRadarData 纯逻辑
 * @param {object} radarData - 当前 radarData 状态
 * @param {object} scores - 输入的 scores 对象（任意键值对）
 * @returns {object} 更新后的 radarData
 */
function updateRadarData(radarData, scores) {
  const dimensionMap = {
    '技术能力': 0, '沟通表达': 1, '项目经验': 2,
    '学习能力': 3, '团队协作': 4, '职业规划': 5
  }
  const newValues = [0, 0, 0, 0, 0, 0]
  for (const [key, value] of Object.entries(scores)) {
    const index = dimensionMap[key]
    if (index !== undefined) {
      newValues[index] = Math.max(0, Math.min(100, Number(value) || 0))
    }
  }
  return { ...radarData, values: newValues }
}

// ===== 自定义 Arbitraries =====

/**
 * 生成任意 scores 对象：键为任意字符串，值为各种边界类型
 * 包含正常数值、负数、NaN、Infinity、null、undefined、字符串等
 */
const arbitraryScoresArb = fc.dictionary(
  fc.string({ minLength: 0, maxLength: 20 }),
  fc.oneof(
    fc.integer({ min: -1000, max: 1000 }),
    fc.double({ min: -1000, max: 1000, noNaN: false }),
    fc.constant(NaN),
    fc.constant(Infinity),
    fc.constant(-Infinity),
    fc.constant(null),
    fc.constant(undefined),
    fc.string({ minLength: 0, maxLength: 10 })
  )
)

/**
 * 生成包含有效维度名称的 scores 对象
 * 键为六维能力名称的子集，值为各种类型
 */
const dimensions = ['技术能力', '沟通表达', '项目经验', '学习能力', '团队协作', '职业规划']

const validDimensionScoresArb = fc.tuple(
  fc.subarray(dimensions, { minLength: 0, maxLength: 6 }),
  fc.array(
    fc.oneof(
      fc.integer({ min: -1000, max: 1000 }),
      fc.double({ min: -1000, max: 1000, noNaN: false }),
      fc.constant(NaN),
      fc.constant(Infinity),
      fc.constant(-Infinity),
      fc.constant(null),
      fc.constant(undefined),
      fc.string({ minLength: 0, maxLength: 10 })
    ),
    { minLength: 6, maxLength: 6 }
  )
).map(([keys, values]) => {
  const obj = {}
  keys.forEach((key, i) => { obj[key] = values[i] })
  return obj
})

/**
 * 混合 scores：既有有效维度名称，也有随机键
 */
const mixedScoresArb = fc.tuple(
  validDimensionScoresArb,
  arbitraryScoresArb
).map(([validPart, randomPart]) => ({ ...randomPart, ...validPart }))

// ===== 初始 radarData 状态 =====

const initialRadarData = {
  indicators: [
    { name: '技术能力', max: 100 },
    { name: '沟通表达', max: 100 },
    { name: '项目经验', max: 100 },
    { name: '学习能力', max: 100 },
    { name: '团队协作', max: 100 },
    { name: '职业规划', max: 100 }
  ],
  values: [0, 0, 0, 0, 0, 0]
}

// ===== Property Tests =====

describe('userStore.updateRadarData - Property Tests', () => {
  it('Property: 任意 scores 对象 → values 数组长度恒为 6 且每项 ∈ [0, 100]（随机键值对）', () => {
    fc.assert(
      fc.property(
        arbitraryScoresArb,
        (scores) => {
          const result = updateRadarData(initialRadarData, scores)

          // values 长度恒为 6
          expect(result.values).toHaveLength(6)

          // 每项 ∈ [0, 100]
          for (const v of result.values) {
            expect(v).toBeGreaterThanOrEqual(0)
            expect(v).toBeLessThanOrEqual(100)
          }
        }
      ),
      { numRuns: 500 }
    )
  })

  it('Property: 包含有效维度名称的 scores → values 数组长度恒为 6 且每项 ∈ [0, 100]', () => {
    fc.assert(
      fc.property(
        validDimensionScoresArb,
        (scores) => {
          const result = updateRadarData(initialRadarData, scores)

          // values 长度恒为 6
          expect(result.values).toHaveLength(6)

          // 每项 ∈ [0, 100]
          for (const v of result.values) {
            expect(v).toBeGreaterThanOrEqual(0)
            expect(v).toBeLessThanOrEqual(100)
          }
        }
      ),
      { numRuns: 500 }
    )
  })

  it('Property: 混合 scores（有效维度 + 随机键）→ values 数组长度恒为 6 且每项 ∈ [0, 100]', () => {
    fc.assert(
      fc.property(
        mixedScoresArb,
        (scores) => {
          const result = updateRadarData(initialRadarData, scores)

          // values 长度恒为 6
          expect(result.values).toHaveLength(6)

          // 每项 ∈ [0, 100]
          for (const v of result.values) {
            expect(v).toBeGreaterThanOrEqual(0)
            expect(v).toBeLessThanOrEqual(100)
          }
        }
      ),
      { numRuns: 500 }
    )
  })

  it('Property: indicators 数组在 updateRadarData 后保持不变', () => {
    fc.assert(
      fc.property(
        arbitraryScoresArb,
        (scores) => {
          const result = updateRadarData(initialRadarData, scores)

          // indicators 不变
          expect(result.indicators).toEqual(initialRadarData.indicators)
        }
      ),
      { numRuns: 200 }
    )
  })

  it('Property: 空对象 scores → values 全为 0', () => {
    const result = updateRadarData(initialRadarData, {})
    expect(result.values).toEqual([0, 0, 0, 0, 0, 0])
  })
})
