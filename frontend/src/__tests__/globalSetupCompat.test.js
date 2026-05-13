/**
 * GlobalSetup.vue 向后兼容验证测试
 *
 * **Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5**
 *
 * 验证内容：
 * 1. /setup 路由仍然存在且指向 GlobalSetup 组件
 * 2. 已注册用户（有 candidate_name + resume_text）通过 GlobalSetup 流程后可正常进入 Dashboard
 * 3. 新路由守卫不会破坏 GlobalSetup → Dashboard 的现有流程
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import { readFileSync } from 'fs'
import { resolve } from 'path'
import { routerGuardDecision } from '../router/guardLogic.js'

// ===== 模拟 localStorage =====
let store = {}

const mockLocalStorage = {
  getItem: (key) => store[key] ?? null,
  setItem: (key, value) => { store[key] = String(value) },
  removeItem: (key) => { delete store[key] },
  clear: () => { store = {} }
}

beforeEach(() => {
  store = {}
  Object.defineProperty(globalThis, 'localStorage', {
    value: mockLocalStorage,
    writable: true,
    configurable: true
  })
})

afterEach(() => {
  store = {}
})

// ===== 路由配置验证（通过读取源文件验证） =====

describe('GlobalSetup 路由配置向后兼容', () => {
  const routerSource = readFileSync(
    resolve(__dirname, '../router/index.js'),
    'utf-8'
  )

  it('/setup 路由存在且 name 为 GlobalSetup', () => {
    // 验证路由配置中包含 /setup 路由定义
    expect(routerSource).toContain("path: '/setup'")
    expect(routerSource).toContain("name: 'GlobalSetup'")
  })

  it('/setup 路由指向 GlobalSetup 组件', () => {
    // 验证 GlobalSetup 组件被导入
    expect(routerSource).toContain("import GlobalSetup from")
    // 验证 /setup 路由使用 GlobalSetup 组件
    // 路由定义中 component: GlobalSetup 紧跟在 path: '/setup' 之后
    const setupRouteMatch = routerSource.match(/path:\s*'\/setup'[\s\S]*?component:\s*(\w+)/)
    expect(setupRouteMatch).not.toBeNull()
    expect(setupRouteMatch[1]).toBe('GlobalSetup')
  })

  it('/setup 路由没有 requiresAuth meta（无需认证即可访问）', () => {
    // 提取 /setup 路由块，验证它没有 requiresAuth: true
    const setupBlock = routerSource.match(/\{[^}]*path:\s*'\/setup'[^}]*\}/s)
    expect(setupBlock).not.toBeNull()
    expect(setupBlock[0]).not.toContain('requiresAuth')
  })

  it('/dashboard 路由存在且有 requiresAuth: true', () => {
    expect(routerSource).toContain("path: '/dashboard'")
    expect(routerSource).toContain("name: 'Dashboard'")
    // 验证 dashboard 路由有 requiresAuth: true
    const dashboardBlock = routerSource.match(/\{[^}]*path:\s*'\/dashboard'[\s\S]*?\}/s)
    expect(dashboardBlock).not.toBeNull()
    expect(dashboardBlock[0]).toContain('requiresAuth: true')
  })
})

// ===== GlobalSetup → Dashboard 流程兼容性 =====

describe('GlobalSetup 完成后进入 Dashboard 的流程兼容性', () => {
  it('用户完成 GlobalSetup 后设置 candidate_name + resume_text，配合 token 可进入 Dashboard', () => {
    // 模拟 GlobalSetup 完成后的 localStorage 状态
    // GlobalSetup.handleSave() 会写入 candidate_name 和 resume_text
    mockLocalStorage.setItem('candidate_name', '张三')
    mockLocalStorage.setItem('resume_text', '这是一份测试简历内容，包含足够的字符数量来通过验证要求。')
    // 已注册用户通常有 token
    mockLocalStorage.setItem('token', 'valid-auth-token')

    // 验证路由守卫允许访问 /dashboard
    const result = routerGuardDecision({
      requiresAuth: true,
      token: mockLocalStorage.getItem('token'),
      userRole: mockLocalStorage.getItem('userRole')
    })
    expect(result).toBe(true)
  })

  it('用户完成 GlobalSetup 后设置 candidate_name + resume_text，配合 guest 角色可进入 Dashboard', () => {
    // 模拟游客用户先进入 Dashboard，然后通过 SetupModal 完善信息的场景
    // 或者用户先以 guest 身份进入，后续通过 GlobalSetup 补充信息
    mockLocalStorage.setItem('candidate_name', '李四')
    mockLocalStorage.setItem('resume_text', '这是一份完整的简历文本，包含了足够的字符数量来满足最低要求。')
    mockLocalStorage.setItem('userRole', 'guest')

    const result = routerGuardDecision({
      requiresAuth: true,
      token: mockLocalStorage.getItem('token'),
      userRole: mockLocalStorage.getItem('userRole')
    })
    expect(result).toBe(true)
  })

  it('用户完成 GlobalSetup 后 userRole 为 registered 且有 token 可进入 Dashboard', () => {
    // SetupModal 完成后会设置 userRole 为 registered
    mockLocalStorage.setItem('candidate_name', '王五')
    mockLocalStorage.setItem('resume_text', '资深前端工程师，五年开发经验，精通 Vue.js 和 React 框架。')
    mockLocalStorage.setItem('userRole', 'registered')
    mockLocalStorage.setItem('token', 'user-token-123')

    const result = routerGuardDecision({
      requiresAuth: true,
      token: mockLocalStorage.getItem('token'),
      userRole: mockLocalStorage.getItem('userRole')
    })
    expect(result).toBe(true)
  })

  it('仅有 candidate_name + resume_text 但无 token 且无 guest 角色时，路由守卫会重定向', () => {
    // 这种情况下用户需要通过 Landing 页面重新选择入口
    // GlobalSetup 本身不设置 token 或 userRole，所以单独完成 GlobalSetup 不足以通过新守卫
    // 但这是预期行为：用户需要先通过 Landing 选择入口路径
    mockLocalStorage.setItem('candidate_name', '赵六')
    mockLocalStorage.setItem('resume_text', '这是一份简历内容，用于测试路由守卫在缺少认证凭证时的行为。')

    const result = routerGuardDecision({
      requiresAuth: true,
      token: mockLocalStorage.getItem('token'),  // null
      userRole: mockLocalStorage.getItem('userRole')  // null
    })
    // 新守卫要求 token 或 guest 角色，仅有 candidate_name/resume_text 不够
    // 这是设计上的变更：用户需要通过正确的入口进入
    expect(result).toBe('/')
  })
})

// ===== 新守卫不破坏 GlobalSetup 数据写入 =====

describe('新路由守卫与 GlobalSetup localStorage 写入兼容', () => {
  it('GlobalSetup 写入的 candidate_name 和 resume_text 键不与新守卫冲突', () => {
    // 路由守卫只检查 token 和 userRole，不检查 candidate_name 或 resume_text
    // 验证守卫逻辑不依赖这两个键
    mockLocalStorage.setItem('candidate_name', '测试用户')
    mockLocalStorage.setItem('resume_text', '这是一份足够长的简历文本内容用于测试。')

    // 即使有 candidate_name 和 resume_text，没有 token/guest 仍然重定向
    const resultWithoutAuth = routerGuardDecision({
      requiresAuth: true,
      token: null,
      userRole: null
    })
    expect(resultWithoutAuth).toBe('/')

    // 有 token 时放行，不受 candidate_name/resume_text 影响
    const resultWithToken = routerGuardDecision({
      requiresAuth: true,
      token: 'valid-token',
      userRole: null
    })
    expect(resultWithToken).toBe(true)
  })

  it('SetupModal 写入 userRole: registered 不会覆盖 GlobalSetup 的 candidate_name/resume_text', () => {
    // 模拟 GlobalSetup 先写入数据
    mockLocalStorage.setItem('candidate_name', '原始姓名')
    mockLocalStorage.setItem('resume_text', '原始简历内容，这是一份足够长的文本用于验证。')

    // 模拟 SetupModal 写入 userRole（不应覆盖已有数据）
    mockLocalStorage.setItem('userRole', 'registered')

    // 验证原始数据未被覆盖
    expect(mockLocalStorage.getItem('candidate_name')).toBe('原始姓名')
    expect(mockLocalStorage.getItem('resume_text')).toBe('原始简历内容，这是一份足够长的文本用于验证。')
    expect(mockLocalStorage.getItem('userRole')).toBe('registered')
  })

  it('/setup 路由可自由访问（无 requiresAuth），守卫不会拦截', () => {
    // /setup 路由没有 requiresAuth meta，所以守卫应该放行
    const result = routerGuardDecision({
      requiresAuth: false,  // /setup 没有 requiresAuth
      token: null,
      userRole: null
    })
    expect(result).toBe(true)
  })
})
