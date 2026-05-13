/**
 * 全局文件格式常量模块
 * 统一管理全站允许的文件扩展名、MIME 类型、类型映射和校验函数
 */

export const ACCEPTED_EXTENSIONS = '.pdf,.doc,.docx,.txt,.jpg,.jpeg,.png,.webp'

export const ACCEPTED_MIME_TYPES = [
  'application/pdf',
  'application/msword',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'text/plain',
  'image/jpeg',
  'image/png',
  'image/webp'
]

export const FILE_TYPE_MAP = {
  pdf: { label: 'PDF', icon: 'FileText', color: 'text-red-400' },
  doc: { label: 'Word', icon: 'FileText', color: 'text-blue-400' },
  docx: { label: 'Word', icon: 'FileText', color: 'text-blue-400' },
  txt: { label: 'TXT', icon: 'FileText', color: 'text-gray-400' },
  jpg: { label: 'JPG', icon: 'Image', color: 'text-emerald-400' },
  jpeg: { label: 'JPEG', icon: 'Image', color: 'text-emerald-400' },
  png: { label: 'PNG', icon: 'Image', color: 'text-cyan-400' },
  webp: { label: 'WEBP', icon: 'Image', color: 'text-purple-400' }
}

export const MAX_FILE_SIZE = 20 * 1024 * 1024 // 20MB

/**
 * 根据文件名获取文件类型信息
 * @param {string} filename - 文件名
 * @returns {{ label: string, icon: string, color: string }}
 */
export function getFileType(filename) {
  const ext = filename.split('.').pop().toLowerCase()
  return FILE_TYPE_MAP[ext] || { label: ext.toUpperCase(), icon: 'File', color: 'text-gray-400' }
}

/**
 * 校验文件的扩展名和大小
 * @param {File} file - 文件对象
 * @returns {{ valid: boolean, error: string | null }}
 */
export function validateFile(file) {
  const ext = file.name.split('.').pop().toLowerCase()
  if (!FILE_TYPE_MAP[ext]) {
    return { valid: false, error: `不支持的文件格式: .${ext}` }
  }
  if (file.size > MAX_FILE_SIZE) {
    return { valid: false, error: `文件大小超过限制 (最大 20MB)` }
  }
  return { valid: true, error: null }
}
