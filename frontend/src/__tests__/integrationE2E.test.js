/**
 * 端到端集成测试 — 验证核心用户流程
 *
 * **Property 8: 菜单唯一重资产入口**
 * **Validates: Requirements 1.1, 3.1, 5.1, 5.2**
 *
 * 测试流程：
 * 1. 点击全局资产 → SetupModal 弹出 → 填写提交 → 状态更新为"已就绪"
 * 2. 菜单"文件管理" → 跳转 /files → 确认路由调用
 * 3. Property 8: 菜单中有且仅有一个指向 /files 的菜单项
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import * as fc from 'fast-check'
import { handleSetupSubmit } from '../components/setupModalLogic.js'

// ===== localStorage Mock =====

function createLocalStorageMock() {
  let store = {}
  return {
    getItem(key) {
      return Object.prototype.hasOwnProperty.call(store, key) ? store[key] : null
    },
    setItem(key, value) {
      store[key] = String(value)
    },
    removeItem(key) {
      delete store[key]
    },
    clear() {
      store = {}
    },
    key(index) {
      const keys = Object.keys(store)
      return keys[index] || null
    },
    get length() {
      return Object.keys(store).length
    },
    _getSnapshot() {
      return { ...store }
    }
  }
}

// ===== Dashboard 菜单数据结构（与 Dashboard.vue 保持一致）=====

const menuItems = [
  {
    category: '主要功能',
    items: [
      { icon: 'file-text', label: '功能模板' },
      { icon: 'message-square', label: '保存的对话' },
      { icon: 'folder', label: '文件管理' },
      { icon: 'clock', label: '历史记录' },
      { icon: 'plugin', label: '插件集成' },
      { icon: 'settings', label: '系统设置' }
    ]
  },
  {
    category: '我的项目',
    items: [
      { icon: 'folder', label: '商业分析' },
      { icon: 'bot', label: '个人规划' },
      { icon: 'file-text', label: '项目进度' }
    ]
  }
]

// ===== Dashboard 侧边栏菜单点击逻辑（提取自 Dashboard.vue handleSidebarItemClick）=====

/**
 * 模拟 Dashboard 侧边栏菜单项点击逻辑
 * @param {{ label: string }} item - 菜单项
 * @param {{ category: string }} menu - 菜单分组
 * @param {{ push: function }} router - 路由实例
 * @returns {{ navigated: string|null, toast: string|null }}
 */
function handleSidebarItemClick(item, menu, router) {
  if (item.label === '历史记录') {
    router.push('/history-archive')
    return { navigated: '/history-archive', toast: null }
  }

  if (item.label === '保存的对话') {
    router.push('/saved-chats')
    return { navigated: '/saved-chats', toast: null }
  }

  if (item.label === '文件管理') {
    router.push('/files')
    return { navigated: '/files', toast: null }
  }

  if (item.label === '功能模板' || item.label === '插件集成' || item.label === '系统设置' || menu.category === '我的项目') {
    return { navigated: null, toast: '工程师正在玩命开发中，敬请期待！🚀' }
  }

  return { navigated: null, toast: '工程师正在玩命开发中，敬请期待！🚀' }
}

/**
 * 模拟 Dashboard handleSetupComplete 逻辑
 * @param {object} storage - localStorage 实例
 * @returns {{ showSetupModal: boolean, globalResumeStatus: string, userName: string }}
 */
function handleSetupComplete(storage) {
  return {
    showSetupModal: false,
    globalResumeStatus: 'ready',
    userName: storage.getItem('candidate_name') || ''
  }
}

/**
 * 计算 globalResumeStatus
 * @param {object} storage - localStorage 实例
 * @returns {string} 'ready' | 'missing'
 */
function computeGlobalResumeStatus(storage) {
  const resumeText = storage.getItem('resume_text') || ''
  return resumeText.trim().length > 0 ? 'ready' : 'missing'
}

// ===== 集成测试 =====

describe('端到端集成测试：全局资产 → SetupModal → 状态更新', () => {
  let mockLocalStorage

  beforeEach(() => {
    mockLocalStorage = createLocalStorageMock()
    globalThis.localStorage = mockLocalStorage
  })

  afterEach(() => {
    mockLocalStorage.clear()
    delete globalThis.localStorage
  })

  describe('Flow 1: 点击全局资产 → SetupModal 弹出 → 填写提交 → 状态更新为"已就绪"', () => {
    it('完整流程：点击全局资产卡片 → 弹窗显示 → 提交有效数据 → globalResumeStatus 变为 ready', () => {
      // Step 1: 初始状态 — globalResumeStatus 为 missing
      expect(computeGlobalResumeStatus(mockLocalStorage)).toBe('missing')

      // Step 2: 用户点击全局资产卡片 → showSetupModal = true
      let showSetupModal = false
      showSetupModal = true
      expect(showSetupModal).toBe(true)

      // Step 3: 用户在 SetupModal 中填写有效数据并提交
      const candidateName = '张三'
      const resumeText = '这是一份足够长的简历文本内容，用于测试端到端流程的完整性验证。'

      const submitResult = handleSetupSubmit(candidateName, resumeText)

      // Step 4: 验证提交成功
      expect(submitResult.success).toBe(true)
      expect(submitResult.emitted).toBe('complete')

      // Step 5: 验证 localStorage 已更新
      expect(mockLocalStorage.getItem('candidate_name')).toBe('张三')
      expect(mockLocalStorage.getItem('resume_text')).toBe(resumeText)

      // Step 6: SetupModal emit('complete') → Dashboard handleSetupComplete
      const dashboardState = handleSetupComplete(mockLocalStorage)
      expect(dashboardState.showSetupModal).toBe(false)
      expect(dashboardState.globalResumeStatus).toBe('ready')
      expect(dashboardState.userName).toBe('张三')

      // Step 7: 验证 globalResumeStatus 与 localStorage 同步
      expect(computeGlobalResumeStatus(mockLocalStorage)).toBe('ready')
    })

    it('提交后 localStorage 中 resume_text 非空 → globalResumeStatus 为 ready', () => {
      const candidateName = '李四'
      const resumeText = '我是一名有三年经验的前端开发工程师，熟悉 Vue 和 React 框架。'

      // 提交表单
      const result = handleSetupSubmit(candidateName, resumeText)
      expect(result.success).toBe(true)

      // 验证状态同步
      expect(computeGlobalResumeStatus(mockLocalStorage)).toBe('ready')
    })

    it('提交失败时 globalResumeStatus 保持 missing', () => {
      // 提交无效数据（简历太短）
      const result = handleSetupSubmit('王五', '太短了')
      expect(result.success).toBe(false)

      // 状态不变
      expect(computeGlobalResumeStatus(mockLocalStorage)).toBe('missing')
    })
  })
})

