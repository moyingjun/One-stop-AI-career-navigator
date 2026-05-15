import { defineStore } from 'pinia'

// ─────────────────────────────────────────────
// JWT 工具函数（不依赖任何外部库）
// ─────────────────────────────────────────────

/**
 * 解析 JWT Payload（Base64URL 解码），失败时返回 null
 * @param {string} token
 * @returns {object|null}
 */
function parseJwtPayload(token) {
  try {
    const parts = token.split('.')
    if (parts.length !== 3) return null
    // Base64URL → Base64 → JSON
    const base64 = parts[1].replace(/-/g, '+').replace(/_/g, '/')
    const json = decodeURIComponent(
      atob(base64)
        .split('')
        .map((c) => '%' + c.charCodeAt(0).toString(16).padStart(2, '0'))
        .join('')
    )
    return JSON.parse(json)
  } catch {
    return null
  }
}

/**
 * 判断 JWT token 是否已过期或即将过期（提前 60 秒视为过期）
 * @param {string|null} token
 * @returns {boolean} true = 已过期或无效
 */
function isTokenExpired(token) {
  if (!token || token.trim().length === 0) return true
  const payload = parseJwtPayload(token)
  if (!payload || typeof payload.exp !== 'number') return true
  // 提前 60 秒判定过期，给刷新留出窗口
  const nowSeconds = Math.floor(Date.now() / 1000)
  return nowSeconds >= payload.exp - 60
}

/**
 * 用户基础信息 Store
 *
 * 管理：
 *   - 鉴权状态（token、userId、email）
 *   - 用户画像（姓名、简历、目标岗位等）
 *   - 雷达图数据
 *   - 面板布局配置
 *   - 置顶记录 ID
 */
