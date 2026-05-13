/**
 * SetupModal 表单提交逻辑 — 提取为可测试的纯函数
 *
 * 从 SetupModal.vue 中提取的核心验证与持久化逻辑，
 * 便于属性测试直接调用而无需挂载 Vue 组件。
 */

/**
 * 验证并提交 SetupModal 表单数据
 * @param {string} candidateName - 用户输入的姓名
 * @param {string} resumeText - 用户输入的简历文本
 * @returns {{ success: boolean, errors: { nameError: string, resumeError: string }, emitted: string|null }}
 *   - success: 是否提交成功
 *   - errors: 验证错误信息
 *   - emitted: 触发的事件名称（'complete' 或 null）
 */
export function handleSetupSubmit(candidateName, resumeText) {
  let nameError = ''
  let resumeError = ''
  let hasError = false

  // 验证姓名
  const trimmedName = candidateName.trim()
  if (!trimmedName) {
    nameError = '请填写姓名'
    hasError = true
  } else if (trimmedName.length > 50) {
    nameError = '姓名不能超过 50 个字符'
    hasError = true
  }

  // 验证简历
  const trimmedResume = resumeText.trim()
  if (trimmedResume.length < 20) {
    resumeError = '简历内容至少需要 20 个字符'
    hasError = true
  }

  if (hasError) {
    return {
      success: false,
      errors: { nameError, resumeError },
      emitted: null
    }
  }

  // 验证通过，写入 localStorage
  localStorage.setItem('candidate_name', trimmedName.slice(0, 50))
  localStorage.setItem('resume_text', trimmedResume.slice(0, 10000))
  localStorage.setItem('userRole', 'registered')

  return {
    success: true,
    errors: { nameError: '', resumeError: '' },
    emitted: 'complete'
  }
}
