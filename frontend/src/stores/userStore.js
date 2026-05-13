import { defineStore } from 'pinia'

/**
 * 用户基础信息 Store
 * 管理用户身份、雷达图数据、面板布局等全局用户数据
 */
export const useUserStore = defineStore('user', {
  state: () => ({
    candidateName: '',

    // 六维能力雷达图 mock 数据
    radarData: {
      indicators: [
        { name: '技术能力', max: 100 },
        { name: '沟通表达', max: 100 },
        { name: '项目经验', max: 100 },
        { name: '学习能力', max: 100 },
        { name: '团队协作', max: 100 },
        { name: '职业规划', max: 100 }
      ],
      values: [78, 65, 82, 90, 72, 68]
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
    }
  }
})