export const useUserStore = defineStore('user', {
  state: () => ({
    // ── 鉴权状态 ──────────────────────────────
    token: localStorage.getItem('token') || null,
    userId: localStorage.getItem('user_id') ? Number(localStorage.getItem('user_id')) : null,
    email: localStorage.getItem('user_email') || null,

    // ── 用户画像 ──────────────────────────────
    candidateName: '',
    resumeText: '',

    // 求职模式字段
    targetJob: '',
    jobDescription: '',

    // 模式切换与升学模式字段
    activeMode: 'job',       // 'job' | 'education'
    examType: '',
    estimatedScore: '',
    examRank: '',
    targetSchool: '',

    // 当前雷达图激活的数据源记录 ID（number | null）
    activeDataSourceId: null,

    // 置顶记录 ID（用于 Bento UI 快速访问，null 表示未设置）
    pinnedResumeId: null,
    pinnedInterviewId: null,
    pinnedCareerId: null,

    // 用户目标（用于个性化展示与 AI 提示词注入）
    targetGoal: '',

    // 六维能力雷达图数据（默认空状态，由 API 动态填充）
    radarData: {
      indicators: [
        { name: '技术能力', max: 100 },
        { name: '沟通表达', max: 100 },
        { name: '项目经验', max: 100 },
        { name: '学习能力', max: 100 },
        { name: '团队协作', max: 100 },
        { name: '职业规划', max: 100 }
      ],
      values: [0, 0, 0, 0, 0, 0]
    },

    // 面板布局配置
    panelLayout: {
      columns: 4,
      gap: '1rem',
      cardSizes: {
        greeting: { col: 2, row: 1 },
        resume: { col: 2, row: 1 },
        feature: { col: 4, row: 2 },
        radar: { col: 2, row: 2 },
        quickActions: { col: 2, row: 1 },
        history: { col: 2, row: 1 }
      }
    }
  }),

  getters: {
    /** 动态时间问候语 */
    greeting: () => {
      const hour = new Date().getHours()
      if (hour >= 6 && hour < 12) return '早上好'
      if (hour >= 12 && hour < 14) return '中午好'
      if (hour >= 14 && hour < 18) return '下午好'
      if (hour >= 18 && hour < 24) return '晚上好'
      return '夜深了'
    },

    /**
     * 当前 token 是否已过期（或不存在）
     * 基于 JWT Payload 的 exp 字段判断，提前 60 秒视为过期
     * @returns {boolean}
     */
    isExpired: (state) => isTokenExpired(state.token),

    /**
     * 是否已登录（有 token 且未过期）
     * @returns {boolean}
     */
    isLoggedIn: (state) => {
      return Boolean(state.token) && !isTokenExpired(state.token)
    },

    /**
     * 根据 tab 名称返回对应的置顶记录 ID
     * @param {string} tab - 'resume' | 'interview' | 'career'
     * @returns {number|null}
     */
    getPinnedIdByTab: (state) => (tab) => {
      if (tab === 'resume') return state.pinnedResumeId
      if (tab === 'interview') return state.pinnedInterviewId
      if (tab === 'career') return state.pinnedCareerId
      return null
    }
  },

  actions: {
    /**
     * 登录成功后调用：持久化 token、userId、email 到 state 和 localStorage
     * @param {{ access_token: string, user_id: number, email: string }} authData
     */
    login(authData) {
      this.token = authData.access_token
      this.userId = authData.user_id
      this.email = authData.email

      try {
        localStorage.setItem('token', authData.access_token)
        localStorage.setItem('user_id', String(authData.user_id))
        localStorage.setItem('user_email', authData.email || '')
      } catch {
        // localStorage 写入失败时静默处理（隐私模式或存储已满）
      }
    },

    /**
     * 登出：清除 token、userId、email，重置用户画像
     * 不负责路由跳转，由调用方决定跳转目标
     */
    logout() {
      this.token = null
      this.userId = null
      this.email = null

      // 重置用户画像
      this.candidateName = ''
      this.resumeText = ''
      this.targetJob = ''
      this.jobDescription = ''
      this.activeMode = 'job'
      this.examType = ''
      this.estimatedScore = ''
      this.examRank = ''
      this.targetSchool = ''
      this.targetGoal = ''
      this.pinnedResumeId = null
      this.pinnedInterviewId = null
      this.pinnedCareerId = null

      try {
        localStorage.removeItem('token')
        localStorage.removeItem('user_id')
        localStorage.removeItem('user_email')
        localStorage.removeItem('candidate_name')
        localStorage.removeItem('resume_text')
        localStorage.removeItem('active_mode')
        localStorage.removeItem('target_job')
        localStorage.removeItem('job_description')
        localStorage.removeItem('exam_type')
        localStorage.removeItem('estimated_score')
        localStorage.removeItem('exam_rank')
        localStorage.removeItem('target_school')
        localStorage.removeItem('target_goal')
        localStorage.removeItem('pinned_resume_id')
        localStorage.removeItem('pinned_interview_id')
        localStorage.removeItem('pinned_career_id')
      } catch {
        // localStorage 清除失败时静默处理
      }
    },

    /** 更新所有用户画像字段，并同步持久化到 localStorage */
    updateUserProfile(payload) {
      this.candidateName = payload.candidateName || ''
      this.resumeText = payload.resumeText || ''
      this.activeMode = payload.activeMode || 'job'
      this.targetJob = payload.targetJob || ''
      this.jobDescription = payload.jobDescription || ''
      this.examType = payload.examType || ''
      this.estimatedScore = payload.estimatedScore || ''
      this.examRank = payload.examRank || ''
      this.targetSchool = payload.targetSchool || ''
      this.targetGoal = payload.targetGoal || ''

      try {
        localStorage.setItem('candidate_name', this.candidateName)
        localStorage.setItem('resume_text', this.resumeText)
        localStorage.setItem('active_mode', this.activeMode)
        localStorage.setItem('target_job', this.targetJob)
        localStorage.setItem('job_description', this.jobDescription)
        localStorage.setItem('exam_type', this.examType)
        localStorage.setItem('estimated_score', this.estimatedScore)
        localStorage.setItem('exam_rank', this.examRank)
        localStorage.setItem('target_school', this.targetSchool)
        localStorage.setItem('target_goal', this.targetGoal)
      } catch {
        // localStorage 写入失败时不抛出异常
      }
    },

    /** 根据评估 scores 对象更新雷达图数据，每项 clamp 到 [0, 100] */
    updateRadarData(scores) {
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
      this.radarData = { ...this.radarData, values: newValues }
    },

    /** 重置雷达图数据为空状态 */
    resetRadarData() {
      this.radarData = { ...this.radarData, values: [0, 0, 0, 0, 0, 0] }
    },

    /** 从 localStorage 读取所有用户画像字段并同步到 state */
    loadFromStorage() {
      this.candidateName = localStorage.getItem('candidate_name') || ''
      this.resumeText = localStorage.getItem('resume_text') || ''
      this.activeMode = localStorage.getItem('active_mode') || 'job'
      this.targetJob = localStorage.getItem('target_job') || ''
      this.jobDescription = localStorage.getItem('job_description') || ''
      this.examType = localStorage.getItem('exam_type') || ''
      this.estimatedScore = localStorage.getItem('estimated_score') || ''
      this.examRank = localStorage.getItem('exam_rank') || ''
      this.targetSchool = localStorage.getItem('target_school') || ''
      this.targetGoal = localStorage.getItem('target_goal') || ''
      this.loadPinnedIds()
    },

    /**
     * 设置指定 tab 的置顶记录 ID，并同步写入 localStorage
     */
    setPinnedId(tab, recordId) {
      const tabConfig = {
        resume:    { field: 'pinnedResumeId',    storageKey: 'pinned_resume_id' },
        interview: { field: 'pinnedInterviewId', storageKey: 'pinned_interview_id' },
        career:    { field: 'pinnedCareerId',    storageKey: 'pinned_career_id' }
      }
      const config = tabConfig[tab]
      if (!config) return
      this[config.field] = recordId
      try {
        if (recordId !== null) {
          localStorage.setItem(config.storageKey, String(recordId))
        } else {
          localStorage.removeItem(config.storageKey)
        }
      } catch {
        // 静默处理
      }
    },

    /** 从 localStorage 读取三个置顶 ID 并恢复到 state */
    loadPinnedIds() {
      try {
        const parseId = (raw) => {
          if (raw === null) return null
          const parsed = parseInt(raw, 10)
          return isNaN(parsed) ? null : parsed
        }
        this.pinnedResumeId    = parseId(localStorage.getItem('pinned_resume_id'))
        this.pinnedInterviewId = parseId(localStorage.getItem('pinned_interview_id'))
        this.pinnedCareerId    = parseId(localStorage.getItem('pinned_career_id'))
      } catch {
        // 静默处理
      }
    }
  }
})
