/**
 * resumeBuilderStore.js — Resume Preview Builder 专属 Pinia Store
 *
 * 严格遵守:
 *   - localStorage 命名空间:`resume_builder:` 前缀(Requirement 10.5)
 *   - 写入失败兜底 + Toast(Requirement 10.6)
 *   - 不与 userStore / 任何其它 Store 互写
 *   - 编辑/切换不触发 HTTP(Requirement 8.3 / 11.5)
 */

import { defineStore } from 'pinia'
import { showToast } from '@/utils/uiFallbacks.js'
import {
  ALLOWED_TEMPLATE_IDS,
  applyFieldEdit,
  addArrayItem as schemaAddArrayItem,
  removeArrayItem as schemaRemoveArrayItem,
  buildSafeSkeleton,
  deepEqualExceptTemplateId,
  hasMissingFields,
  listMissingPaths,
  switchTemplate as schemaSwitchTemplate,
  isValidResumeJson
} from '@/utils/resumeJsonSchema.js'
import { extractResumeFromDraft } from '@/services/resumeBuilderClient.js'
import { truncatePlainText, isTextTruncated } from '@/utils/truncatePlainText.js'

const NS = 'resume_builder:'
const STORAGE_VERSION = 1

function storageKey(documentId) {
  return `${NS}current:${documentId || '__default__'}`
}

function dismissedKey(documentId) {
  return `${NS}dismissed:${documentId || '__default__'}`
}

function safeWrite(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value))
    return true
  } catch (err) {
    console.warn('[resumeBuilderStore] localStorage 写入失败:', err)
    showToast('本地存储写入失败,请检查浏览器存储配额', { type: 'error' })
    return false
  }
}

function safeRead(key) {
  try {
    const raw = localStorage.getItem(key)
    if (!raw) return null
    return JSON.parse(raw)
  } catch (err) {
    console.warn('[resumeBuilderStore] localStorage 读取失败:', err)
    return null
  }
}

function safeRemove(key) {
  try {
    localStorage.removeItem(key)
  } catch {
    /* noop */
  }
}

/**
 * 把 LLM 返回的"裸 Resume_JSON"包一层校验:
 *   - 校验通过 → 原样返回
 *   - 校验失败 → 安全骨架兜底
 */
function sanitizeResumeJson(json, documentId) {
  if (isValidResumeJson(json)) return json
  return buildSafeSkeleton(documentId)
}

