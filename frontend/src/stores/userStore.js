import { defineStore } from 'pinia'

/**
 * 用户基础信息 Store
 * 管理用户身份、雷达图数据、面板布局等全局用户数据
 */
export const useUserStore = defineStore('user', {
  state: () => ({
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
     * 根据 tab 名称返回对应的置顶记录 ID
     * @param {string} tab - 'resume' | 'interview' | 'career'
     * @returns {number|null} 对应的置顶 ID，未知 tab 返回 null
     */
    getPinnedIdByTab: (state) => (tab) => {
      if (tab === 'resume') return state.pinnedResumeId
      if (tab === 'interview') return state.pinnedInterviewId
      if (tab === 'career') return state.pinnedCareerId
      return null
    }
  },

  actions: {
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

      // 同步写入 localStorage，失败时静默处理（隐私模式或存储已满）
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
        // localStorage 写入失败时不抛出异常，Store 内存状态仍正常可用
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
     * @param {string} tab - 'resume' | 'interview' | 'career'
     * @param {number|null} recordId - 记录 ID，null 表示取消置顶
     */
    setPinnedId(tab, recordId) {
      // tab 与 state 字段及 localStorage 键名的映射关系
      const tabConfig = {
        resume:    { field: 'pinnedResumeId',    storageKey: 'pinned_resume_id' },
        interview: { field: 'pinnedInterviewId', storageKey: 'pinned_interview_id' },
        career:    { field: 'pinnedCareerId',    storageKey: 'pinned_career_id' }
      }

      const config = tabConfig[tab]
      // 未知 tab 值时静默忽略，不修改任何状态
      if (!config) return

      this[config.field] = recordId

      try {
        if (recordId !== null) {
          // recordId 非 null 时写入 localStorage
          localStorage.setItem(config.storageKey, String(recordId))
        } else {
          // recordId 为 null 时移除对应 localStorage 键
          localStorage.removeItem(config.storageKey)
        }
      } catch {
        // localStorage 操作失败时静默处理，Store 内存状态仍正常可用
      }
    },

    /**
     * 从 localStorage 读取三个置顶 ID 并恢复到 state
     * 键不存在或解析失败时保持 null；整个函数用 try/catch 包裹，异常时静默处理
     */
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
        // localStorage 读取失败时静默处理，保持 state 中的 null 值
      }
    }
  }
})
