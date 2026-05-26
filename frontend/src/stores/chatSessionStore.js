import { defineStore } from 'pinia'

const STORAGE_KEY = 'chat_session_state'

function generateSessionId() {
  return 'sess_' + Date.now().toString(36) + '_' + Math.random().toString(36).slice(2, 8)
}

/**
 * chatSessionStore — 管理 Dashboard 底部 ChatDock 的前端本地状态
 *
 * 职责：
 *   - 当前会话消息列表
 *   - 折叠/展开状态
 *   - localStorage 持久化（跨刷新保持对话）
 *   - streaming 中间态管理
 *   - 归档状态追踪
 */
export const useChatSessionStore = defineStore('chatSession', {
  state: () => ({
    currentSessionId: generateSessionId(),
    messages: [],
    isCollapsed: false,
    isLoading: false,
    // 归档状态
    archivedRecordId: null,   // 已归档到后端的 record_id
    isDirty: false,           // 归档后是否有新消息
    isArchiving: false,       // 归档中 loading
  }),

  getters: {
    /** 折叠态 pill 中展示的最近一条用户消息预览（最多 20 字） */
    lastUserPreview: (state) => {
      const userMsgs = state.messages.filter(m => m.role === 'user')
      if (!userMsgs.length) return ''
      const last = userMsgs[userMsgs.length - 1].content || ''
      return last.length > 20 ? last.slice(0, 20) + '…' : last
    },

    /** 是否有对话内容 */
    hasConversation: (state) => {
      return state.messages.some(m => (m.content || '').trim().length > 0)
    },

    /** 归档按钮状态文案 */
    archiveLabel: (state) => {
      if (state.isArchiving) return '归档中...'
      if (state.archivedRecordId && !state.isDirty) return '已归档'
      if (state.archivedRecordId && state.isDirty) return '重新归档'
      return '归档本次对话'
    },

    /** 归档按钮是否可点击 */
    canArchive: (state) => {
      if (state.isArchiving) return false
      // streaming 中禁止归档:此时最后一条 AI 消息可能仍在持续追加,
      // 归档结果会是不完整的快照,且与 store 状态机存在 race。
      if (state.isLoading) return false
      if (!state.messages.some(m => (m.content || '').trim())) return false
      if (state.archivedRecordId && !state.isDirty) return false
      return true
    }
  },

  actions: {
    /** 追加用户消息 */
    appendUserMessage(content) {
      this.messages.push({
        role: 'user',
        content,
        timestamp: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }),
        isNew: true
      })
      this.isDirty = true
      this.persistLocal()
    },

    /** 追加 AI 消息占位（streaming 开始前调用） */
    appendAIMessage() {
      const msg = {
        role: 'ai',
        content: '',
        timestamp: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }),
        isNew: true,
        agentLabel: ''
      }
      this.messages.push(msg)
      return msg
    },

    /** 更新最后一条 AI 消息的内容（streaming 增量追加） */
    updateStreamingMessage(chunk) {
      const lastAi = [...this.messages].reverse().find(m => m.role === 'ai')
      if (lastAi) {
        lastAi.content += chunk
      }
    },

    /** 设置最后一条 AI 消息的 agentLabel */
    setLastAIAgentLabel(label) {
      const lastAi = [...this.messages].reverse().find(m => m.role === 'ai')
      if (lastAi) {
        lastAi.agentLabel = label
      }
    },

    /** 清空当前会话，开始新对话 */
    clearSession() {
      this.messages = []
      this.currentSessionId = generateSessionId()
      this.isLoading = false
      this.archivedRecordId = null
      this.isDirty = false
      this.persistLocal()
    },

    /** 标记已归档 */
    markArchived(recordId) {
      this.archivedRecordId = recordId
      this.isDirty = false
      this.persistLocal()
    },

    /** 切换折叠状态 */
    toggleCollapsed() {
      this.isCollapsed = !this.isCollapsed
      this.persistLocal()
    },

    /** 设置折叠状态 */
    setCollapsed(val) {
      this.isCollapsed = val
      this.persistLocal()
    },

    /** 从历史记录恢复会话 */
    restoreFromHistory(sessionId, messages, recordId = null) {
      this.currentSessionId = sessionId || generateSessionId()
      this.messages = messages.map(msg => ({
        role: msg.role === 'user' ? 'user' : 'ai',
        content: msg.content || '',
        timestamp: msg.timestamp || '',
        isNew: false
      }))
      this.archivedRecordId = recordId
      this.isDirty = false
      this.persistLocal()
    },

    /** 持久化到 localStorage */
    persistLocal() {
      try {
        const payload = {
          currentSessionId: this.currentSessionId,
          messages: this.messages.slice(-50),
          isCollapsed: this.isCollapsed,
          archivedRecordId: this.archivedRecordId,
          isDirty: this.isDirty
        }
        localStorage.setItem(STORAGE_KEY, JSON.stringify(payload))
      } catch {
        // localStorage 写入失败时静默处理
      }
    },

    /** 从 localStorage 恢复 */
    restoreFromLocalStorage() {
      try {
        const raw = localStorage.getItem(STORAGE_KEY)
        if (!raw) return
        const parsed = JSON.parse(raw)
        if (parsed.currentSessionId) this.currentSessionId = parsed.currentSessionId
        if (Array.isArray(parsed.messages)) {
          this.messages = parsed.messages.map(m => ({ ...m, isNew: false }))
        }
        if (typeof parsed.isCollapsed === 'boolean') this.isCollapsed = parsed.isCollapsed
        if (parsed.archivedRecordId !== undefined) this.archivedRecordId = parsed.archivedRecordId
        if (typeof parsed.isDirty === 'boolean') this.isDirty = parsed.isDirty
      } catch {
        // 解析失败：保持初始状态
      }
    }
  }
})
