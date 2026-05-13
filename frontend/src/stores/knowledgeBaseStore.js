import { defineStore } from 'pinia'

/**
 * 知识库资产舱 Store
 * 管理知识库文件列表状态、上传进度、OCR 解析状态
 *
 * @typedef {Object} FileItem
 * @property {string} id - 唯一标识 (crypto.randomUUID)
 * @property {string} name - 文件名
 * @property {string} ext - 扩展名 (小写)
 * @property {number} size - 文件大小 (bytes)
 * @property {'pending'|'parsing'|'completed'|'failed'} status - OCR 解析状态
 * @property {string} extractedText - OCR 提取的文本内容
 * @property {string} errorMessage - 失败时的错误信息
 * @property {number} createdAt - 上传时间戳
 */
export const useKnowledgeBaseStore = defineStore('knowledgeBase', {
  state: () => ({
    /** @type {FileItem[]} */
    files: [],
    isUploading: false
  }),

  getters: {
    /** 文件总数 */
    fileCount: (state) => state.files.length,

    /** 正在解析中的文件列表 */
    parsingFiles: (state) => state.files.filter(f => f.status === 'parsing'),

    /** 已完成解析的文件列表 */
    completedFiles: (state) => state.files.filter(f => f.status === 'completed')
  },

  actions: {
    /**
     * 添加新文件到列表头部（最新的在前）
     * @param {FileItem} fileMetadata - 文件元数据对象
     */
    addFile(fileMetadata) {
      this.files.unshift(fileMetadata)
    },

    /**
     * 更新文件的解析状态
     * @param {string} id - 文件唯一标识
     * @param {'pending'|'parsing'|'completed'|'failed'} status - 新状态
     * @param {string} [extractedText=''] - OCR 提取的文本
     * @param {string} [errorMessage=''] - 错误信息
     */
    updateFileStatus(id, status, extractedText = '', errorMessage = '') {
      const file = this.files.find(f => f.id === id)
      if (file) {
        file.status = status
        if (extractedText) file.extractedText = extractedText
        if (errorMessage) file.errorMessage = errorMessage
      }
    },

    /**
     * 从列表中移除文件
     * @param {string} id - 文件唯一标识
     */
    removeFile(id) {
      this.files = this.files.filter(f => f.id !== id)
    }
  }
})
