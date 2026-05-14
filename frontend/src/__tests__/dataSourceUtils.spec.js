/**
 * dataSourceUtils 单元测试
 *
 * 覆盖 hasValidScores() 和 filterValidDataSources() 的核心行为：
 *   - null / undefined / 空对象 → false
 *   - 全零对象 → false
 *   - 至少一个正数值 → true
 *   - JSON 字符串解析（合法 / 非法）
 *   - filterValidDataSources 返回正确子集且不修改原数组
 *
 * Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7
 */
import { describe, it, expect } from 'vitest'
import { hasValidScores, filterValidDataSources } from '../utils/dataSourceUtils.js'

// ─────────────────────────────────────────────
// hasValidScores — 单元测试
// ─────────────────────────────────────────────

describe('hasValidScores', () => {
  // Requirement 8.2 — null / undefined scores
  it('record 为 null 时返回 false', () => {
    expect(hasValidScores(null)).toBe(false)
  })

  it('record 为 undefined 时返回 false', () => {
    expect(hasValidScores(undefined)).toBe(false)
  })

  it('record.scores 为 null 时返回 false', () => {
    expect(hasValidScores({ scores: null })).toBe(false)
  })

  it('record.scores 为 undefined 时返回 false', () => {
    expect(hasValidScores({ scores: undefined })).toBe(false)
  })

  // Requirement 8.3 — 空对象
  it('record.scores 为空对象时返回 false', () => {
    expect(hasValidScores({ scores: {} })).toBe(false)
  })

  // Requirement 8.5 — 全零 / 非数值
  it('record.scores 所有维度值为 0 时返回 false', () => {
    expect(hasValidScores({ scores: { '技术能力': 0, '沟通表达': 0 } })).toBe(false)
  })

  it('record.scores 所有维度值为非数值字符串时返回 false', () => {
    expect(hasValidScores({ scores: { '技术能力': 'abc', '沟通表达': '' } })).toBe(false)
  })

  // Requirement 8.1 — 至少一个正数值
  it('record.scores 含一个正数值时返回 true', () => {
    expect(hasValidScores({ scores: { '技术能力': 80 } })).toBe(true)
  })

  it('record.scores 含多个正数值时返回 true', () => {
    expect(hasValidScores({
      scores: { '技术能力': 70, '沟通表达': 60, '项目经验': 50 }
    })).toBe(true)
  })

  it('record.scores 混合零与正数时返回 true', () => {
    expect(hasValidScores({ scores: { '技术能力': 0, '沟通表达': 1 } })).toBe(true)
  })

  // Requirement 8.4 — JSON 字符串解析
  it('record.scores 为合法 JSON 字符串且含正数值时返回 true', () => {
    const jsonStr = JSON.stringify({ '技术能力': 85, '沟通表达': 0 })
    expect(hasValidScores({ scores: jsonStr })).toBe(true)
  })

  it('record.scores 为合法 JSON 字符串但全零时返回 false', () => {
    const jsonStr = JSON.stringify({ '技术能力': 0, '沟通表达': 0 })
    expect(hasValidScores({ scores: jsonStr })).toBe(false)
  })

  it('record.scores 为合法 JSON 字符串但为空对象时返回 false', () => {
    expect(hasValidScores({ scores: '{}' })).toBe(false)
  })

  it('record.scores 为非法 JSON 字符串时返回 false', () => {
    expect(hasValidScores({ scores: '{invalid json' })).toBe(false)
  })

  it('record.scores 为普通字符串（非 JSON）时返回 false', () => {
    expect(hasValidScores({ scores: 'hello' })).toBe(false)
  })

  // 边界：scores 为数组时返回 false（非普通对象）
  it('record.scores 为数组时返回 false', () => {
    expect(hasValidScores({ scores: [1, 2, 3] })).toBe(false)
  })

  // 边界：record 为空对象（无 scores 字段）
  it('record 为空对象（无 scores 字段）时返回 false', () => {
    expect(hasValidScores({})).toBe(false)
  })
})

// ─────────────────────────────────────────────
// filterValidDataSources — 单元测试
// ─────────────────────────────────────────────

describe('filterValidDataSources', () => {
  // Requirement 8.6 — 返回满足 hasValidScores 的子集
  it('空数组输入时返回空数组', () => {
    expect(filterValidDataSources([])).toEqual([])
  })

  it('非数组输入时返回空数组', () => {
    expect(filterValidDataSources(null)).toEqual([])
    expect(filterValidDataSources(undefined)).toEqual([])
    expect(filterValidDataSources('string')).toEqual([])
  })

  it('全部记录无效时返回空数组', () => {
    const records = [
      { scores: null },
      { scores: {} },
      { scores: { '技术能力': 0 } }
    ]
    expect(filterValidDataSources(records)).toEqual([])
  })

  it('全部记录有效时返回全部', () => {
    const records = [
      { id: 1, scores: { '技术能力': 80 } },
      { id: 2, scores: { '沟通表达': 60 } }
    ]
    const result = filterValidDataSources(records)
    expect(result).toHaveLength(2)
    expect(result[0].id).toBe(1)
    expect(result[1].id).toBe(2)
  })

  it('混合有效与无效记录时只返回有效记录', () => {
    const validRecord = { id: 10, scores: { '技术能力': 75 } }
    const invalidRecord = { id: 20, scores: null }
    const records = [invalidRecord, validRecord, { id: 30, scores: {} }]
    const result = filterValidDataSources(records)
    expect(result).toHaveLength(1)
    expect(result[0].id).toBe(10)
  })

  it('含 JSON 字符串 scores 的有效记录被正确保留', () => {
    const record = { id: 5, scores: JSON.stringify({ '项目经验': 90 }) }
    const result = filterValidDataSources([record])
    expect(result).toHaveLength(1)
    expect(result[0].id).toBe(5)
  })

  // Requirement 8.7 — 不修改原数组
  it('不修改原始数组的长度', () => {
    const records = [
      { id: 1, scores: { '技术能力': 80 } },
      { id: 2, scores: null },
      { id: 3, scores: {} }
    ]
    const originalLength = records.length
    filterValidDataSources(records)
    expect(records).toHaveLength(originalLength)
  })

  it('不修改原始数组的元素引用', () => {
    const r1 = { id: 1, scores: { '技术能力': 80 } }
    const r2 = { id: 2, scores: null }
    const records = [r1, r2]
    filterValidDataSources(records)
    expect(records[0]).toBe(r1)
    expect(records[1]).toBe(r2)
  })

  it('返回数组中的元素与原数组中的元素是同一引用', () => {
    const r1 = { id: 1, scores: { '技术能力': 80 } }
    const records = [r1]
    const result = filterValidDataSources(records)
    expect(result[0]).toBe(r1)
  })
})
