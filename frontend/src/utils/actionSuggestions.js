/**
 * actionSuggestions.js —— Dashboard「下一步行动」MVP 规则引擎
 *
 * 输入:Dashboard 已加载的 bentoRecordsPool(最近 100 条历史记录)。
 * 输出:1–3 条「下一步行动」建议,提示用户接下来该做什么。
 *
 * 设计约束:
 *   - 不调用 AI、不发后端请求。
 *   - 只读 bentoRecordsPool 已有数据,不写入 userStore / Provider / history。
 *   - 单一事实源:走 utils/historyRecordTypes.js 的 normalizeRecordType。
 *   - 风格沿用暗黑赛博 + accent 变量,colorKey 与 historyRecordTypes 保持一致。
 *
 * 规则(按 task 描述):
 *   1. 无历史记录                    → 建议先做一次简历诊断(新手启航)
 *   2. 最近一条 = resume_diagnosis    → 建议优化简历项目经历或技能表达
 *   3. 最近一条 = interview_session   → 建议复盘面试薄弱点
 *   4. 最近一条 = career_plan         → 建议执行职业规划近期行动
 *   5. 最近一条 = dashboard_chat      → 建议继续追问或归档对话
 *
 *   每条建议格式:{ id, type, title, desc, actionText, route, colorKey, iconKey }
 *   - id:    去重 / v-for key
 *   - type:  对应 RECORD_TYPES 常量(便于点击埋点)
 *   - route: 直接喂 router.push(route)
 */

import { normalizeRecordType, RECORD_TYPES } from './historyRecordTypes.js'

/**
 * 提取记录的时间戳(毫秒);缺失时返回 0。
 * 不依赖 dateFormat.js,避免循环引用。
 */
function getRecordTs(record) {
  if (!record) return 0
  const raw = record.updated_at || record.created_at || record.timestamp || ''
  if (!raw) return 0
  const t = new Date(raw).getTime()
  return Number.isFinite(t) ? t : 0
}

/**
 * 从最近 N 条历史中找出第一条标准类型为 wantedType 的记录。
 */
function findLatestByType(records, wantedType) {
  if (!Array.isArray(records) || records.length === 0) return null
  for (const r of records) {
    if (normalizeRecordType(r).type === wantedType) return r
  }
  return null
}

/**
 * 主入口:基于历史池生成 1–3 条「下一步行动」。
 *
 * @param {Array<object>} historyPool  bentoRecordsPool 内容(可空)
 * @returns {Array<{id:string,type:string,title:string,desc:string,actionText:string,route:string,colorKey:string,iconKey:string}>}
 */
