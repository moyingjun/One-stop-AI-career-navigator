/**
 * resumeBuilderClient.js — Resume Builder 唯一 HTTP 客户端
 *
 * 严格红线(Requirement 10.4 / 11.5):
 *   - 仅命中 `/api/document/extract-resume` 一个端点
 *   - 严禁触达 /api/resume / /api/interview / /api/career / /api/rag /
 *             /api/knowledge / /api/agent / /api/history
 *   - 失败时回退到本地安全骨架,确保 Workspace 不白屏
 *
 * 满足:
 *   - 4.1 / 4.7: 走 /api/document/extract-resume,不直接调 LLM
 *   - 11.2: HTTP 非 2xx / JSON 解析失败 / 缺顶级 Section 时回退安全骨架
 */

import { getAuthHeaders } from '@/services/authService.js'
import { buildSafeSkeleton, isValidResumeJson } from '@/utils/resumeJsonSchema.js'

const ENDPOINT = '/api/document/extract-resume'

/**
 * 构造客户端 fallback:HTTP 失败 / JSON 解析失败 / 响应非法时使用。
 *
 * @param {string} documentId
 * @param {string[]} extraWarnings
 */
function buildClientFallback(documentId, extraWarnings = []) {
  return {
    success: false,
    resume_json: buildSafeSkeleton(documentId),
    warnings: extraWarnings.length > 0 ? extraWarnings.slice() : ['json_parse_failed'],
    missing_questions: [],
    debug_request_id: null
  }
}

/**
 * 计算 Resume_JSON 各 Section 的条目数,用于诊断日志。
 *
 * @param {object|null} json
 */
function buildCountsForLog(json) {
  if (!json || typeof json !== 'object') return {}
  const get = (k) => Array.isArray(json?.[k]?.items) ? json[k].items.length : 0
  return {
    education: get('education'),
    projects: get('projects'),
    experience: get('experience'),
    skills: get('skills'),
    awards: get('awards'),
    certificates: get('certificates')
  }
}

/**
 * 调用 Extract_Resume_API,把草稿一次性抽取为 Resume_JSON。
 *
 * @param {object} payload
 * @param {string} payload.document_id
 * @param {string} payload.plain_text
 * @param {object} payload.content_json
 * @param {string|null} [payload.provider_id]
 *
 * @returns {Promise<{success: boolean, resume_json: object, warnings: string[], missing_questions: string[], debug_request_id: string|null}>}
 */
export async function extractResumeFromDraft(payload) {
  const documentId = (payload && payload.document_id) || ''

  let resp
  try {
    resp = await fetch(ENDPOINT, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders()
      },
      body: JSON.stringify({
        document_id: documentId,
        plain_text: typeof payload?.plain_text === 'string' ? payload.plain_text : '',
        content_json: payload?.content_json && typeof payload.content_json === 'object'
          ? payload.content_json
          : {},
        provider_id: payload?.provider_id || null
      })
    })
  } catch (err) {
    // 网络层失败(断网 / CORS / fetch 异常)
    console.warn('[resumeBuilderClient] fetch 失败,回退安全骨架:', err)
    return buildClientFallback(documentId)
  }

  if (!resp.ok) {
    console.warn('[resumeBuilderClient] HTTP 非 2xx:', resp.status)
    return buildClientFallback(documentId)
  }

  let data
  try {
    data = await resp.json()
  } catch (err) {
    console.warn('[resumeBuilderClient] 响应 JSON 解析失败:', err)
    return buildClientFallback(documentId)
  }

  if (!data || typeof data !== 'object') {
    return buildClientFallback(documentId)
  }
  if (!isValidResumeJson(data.resume_json)) {
    return buildClientFallback(documentId)
  }

  const result = {
    success: !!data.success,
    resume_json: data.resume_json,
    warnings: Array.isArray(data.warnings) ? data.warnings.slice() : [],
    missing_questions: Array.isArray(data.missing_questions) ? data.missing_questions.slice() : [],
    debug_request_id: typeof data.debug_request_id === 'string' && data.debug_request_id
      ? data.debug_request_id
      : null
  }

  // 取证日志(浏览器 console 可见;后端 debug/resume_extract/{rid}_*.json 一一对应)
  try {
    console.log(
      '[resume-builder] request_id=%s success=%s warnings=%o counts=%o',
      result.debug_request_id || '(no-debug)',
      result.success,
      result.warnings,
      buildCountsForLog(result.resume_json)
    )
  } catch {
    /* noop:console 不可用时静默 */
  }

  return result
}
