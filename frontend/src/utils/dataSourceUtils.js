/**
 * dataSourceUtils.js
 * 有效数据源筛选工具函数
 *
 * 职责：判断历史评估记录是否含有效雷达图评分数据，
 * 并从记录数组中筛选出可用的数据源子集。
 *
 * 对应需求：Requirements 8.1 ~ 8.7
 */

/**
 * 判断一条历史记录是否含有效雷达图评分数据。
 *
 * 有效定义：scores 解析后至少包含 1 个维度值 > 0 的数值。
 *
 * 前置条件：record 可以是任意值（函数内部做防御性检查）
 * 后置条件：
 *   - 返回 true  当且仅当 record.scores 解析后至少有一个正数值
 *   - 返回 false 对于 null、undefined、空对象、解析失败的情况
 *   - 无副作用，不修改传入参数
 *
 * @param {*} record - 历史评估记录对象
 * @returns {boolean}
 */
export function hasValidScores(record) {
  // 防御性检查：record 本身为空值时直接返回 false
  if (record == null) return false

  let scores = record.scores

  // scores 为 JSON 字符串时尝试解析；解析失败则视为无效
  if (typeof scores === 'string') {
    try {
      scores = JSON.parse(scores)
    } catch {
      return false
    }
  }

  // scores 为 null、undefined 或非对象（含数组）时返回 false
  if (!scores || typeof scores !== 'object' || Array.isArray(scores)) {
    return false
  }

  // 至少有一个维度的数值 > 0 才算有效
  return Object.values(scores).some(v => Number(v) > 0)
}

/**
 * 从历史记录数组中筛选出含有效雷达图评分的记录子集。
 *
 * 前置条件：records 是 Array 类型，每项可能含 scores 字段
 * 后置条件：
 *   - 返回数组是 records 的子集（引用不变）
 *   - 每条返回记录均满足 hasValidScores === true
 *   - 不修改原始 records 数组（长度与元素引用保持不变）
 *
 * @param {Array} records - 历史评估记录数组
 * @returns {Array} 含有效评分的记录列表
 */
export function filterValidDataSources(records) {
  if (!Array.isArray(records)) return []
  // Array.prototype.filter 不修改原数组，满足不可变性要求
  return records.filter(record => hasValidScores(record))
}
