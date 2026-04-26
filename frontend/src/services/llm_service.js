// src/services/llm_service.js
import axios from 'axios'

// 1. 规范：优先从环境变量读取，否则动态获取当前访问的协议和域名
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || `${window.location.protocol}//${window.location.hostname}:8000`

// 2. 创建专属的 axios 实例
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000, // AI 大模型解析通常很慢，务必设置至少 120s 超时防断连
})

/**
 * 核心技术栈要求：高扩展性的接口解耦设计（适配器模式）
 * 统一抽象大模型服务，实现业务逻辑与具体 API 隔离
 */
class LLMService {
  /**
   * AI 简历诊断分析
   * @param {File} file - 简历文件
   * @param {String} userId - 用户标识
   * @returns {Promise<Object>} 诊断结果
   */
  async diagnoseResume(file, userId) {
    const formData = new FormData()
    formData.append('userId', userId)
    // 严格按照师兄后端的字段名拼写（区分大小写）
    formData.append('ResumeFile', file) 

    try {
      const response = await apiClient.post('/jobResume/uploadJobResume', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      })
      return response.data
    } catch (error) {
      console.error('LLM Engine API Error:', error)
      throw error
    }
  }
}

export const llmService = new LLMService()