export function buildNextActions(historyPool = []) {
  // 1) 无历史 → 新手启航,只给一条
  if (!Array.isArray(historyPool) || historyPool.length === 0) {
    return [
      {
        id: 'next-onboard-resume',
        type: RECORD_TYPES.RESUME_DIAGNOSIS,
        title: '先完成一次简历诊断',
        desc: '上传你的简历,AI 会给出六维评分与优化建议,帮你打开整套职业导航闭环。',
        actionText: '开始诊断',
        route: '/resume-diagnosis',
        colorKey: 'purple',
        iconKey: 'file-text'
      }
    ]
  }

  // 2) 历史按时间倒序后取最近一条作为「主建议」
  const sorted = [...historyPool].sort((a, b) => getRecordTs(b) - getRecordTs(a))
  const latest = sorted[0]
  const latestType = normalizeRecordType(latest).type

  const actions = []

  // 主建议:基于最近一条记录类型
  switch (latestType) {
    case RECORD_TYPES.RESUME_DIAGNOSIS: {
      actions.push({
        id: `next-resume-${latest.id || 'latest'}`,
        type: RECORD_TYPES.RESUME_DIAGNOSIS,
        title: '优化简历项目与技能表达',
        desc: '回到简历诊断,根据最新报告改写项目经历的 STAR 描述,补全关键词缺口。',
        actionText: '继续优化',
        route: `/resume-diagnosis?id=${latest.id}`,
        colorKey: 'purple',
        iconKey: 'file-text'
      })
      break
    }
    case RECORD_TYPES.INTERVIEW: {
      actions.push({
        id: `next-interview-${latest.id || 'latest'}`,
        type: RECORD_TYPES.INTERVIEW,
        title: '复盘面试薄弱点',
        desc: '对照最近一次面试评估,挑出最低分维度做针对性追问练习。',
        actionText: '查看复盘',
        route: `/interview?id=${latest.id}`,
        colorKey: 'pink',
        iconKey: 'bot'
      })
      break
    }
    case RECORD_TYPES.CAREER_PLAN: {
      actions.push({
        id: `next-career-${latest.id || 'latest'}`,
        type: RECORD_TYPES.CAREER_PLAN,
        title: '执行规划中的近期行动',
        desc: '回到职业规划蓝图,挑选 0–3 个月阶段的一项行动今天就开始执行。',
        actionText: '查看蓝图',
        route: `/career-planning?id=${latest.id}`,
        colorKey: 'cyan',
        iconKey: 'compass'
      })
      break
    }
    case RECORD_TYPES.DASHBOARD_CHAT:
    case RECORD_TYPES.LEGACY_CHAT: {
      // 沿用 historyRecordTypes 的路由约定:有 session_id 用 session,否则 chat_id
      const path = latest.session_id
        ? `/dashboard?session_id=${latest.session_id}`
        : `/dashboard?chat_id=${latest.id}`
      actions.push({
        id: `next-chat-${latest.id || 'latest'}`,
        type: RECORD_TYPES.DASHBOARD_CHAT,
        title: '继续追问或归档对话',
        desc: '返回工作台对话,继续追问刚才聊到一半的问题,或一键归档到历史记录。',
        actionText: '继续对话',
        route: path,
        colorKey: 'emerald',
        iconKey: 'message-square'
      })
      break
    }
    default: {
      // UNKNOWN / 兜底:还是引导做简历诊断
      actions.push({
        id: 'next-fallback-resume',
        type: RECORD_TYPES.RESUME_DIAGNOSIS,
        title: '先完成一次简历诊断',
        desc: '上传你的简历,AI 会给出六维评分与优化建议,这是其它功能的最佳起点。',
        actionText: '开始诊断',
        route: '/resume-diagnosis',
        colorKey: 'purple',
        iconKey: 'file-text'
      })
    }
  }

  // 3) 第二条:从尚未涉及的核心功能里再补 1–2 条(简历 / 面试 / 规划三选一)
  const present = new Set(actions.map(a => a.type))
  const candidates = []

  // 简历诊断兜底入口:如果历史里没有简历记录,推一条新手简历诊断
  if (!present.has(RECORD_TYPES.RESUME_DIAGNOSIS)) {
    const r = findLatestByType(sorted, RECORD_TYPES.RESUME_DIAGNOSIS)
    if (r) {
      candidates.push({
        id: `next-resume-${r.id}`,
        type: RECORD_TYPES.RESUME_DIAGNOSIS,
        title: '回顾上次简历诊断',
        desc: '回到上次的简历诊断报告,把里面给出的修改建议落地到正式简历里。',
        actionText: '回顾报告',
        route: `/resume-diagnosis?id=${r.id}`,
        colorKey: 'purple',
        iconKey: 'file-text'
      })
    } else {
      candidates.push({
        id: 'next-suggest-resume',
        type: RECORD_TYPES.RESUME_DIAGNOSIS,
        title: '试一次简历诊断',
        desc: '上传你的简历,AI 会给出六维评分与改写建议,补齐目标岗位关键词缺口。',
        actionText: '开始诊断',
        route: '/resume-diagnosis',
        colorKey: 'purple',
        iconKey: 'file-text'
      })
    }
  }

  // 模拟面试入口
  if (!present.has(RECORD_TYPES.INTERVIEW)) {
    const r = findLatestByType(sorted, RECORD_TYPES.INTERVIEW)
    if (r) {
      candidates.push({
        id: `next-interview-${r.id}`,
        type: RECORD_TYPES.INTERVIEW,
        title: '回顾上次面试评估',
        desc: '查看上次的能力雷达,锁定最低维度,围绕它再练一次模拟面试。',
        actionText: '查看复盘',
        route: `/interview?id=${r.id}`,
        colorKey: 'pink',
        iconKey: 'bot'
      })
    } else {
      candidates.push({
        id: 'next-suggest-interview',
        type: RECORD_TYPES.INTERVIEW,
        title: '试一次模拟面试',
        desc: '挑一个难度,沉浸式 AI 面试官对练,完成后会得到一张能力雷达图。',
        actionText: '开启实战',
        route: '/interview',
        colorKey: 'pink',
        iconKey: 'bot'
      })
    }
  }

  // 职业规划入口
  if (!present.has(RECORD_TYPES.CAREER_PLAN)) {
    const r = findLatestByType(sorted, RECORD_TYPES.CAREER_PLAN)
    if (r) {
      candidates.push({
        id: `next-career-${r.id}`,
        type: RECORD_TYPES.CAREER_PLAN,
        title: '回顾职业规划蓝图',
        desc: '打开上次的蓝图,选 0–3 个月阶段的一项任务,把它写进本周计划。',
        actionText: '查看蓝图',
        route: `/career-planning?id=${r.id}`,
        colorKey: 'cyan',
        iconKey: 'compass'
      })
    } else {
      candidates.push({
        id: 'next-suggest-career',
        type: RECORD_TYPES.CAREER_PLAN,
        title: '生成专属职业规划',
        desc: '把当前的职业困惑写下来,AI 会给出阶段路线、能力缺口与近期可执行的行动。',
        actionText: '生成规划',
        route: '/career-planning',
        colorKey: 'cyan',
        iconKey: 'compass'
      })
    }
  }

  // 取前 2 条候选,合并到 actions(限制总数 ≤ 3)
  for (const c of candidates) {
    if (actions.length >= 3) break
    actions.push(c)
  }

  return actions.slice(0, 3)
}
