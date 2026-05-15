/**
 * kbService.js — 知识库 API 客户端
 *
 * 封装所有与知识库相关的 HTTP 请求：
 *   - uploadFile(file)         — 上传文件入库（FormData + JWT）
 *   - getKnowledgeList()       — 查询当前用户的知识库列表
 *   - deleteKnowledgeSource(sourceName) — 删除指定来源的所有分块
 *
 * 🚨 安全铁律：
 *   - 所有请求必须携带 Authorization: Bearer <token>（由 getAuthHeaders 注入）
 *   - user_id 由后端从 JWT Token 中解析，前端无需传递
 *   - 上传使用 FormData，不得将文件内容序列化为 JSON
 */

import { getAuthHeaders } from '@/services/authService'

const API_BASE = '/api'

/**
 * 上传文件到知识库
 *
 * @param {File} file — 原生 File 对象（PDF / DOCX / TXT / MD）
 * @returns {Promise<{ success: boolean, source_name: string, chunk_count: number, message: string }>}
 * @throws {Error} 上传失败时抛出，message 为后端 detail 字符串
 */
export async function uploadFile(file) {
  const formData = new FormData()
  formData.append('file', file)

  const response = await fetch(`${API_BASE}/kb/upload`, {
    method: 'POST',
    headers: {
      // ⚠️ 不要手动设置 Content-Type，让浏览器自动附加 multipart boundary
      ...getAuthHeaders(),
    },
    body: formData,
  })

  if (!response.ok) {
    let detail = `上传失败（HTTP ${response.status}）`
    try {
      const body = await response.json()
      if (body?.detail) detail = body.detail
    } catch { /* 响应体非 JSON */ }
    throw new Error(detail)
  }

  return response.json()
}

/**
 * 获取当前用户的知识库来源列表
 *
 * @returns {Promise<{ success: boolean, sources: Array<{ source_name: string, chunk_count: number }>, total_chunks: number }>}
 * @throws {Error} 请求失败时抛出
 */
export async function getKnowledgeList() {
  const response = await fetch(`${API_BASE}/kb/list`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    },
  })

  if (!response.ok) {
    let detail = `获取列表失败（HTTP ${response.status}）`
    try {
      const body = await response.json()
      if (body?.detail) detail = body.detail
    } catch { /* 响应体非 JSON */ }
    throw new Error(detail)
  }

  return response.json()
}

/**
 * 删除指定来源的所有知识库分块
 *
 * @param {string} sourceName — 要删除的来源名称（文件名）
 * @returns {Promise<{ success: boolean, deleted_chunks: number, message: string }>}
 * @throws {Error} 删除失败时抛出
 */
export async function deleteKnowledgeSource(sourceName) {
  const params = new URLSearchParams({ source_name: sourceName })

  const response = await fetch(`${API_BASE}/kb/source?${params.toString()}`, {
    method: 'DELETE',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    },
  })

  if (!response.ok) {
    let detail = `删除失败（HTTP ${response.status}）`
    try {
      const body = await response.json()
      if (body?.detail) detail = body.detail
    } catch { /* 响应体非 JSON */ }
    throw new Error(detail)
  }

  return response.json()
}
