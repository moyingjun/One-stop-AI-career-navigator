/**
 * dateFormat.js — 统一时间格式工具
 *
 * 全 Dashboard 使用此函数渲染历史记录时间，保证一致性。
 * 字段优先级：updated_at > created_at > timestamp > date
 */

/**
 * 格式化历史记录的时间为本地可读字符串。
 *
 * @param {object|string|null} recordOrTimestamp
 *   传 record 对象：自动按字段优先级取时间
 *   传 string：直接当时间字符串处理
 * @returns {string} 形如 "2026/05/23 14:30"，无效输入返回空串
 */
export function formatRecordTime(recordOrTimestamp) {
  if (!recordOrTimestamp) return ''

  let raw = ''
  if (typeof recordOrTimestamp === 'string') {
    raw = recordOrTimestamp
  } else if (typeof recordOrTimestamp === 'object') {
    raw = recordOrTimestamp.updated_at
      || recordOrTimestamp.created_at
      || recordOrTimestamp.timestamp
      || recordOrTimestamp.date
      || ''
  }

  if (!raw || typeof raw !== 'string') return ''

  try {
    const d = new Date(raw)
    if (isNaN(d.getTime())) return raw  // 无法解析时回退原字符串
    return d.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    })
  } catch {
    return raw
  }
}

/**
 * 获取记录的原始时间字段（用于排序），返回 Number 时间戳，无效返回 0
 */
export function getRecordTimestamp(record) {
  if (!record || typeof record !== 'object') return 0
  const raw = record.updated_at || record.created_at || record.timestamp || record.date || ''
  if (!raw) return 0
  try {
    const t = new Date(raw).getTime()
    return Number.isFinite(t) ? t : 0
  } catch {
    return 0
  }
}