export const useResumeBuilderStore = defineStore('resumeBuilder', {
  state: () => ({
    /** 当前 Resume_JSON(Single Source of Truth) */
    resumeJson: null,
    /** AI 抽取追问问题列表(本会话) */
    missingQuestions: [],
    /** 用户在本会话中"忽略"的 missing_questions 索引集合 */
    dismissedQuestions: new Set(),
    /** 后端返回的 warnings(empty_input / fabrication_suspected / ...) */
    warnings: [],
    /** Resume_JSON 是否相对 lastExtract 产生了未保存的编辑 */
    isDirty: false,
    /** 上次成功 extract 的时间戳 */
    lastExtractAt: 0,
    /** 当前文档 ID(来自 /files) */
    documentId: '',
    /** 是否正在调用 extract API */
    extracting: false,
    /** 关闭横幅状态(本会话) */
    fabricationBannerDismissed: false,
    /** 是否提示"草稿已截断" */
    draftTruncated: false,
    /** 校验快照 — 用于 switchTemplate 非法变更检测 */
    _snapshotForTemplateGuard: null,
    /**
     * Hotfix 7 取证 — 单调请求计数器,本会话内每次发起 extract 请求 +1。
     * 仅最新一次 token 对应的响应允许覆盖 store;旧 token 的迟到响应被丢弃,
     * 防止用户连续点击「生成简历预览」/「重新抽取」时旧请求覆盖新结果。
     */
    _extractCounter: 0,
    /** 最近一次后端返回的 debug_request_id(供调试取证用) */
    lastDebugRequestId: null
  }),

  getters: {
    /** 是否有可用 Resume_JSON。 */
    hasResume(state) {
      return !!state.resumeJson
    },
    /** 当前模板 ID。 */
    currentTemplateId(state) {
      return state.resumeJson?.meta?.templateId || 'ats_single_column'
    },
    /** 是否已确认。 */
    isConfirmedByUser(state) {
      return !!state.resumeJson?.meta?.confirmedByUser
    },
    /** Resume_JSON 是否仍含 missing/needs_confirmation。 */
    stillHasMissing(state) {
      return state.resumeJson ? hasMissingFields(state.resumeJson) : false
    },
    /** 是否含「疑似编造」红色警告。 */
    showFabricationBanner(state) {
      return (
        state.warnings?.includes('fabrication_suspected') &&
        !state.fabricationBannerDismissed &&
        state.resumeJson
      )
    },
    /** 当前 missing_questions(剔除已忽略的)。 */
    visibleMissingQuestions(state) {
      return (state.missingQuestions || [])
        .map((text, idx) => ({ idx, text }))
        .filter((q) => !state.dismissedQuestions.has(q.idx))
    }
  },

  actions: {
    // ─── 进入 Workspace ──────────────────────────────────────────

    /**
     * 从 /files 进入 Workspace 时调用。
     *
     * 流程:
     *   1. 优先尝试从 localStorage 加载现有结构化结果
     *   2. localStorage 没有 → 调用 extract API
     *   3. 二者都失败 → 加载安全骨架
     */
    async initFromDraft(draft) {
      if (!draft || typeof draft !== 'object') return
      const documentId = String(draft.document_id || '')
      this.documentId = documentId
      this.dismissedQuestions = new Set()
      this.fabricationBannerDismissed = false

      // 1) 草稿截断
      const rawText = typeof draft.plain_text === 'string' ? draft.plain_text : ''
      this.draftTruncated = isTextTruncated(rawText)
      const plainText = truncatePlainText(rawText)
      const contentJson =
        draft.content_json && typeof draft.content_json === 'object' ? draft.content_json : {}

      // 2) 尝试 localStorage 命中
      const cached = safeRead(storageKey(documentId))
      if (cached && cached.version === STORAGE_VERSION && isValidResumeJson(cached.resumeJson)) {
        this.resumeJson = cached.resumeJson
        this.missingQuestions = Array.isArray(cached.missingQuestions) ? cached.missingQuestions.slice() : []
        this.warnings = Array.isArray(cached.warnings) ? cached.warnings.slice() : []
        this.lastExtractAt = cached.lastExtractAt || Date.now()
        this.isDirty = false
        this._snapshotForTemplateGuard = JSON.parse(JSON.stringify(this.resumeJson))
        return
      }

      // 3) 调用 extract API
      await this._doExtract({
        document_id: documentId,
        plain_text: plainText,
        content_json: contentJson,
        provider_id: draft.provider_id || null
      })
    },

    /**
     * 「确认覆盖」路径:丢弃当前未保存编辑,重新抽取。
     */
    async reextractFromDraft(draft) {
      if (!draft || typeof draft !== 'object') return
      const documentId = String(draft.document_id || '')
      this.documentId = documentId
      this.dismissedQuestions = new Set()
      this.fabricationBannerDismissed = false

      const rawText = typeof draft.plain_text === 'string' ? draft.plain_text : ''
      this.draftTruncated = isTextTruncated(rawText)
      const plainText = truncatePlainText(rawText)
      const contentJson =
        draft.content_json && typeof draft.content_json === 'object' ? draft.content_json : {}

      await this._doExtract({
        document_id: documentId,
        plain_text: plainText,
        content_json: contentJson,
        provider_id: draft.provider_id || null
      })
    },

    /** 内部:执行 extract API + 写入状态 + 持久化。 */
    async _doExtract(payload) {
      this.extracting = true
      // Hotfix 7:发起前递增 token,只有当响应回来时 token 仍是最新才允许覆盖 store
      this._extractCounter += 1
      const myToken = this._extractCounter
      try {
        const data = await extractResumeFromDraft(payload)
        // 旧请求迟到 → 丢弃(防止覆盖更新)
        if (myToken !== this._extractCounter) {
          console.warn(
            '[resumeBuilderStore] 丢弃迟到响应 token=%d (latest=%d) debug_request_id=%s',
            myToken,
            this._extractCounter,
            data?.debug_request_id || '(none)'
          )
          return
        }
        const sanitized = sanitizeResumeJson(data.resume_json, payload.document_id)
        this.resumeJson = sanitized
        this.missingQuestions = (data.missing_questions || []).slice()
        this.warnings = (data.warnings || []).slice()
        this.lastExtractAt = Date.now()
        this.lastDebugRequestId = data.debug_request_id || null
        this.isDirty = false
        this._snapshotForTemplateGuard = JSON.parse(JSON.stringify(sanitized))
        this._persist()
        if (!data.success && this.warnings.includes('json_parse_failed')) {
          showToast('AI 抽取失败,可手工填写', { type: 'error' })
        } else if (this.warnings.includes('extraction_timeout')) {
          showToast('AI 抽取超时,可手工填写', { type: 'error' })
        } else if (this.warnings.includes('non_resume_content_detected')) {
          showToast('草稿可能含非简历内容,已尽力抽取', { type: 'success' })
        }
      } catch (err) {
        // 旧请求 reject 也要丢弃,不能覆盖最新 store
        if (myToken !== this._extractCounter) {
          console.warn('[resumeBuilderStore] 丢弃迟到的 reject token=%d', myToken)
          return
        }
        console.error('[resumeBuilderStore] extract 异常:', err)
        const skeleton = buildSafeSkeleton(payload.document_id)
        this.resumeJson = skeleton
        this.missingQuestions = []
        this.warnings = ['json_parse_failed']
        this.lastExtractAt = Date.now()
        this.lastDebugRequestId = null
        this.isDirty = false
        this._snapshotForTemplateGuard = JSON.parse(JSON.stringify(skeleton))
        showToast('AI 抽取失败,可手工填写', { type: 'error' })
      } finally {
        // 仅当本 token 仍是最新时,才把 extracting 置 false
        // 旧 token 的 finally 不影响 UI 旋转状态(避免新请求还在跑就被关掉 loading)
        if (myToken === this._extractCounter) {
          this.extracting = false
        }
      }
    },

    // ─── 字段编辑 ──────────────────────────────────────────

    patchField(path, value) {
      if (!this.resumeJson) return
      try {
        applyFieldEdit(this.resumeJson, path, value)
        this.isDirty = true
        this._persist()
      } catch (err) {
        console.warn('[resumeBuilderStore] patchField 异常:', err)
      }
    },

    addArrayItem(sectionPath, template) {
      if (!this.resumeJson) return
      try {
        schemaAddArrayItem(this.resumeJson, sectionPath, template)
        this.isDirty = true
        this._persist()
      } catch (err) {
        console.warn('[resumeBuilderStore] addArrayItem 异常:', err)
      }
    },

    removeArrayItem(sectionPath, index) {
      if (!this.resumeJson) return
      try {
        schemaRemoveArrayItem(this.resumeJson, sectionPath, index)
        this.isDirty = true
        this._persist()
      } catch (err) {
        console.warn('[resumeBuilderStore] removeArrayItem 异常:', err)
      }
    },

    /**
     * 模板切换 — 仅写 meta.templateId,其他字段必须深相等。
     * Requirement 7.5 / 7.10。
     */
    switchTemplate(templateId) {
      if (!this.resumeJson) return
      if (!ALLOWED_TEMPLATE_IDS.includes(templateId)) {
        showToast('未知的模板标识', { type: 'error' })
        return
      }

      // 先记录"切换前"的快照
      const prevSnapshot = JSON.parse(JSON.stringify(this.resumeJson))
      const prevTemplateId = prevSnapshot.meta?.templateId

      // 切换
      schemaSwitchTemplate(this.resumeJson, templateId)

      // 检查是否有非法字段变更(理论上只会改 meta.templateId,这是防御性检查)
      if (!deepEqualExceptTemplateId(prevSnapshot, this.resumeJson)) {
        // 回滚
        if (prevTemplateId) this.resumeJson.meta.templateId = prevTemplateId
        showToast('模板切换失败:检测到非法字段变更', { type: 'error' })
        return
      }

      this._persist()
    },

    // ─── 确认 / 忽略问题 ──────────────────────────────────────────

    /**
     * 「确认结构化结果」入口。
     * @param {boolean} force — 含缺失字段时由 ConfirmWithMissingModal 调用 confirmResume(true)。
     * @returns {{ok: boolean, missingFields: string[]}} ok=false 表示"含缺失,需要二次确认"
     */
    confirmResume(force = false) {
      if (!this.resumeJson) return { ok: false, missingFields: [] }
      const stillMissing = hasMissingFields(this.resumeJson)
      if (!stillMissing) {
        this.resumeJson.meta.confirmedByUser = true
        this._persist()
        showToast('已确认结构化结果', { type: 'success' })
        return { ok: true, missingFields: [] }
      }
      if (force) {
        this.resumeJson.meta.confirmedByUser = true
        this._persist()
        showToast('已强制确认(仍含缺失字段)', { type: 'success' })
        return { ok: true, missingFields: [] }
      }
      // 待二次确认
      return { ok: false, missingFields: listMissingPaths(this.resumeJson) }
    },

    /** 取消 confirmResume:不修改任何字段。 */
    cancelConfirm() {
      // no-op,保留以便组件层显式调用以表达意图
    },

    /** 关闭红色 fabrication 横幅。 */
    dismissFabricationBanner() {
      this.fabricationBannerDismissed = true
    },

    /** 用户在 missing_questions 卡片里点击"忽略"。本会话内立刻持久化,刷新后仍生效。 */
    dismissQuestion(idx) {
      this.dismissedQuestions = new Set([...this.dismissedQuestions, idx])
      // 关键:dismissedQuestions 走的是独立的 dismissedKey() 持久化通道,
      // 必须显式调 _persist() 才能落到 localStorage,否则刷新后 dismiss 失效。
      this._persist()
    },

    /** 重置 dismissed 列表(用于"撤回所有忽略")。同样需要持久化清空状态。 */
    clearDismissedQuestions() {
      this.dismissedQuestions = new Set()
      this._persist()
    },

    // ─── 持久化 ──────────────────────────────────────────

    _persist() {
      if (!this.resumeJson || !this.documentId) return
      const ok = safeWrite(storageKey(this.documentId), {
        version: STORAGE_VERSION,
        resumeJson: this.resumeJson,
        missingQuestions: this.missingQuestions,
        warnings: this.warnings,
        lastExtractAt: this.lastExtractAt
      })
      if (!ok) return
      // dismissed 列表单独写一份,避免 JSON 体积放大主键
      safeWrite(dismissedKey(this.documentId), Array.from(this.dismissedQuestions))
    },

    saveLocalStorage() {
      this._persist()
    },

    loadLocalStorage(documentId) {
      const cached = safeRead(storageKey(documentId))
      if (!cached || !isValidResumeJson(cached.resumeJson)) return false
      this.resumeJson = cached.resumeJson
      this.missingQuestions = Array.isArray(cached.missingQuestions) ? cached.missingQuestions.slice() : []
      this.warnings = Array.isArray(cached.warnings) ? cached.warnings.slice() : []
      this.lastExtractAt = cached.lastExtractAt || 0
      this.isDirty = false
      this.documentId = documentId
      const dismissed = safeRead(dismissedKey(documentId))
      this.dismissedQuestions = new Set(Array.isArray(dismissed) ? dismissed : [])
      this._snapshotForTemplateGuard = JSON.parse(JSON.stringify(this.resumeJson))
      return true
    },

    /** 清空当前文档的本地存储(谨慎使用)。 */
    clearLocalStorage(documentId = this.documentId) {
      if (!documentId) return
      safeRemove(storageKey(documentId))
      safeRemove(dismissedKey(documentId))
    },

    /** 完整 reset。 */
    $resetWorkspace() {
      this.resumeJson = null
      this.missingQuestions = []
      this.dismissedQuestions = new Set()
      this.warnings = []
      this.isDirty = false
      this.lastExtractAt = 0
      this.documentId = ''
      this.extracting = false
      this.fabricationBannerDismissed = false
      this.draftTruncated = false
      this._snapshotForTemplateGuard = null
      this._extractCounter = 0
      this.lastDebugRequestId = null
    }
  }
})
