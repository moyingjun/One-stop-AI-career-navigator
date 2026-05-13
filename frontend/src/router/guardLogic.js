/**
 * 路由守卫核心决策逻辑（纯函数，便于测试）
 *
 * @param {object} params
 * @param {boolean} params.requiresAuth - 目标路由是否需要认证
 * @param {string|null} params.token - localStorage 中的 token 值
 * @param {string|null} params.userRole - localStorage 中的 userRole 值
 * @returns {true | '/'} - true 表示放行，'/' 表示重定向至首页
 */
export function routerGuardDecision({ requiresAuth, token, userRole }) {
  // 无需认证的页面直接放行
  if (!requiresAuth) {
    return true
  }

  // token 非空且非纯空白字符串时放行
  if (token && token.trim().length > 0) {
    return true
  }

  // guest 角色放行
  if (userRole === 'guest') {
    return true
  }

  // 两者均不满足，重定向至首页
  return '/'
}