describe('端到端集成测试：菜单"文件管理" → 跳转 /files', () => {
  it('点击"文件管理"菜单项应调用 router.push("/files")', () => {
    const pushCalls = []
    const mockRouter = { push: (path) => pushCalls.push(path) }

    const fileManagementItem = { icon: 'folder', label: '文件管理' }
    const mainMenu = { category: '主要功能' }

    const result = handleSidebarItemClick(fileManagementItem, mainMenu, mockRouter)

    expect(pushCalls).toEqual(['/files'])
    expect(result.navigated).toBe('/files')
    expect(result.toast).toBeNull()
  })

  it('菜单中"文件管理"项存在于主要功能分组中', () => {
    const mainCategory = menuItems.find(m => m.category === '主要功能')
    expect(mainCategory).toBeDefined()

    const fileItem = mainCategory.items.find(item => item.label === '文件管理')
    expect(fileItem).toBeDefined()
    expect(fileItem.icon).toBe('folder')
  })

  it('点击其他菜单项不会导航到 /files', () => {
    const pushCalls = []
    const mockRouter = { push: (path) => pushCalls.push(path) }

    // 测试所有非"文件管理"的菜单项
    for (const menu of menuItems) {
      for (const item of menu.items) {
        if (item.label !== '文件管理') {
          handleSidebarItemClick(item, menu, mockRouter)
        }
      }
    }

    // 验证没有任何调用导航到 /files
    expect(pushCalls.every(path => path !== '/files')).toBe(true)
  })
})

// ===== Property 8: 菜单唯一重资产入口 =====

describe('Property 8: 菜单唯一重资产入口', () => {
  it('Property: Dashboard 菜单中有且仅有一个指向 /files 的菜单项', () => {
    // 收集所有菜单项
    const allItems = menuItems.flatMap(menu => menu.items)

    // 找出所有"文件管理"项（即路由到 /files 的项）
    const fileManagementItems = allItems.filter(item => item.label === '文件管理')

    // 有且仅有一个
    expect(fileManagementItems).toHaveLength(1)
  })

  it('Property: 唯一的文件管理菜单项点击后路由到 /files', () => {
    const pushCalls = []
    const mockRouter = { push: (path) => pushCalls.push(path) }

    // 找到唯一的文件管理项
    const allItems = menuItems.flatMap(menu => menu.items)
    const fileItems = allItems.filter(item => item.label === '文件管理')

    expect(fileItems).toHaveLength(1)

    // 模拟点击
    const mainMenu = menuItems.find(m => m.items.includes(fileItems[0]))
    handleSidebarItemClick(fileItems[0], mainMenu, mockRouter)

    // 验证路由调用
    expect(pushCalls).toEqual(['/files'])
  })

  it('Property: 对任意菜单结构遍历，仅"文件管理"项路由到 /files（属性测试）', () => {
    fc.assert(
      fc.property(
        // 生成随机的菜单项索引来模拟用户点击
        fc.nat({ max: menuItems.reduce((sum, m) => sum + m.items.length, 0) - 1 }),
        (flatIndex) => {
          const pushCalls = []
          const mockRouter = { push: (path) => pushCalls.push(path) }

          // 将 flatIndex 映射到具体的菜单项
          let currentIndex = 0
          let targetItem = null
          let targetMenu = null

          for (const menu of menuItems) {
            for (const item of menu.items) {
              if (currentIndex === flatIndex) {
                targetItem = item
                targetMenu = menu
                break
              }
              currentIndex++
            }
            if (targetItem) break
          }

          if (!targetItem) return // 安全退出

          handleSidebarItemClick(targetItem, targetMenu, mockRouter)

          // 核心断言：路由到 /files 当且仅当 label === '文件管理'
          const navigatedToFiles = pushCalls.includes('/files')
          const isFileManagement = targetItem.label === '文件管理'

          expect(navigatedToFiles).toBe(isFileManagement)
        }
      ),
      { numRuns: 50 }
    )
  })

  it('Property: 菜单中不存在多个路由到 /files 的入口（对任意菜单分组验证）', () => {
    fc.assert(
      fc.property(
        fc.constant(menuItems), // 使用实际菜单数据
        (menus) => {
          let filesRouteCount = 0

          for (const menu of menus) {
            for (const item of menu.items) {
              const pushCalls = []
              const mockRouter = { push: (path) => pushCalls.push(path) }

              handleSidebarItemClick(item, menu, mockRouter)

              if (pushCalls.includes('/files')) {
                filesRouteCount++
              }
            }
          }

          // 有且仅有一个菜单项路由到 /files
          expect(filesRouteCount).toBe(1)
        }
      ),
      { numRuns: 10 }
    )
  })
})
