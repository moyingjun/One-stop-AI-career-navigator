/**
 * HistoryArchive 收藏过滤 属性测试 — Property-Based Testing with fast-check
 *
 * **Validates: Requirements 2.2, 2.5**
 *
 * Property 4: 对任意 historyRecords 数组和 filterSaved='saved'，filteredRecords 中每条记录的 is_saved 为 truthy
 *
 * filterRecords 的实现（HistoryArchive.vue）：
 *   if (filterSaved === 'saved') {
 *     records = records.filter(r => r.is_saved === 1 || r.is_saved === true)
 *   }
 *   if (filterCategory !== 'all') {
 *     records = records.filter(r => r.category === filterCategory)
 *   }
 *   if (searchQuery.trim()) {
 *     const query = searchQuery.toLowerCase()
 *     records = records.filter(r =>
 *       String(r.user_input || '').toLowerCase().includes(query) ||
 *       String(r.ai_result || '').toLowerCase().includes(query)
 *     )
 *   }
 */
import { describe, it, expect } from 'vitest'
import * as fc from 'fast-check'

// ===== filterRecords 纯逻辑提取 =====

/**
 * 从 HistoryArchive.vue 提取的 filteredRecords computed 纯逻辑
 * @param {Array} records - 历史记录数组
 * @param {string} filterSaved - 'all' | 'saved'
 * @param {string} filterCategory - 类型过滤（'all' 表示不过滤）
 * @param {string} searchQuery - 搜索关键词
 * @returns {Array} 过滤后的记录数组
 */
function filterRecords(records, filterSaved, filterCategory, searchQuery) {
  let result = records

  // 收藏状态过滤
  if (filterSaved === 'saved') {
    result = result.filter(r => r.is_saved === 1 || r.is_saved === true)
  }

  // 类型过滤
  if (filterCategory !== 'all') {
    result = result.filter(r => r.category === filterCategory)
  }

  // 搜索过滤
  if (searchQuery.trim()) {
    const query = searchQuery.toLowerCase()
    result = result.filter(r =>
      String(r.user_input || '').toLowerCase().includes(query) ||
      String(r.ai_result || '').toLowerCase().includes(query)
    )
  }

  return result
}

// ===== 自定义 Arbitraries =====

/**
 * 生成任意 is_saved 值：覆盖 0, 1, true, false, null, undefined 等边界
 */
const isSavedArb = fc.oneof(
  fc.constant(0),
  fc.constant(1),
  fc.constant(true),
  fc.constant(false),
  fc.constant(null),
  fc.constant(undefined)
)

/**
 * 生成任意历史记录对象
 */
const historyRecordArb = fc.record({
  id: fc.integer({ min: 1, max: 100000 }),
  category: fc.oneof(
    fc.constant('resume_diagnosis'),
    fc.constant('interview_evaluate'),
    fc.constant('career_planning'),
    fc.constant('agent_general'),
    fc.constant('general_chat'),
    fc.string({ minLength: 1, maxLength: 20 })
  ),
  user_input: fc.oneof(fc.string({ minLength: 0, maxLength: 50 }), fc.constant(null), fc.constant(undefined)),
  ai_result: fc.oneof(fc.string({ minLength: 0, maxLength: 50 }), fc.constant(null), fc.constant(undefined)),
  is_saved: isSavedArb,
  created_at: fc.constant('2024-01-01 12:00:00')
})

/**
 * 生成任意历史记录数组
 */
const historyRecordsArb = fc.array(historyRecordArb, { minLength: 0, maxLength: 30 })

// ===== Property Tests =====

describe('HistoryArchive filterSaved - Property Tests', () => {
  it('Property 4: filterSaved="saved" → 结果中每条记录的 is_saved 为 truthy（=== 1 或 === true）', () => {
    fc.assert(
      fc.property(
        historyRecordsArb,
        (records) => {
          const result = filterRecords(records, 'saved', 'all', '')

          // 结果中每条记录的 is_saved 必须为 1 或 true
          for (const record of result) {
            expect(record.is_saved === 1 || record.is_saved === true).toBe(true)
          }
        }
      ),
      { numRuns: 500 }
    )
  })

  it('Property: filterSaved="all" → 所有记录通过（不过滤 is_saved）', () => {
    fc.assert(
      fc.property(
        historyRecordsArb,
        (records) => {
          const result = filterRecords(records, 'all', 'all', '')

          // 不过滤时，结果应与输入完全一致
          expect(result).toEqual(records)
        }
      ),
      { numRuns: 500 }
    )
  })

  it('Property: 过滤结果始终是输入记录的子集', () => {
    fc.assert(
      fc.property(
        historyRecordsArb,
        fc.oneof(fc.constant('all'), fc.constant('saved')),
        (records, filterSaved) => {
          const result = filterRecords(records, filterSaved, 'all', '')

          // 结果长度 ≤ 输入长度
          expect(result.length).toBeLessThanOrEqual(records.length)

          // 结果中每条记录都存在于输入中
          for (const record of result) {
            expect(records).toContain(record)
          }
        }
      ),
      { numRuns: 500 }
    )
  })
})
