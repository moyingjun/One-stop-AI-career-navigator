import { defineStore } from 'pinia'
import { getAuthHeaders } from '@/services/authService.js'

const isLocalDev = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
const API_BASE_URL = isLocalDev ? 'http://127.0.0.1:8000/api' : '/api'

const STORAGE_KEY = 'llm_provider_id'

/**
 * Provider 能力描述字典（纯前端展示资产）
 *
 * 用于在 GlobalProviderSwitcher 下拉中给每条 Provider 显示一句简短能力标签。
 * 不影响后端契约，不会发送到任何 API。
 *
 * key 与 Provider id 一致；后端真实 Provider（mimo / deepseek）也复用此字典。
 */
const PROVIDER_DESCRIPTIONS = {
  mimo: '中文规划强 · 成本友好',
  deepseek: '逻辑推理强 · 代码辅助',
  'gpt-5.5': '综合能力强 · 多场景',
  'glm-5.1': '中文办公 · 本土生态',
  'kimi-2.6': '长文本阅读 · 资料分析',
  'qwen-3.7-max': '工程代码 · 工具调用'
}

/**
 * 占位 Provider 列表
 *
 * 这些条目仅用于在 UI 中提示"未来支持"，是纯前端展示资产：
 *   - is_placeholder: true     —— 标记为占位（store 会拒绝其 setCurrentProvider）
 *   - status: 'unconfigured'   —— 渲染为灰色 / Standby
 *   - 不能携带 api_key，不会发送 provider_id 到后端
 *
 * 排序：在真实 providers 之后追加，避免抢占默认选中位。
 */
const PLACEHOLDER_PROVIDERS = [
  { id: 'gpt-5.5',     display_name: 'GPT-5.5',     model_name: 'gpt-5.5',     status: 'unconfigured', is_default: false, is_placeholder: true },
  { id: 'glm-5.1',     display_name: 'GLM-5.1',     model_name: 'glm-5.1',     status: 'unconfigured', is_default: false, is_placeholder: true },
  { id: 'kimi-2.6',    display_name: 'Kimi-2.6',    model_name: 'kimi-2.6',    status: 'unconfigured', is_default: false, is_placeholder: true },
  { id: 'qwen-3.7-max', display_name: 'Qwen-3.7Max', model_name: 'qwen-3.7-max', status: 'unconfigured', is_default: false, is_placeholder: true }
]

/** 给单个 Provider 注入 description（基于 id 字典查找，未命中返回空串） */
function withDescription(p) {
  return { ...p, description: PROVIDER_DESCRIPTIONS[p.id] || '' }
}

/**
 * llmProviderStore — LLM Provider 切换状态管理
 *
 * 职责：
 *   - 拉取后端 Provider 列表（脱敏后的 id/display_name/model_name/status/is_default）
 *   - 管理用户当前选中的 provider_id（持久化到 localStorage）
 *   - 提供 currentProvider getter，供 Dashboard / 三功能页 / ChatDock 共用
 *   - 在真实列表后追加 placeholder providers（GPT-5.5 / GLM-5.1 / Kimi-2.6 / Qwen-3.7Max）
 *   - 给每个 Provider 注入纯前端 description（能力标签）
 *
 * 安全约束：
 *   - 永远不存储 api_key
 *   - 即使后端意外返回 api_key 字段，前端也丢弃
 *   - placeholder providers 永远不可被选中、不会写入 localStorage
 */
export const useLlmProviderStore = defineStore('llmProvider', {
  state: () => ({
    providers: [],                                              // 真实 providers + placeholder providers
    currentProviderId: localStorage.getItem(STORAGE_KEY) || null,
    loading: false,
    error: ''
  }),

  getters: {
    /** 当前选中的 Provider 对象（必须是真实可用的 online 项） */
    currentProvider: (state) => {
      if (!Array.isArray(state.providers) || state.providers.length === 0) return null
      // 优先按用户选择
      if (state.currentProviderId) {
        const found = state.providers.find(p => p.id === state.currentProviderId && !p.is_placeholder)
        if (found) return found
      }
      // 否则用 is_default
      const def = state.providers.find(p => p.is_default && !p.is_placeholder)
      if (def) return def
      // 兜底：第一个真实 online
      return state.providers.find(p => p.status === 'online' && !p.is_placeholder) || null
    },

    /** 当前 Provider 的展示名称（带 Online 状态后缀） */
    currentDisplayLabel: (state) => {
      const cur = state.providers.find(p => p.id === state.currentProviderId && !p.is_placeholder)
        || state.providers.find(p => p.is_default && !p.is_placeholder)
        || state.providers.find(p => p.status === 'online' && !p.is_placeholder)
      if (!cur) return 'Default LLM Online'
      return `${cur.display_name} Online`
    }
  },

  actions: {
    /** 拉取 Provider 列表（真实数据 + placeholder） */
    async loadProviders() {
      this.loading = true
      this.error = ''
      try {
        const res = await fetch(`${API_BASE_URL}/llm/providers`, {
          headers: { ...getAuthHeaders() }
        })
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const data = await res.json()
        const list = Array.isArray(data?.providers) ? data.providers : []
        // 字段白名单过滤：丢弃任何意外返回的敏感字段
        const realProviders = list.map(p => withDescription({
          id: String(p.id || ''),
          display_name: String(p.display_name || p.id || ''),
          model_name: String(p.model_name || ''),
          status: p.status === 'online' ? 'online' : 'unconfigured',
          is_default: !!p.is_default,
          is_placeholder: false
        }))

        // 合并占位 Provider：仅在真实列表中不存在同名 ID 时追加，避免覆盖真实可用引擎
        const realIds = new Set(realProviders.map(p => p.id))
        const placeholders = PLACEHOLDER_PROVIDERS
          .filter(p => !realIds.has(p.id))
          .map(withDescription)

        this.providers = [...realProviders, ...placeholders]

        // 校验当前选择是否还有效：必须存在于真实列表 && online
        if (this.currentProviderId) {
          const exists = realProviders.find(p => p.id === this.currentProviderId)
          if (!exists || exists.status !== 'online') {
            this.currentProviderId = null
            try { localStorage.removeItem(STORAGE_KEY) } catch {}
          }
        }

        // 如果还没有选择，使用 is_default
        if (!this.currentProviderId) {
          const def = realProviders.find(p => p.is_default && p.status === 'online')
          if (def) {
            this.currentProviderId = def.id
            try { localStorage.setItem(STORAGE_KEY, def.id) } catch {}
          }
        }
      } catch (err) {
        console.error('加载 Provider 列表失败:', err)
        this.error = '无法加载 AI 引擎列表'
        // 失败时也展示占位列表，保持 UI 不塌陷
        this.providers = PLACEHOLDER_PROVIDERS.map(withDescription)
      } finally {
        this.loading = false
      }
    },

    /**
     * 设置当前 Provider
     * @param {string} providerId
     * @returns {boolean} 是否成功（unconfigured / placeholder 会拒绝）
     */
    setCurrentProvider(providerId) {
      const target = this.providers.find(p => p.id === providerId)
      if (!target) return false
      if (target.is_placeholder) return false
      if (target.status !== 'online') return false
      this.currentProviderId = providerId
      try { localStorage.setItem(STORAGE_KEY, providerId) } catch {}
      return true
    },

    /** 获取当前 provider_id（请求体附加用，placeholder 永远不会返回） */
    getCurrentProviderId() {
      if (!this.currentProviderId) return null
      const found = this.providers.find(p => p.id === this.currentProviderId)
      if (!found || found.is_placeholder) return null
      return this.currentProviderId
    }
  }
})
