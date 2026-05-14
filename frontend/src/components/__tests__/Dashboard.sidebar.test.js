// @vitest-environment jsdom

/**
 * Dashboard 侧边栏"全局资产"区块单元测试
 *
 * 测试范围：Requirements 1.1, 1.2, 1.3, 1.4
 * - 升学模式 (activeMode === 'education') 分支渲染
 * - 求职模式 (activeMode === 'job') 分支渲染
 * - estimatedScore / examRank 为空时显示 '未设置' 占位文本
 * - targetJob 为空时显示 '点击完善个人信息' 占位文本
 * - resumeText 非空时显示 '简历已就绪' 指示器
 * - resumeText 为空时不显示 '简历已就绪' 指示器
 *
 * 由于 Dashboard.vue 是包含 Three.js / ECharts / fetch 等重型依赖的大型组件，
 * 测试采用 mount + vi.mock + stubs 策略隔离外部依赖，专注于侧边栏模板逻辑。
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { useUserStore } from '@/stores/userStore'

// ─── 全局依赖 Mock ────────────────────────────────────────────────────────────

// Mock vue-router（Dashboard 内部使用 useRouter / useRoute）
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useRoute: () => ({ query: {} })
}))

// Mock Three.js / Vanta（3D 背景效果，不需要在 jsdom 中运行）
vi.mock('three', () => ({}))
vi.mock('vanta/dist/vanta.net.min', () => ({ default: vi.fn(() => ({ destroy: vi.fn() })) }))
vi.mock('vanta', () => ({ default: vi.fn(() => ({ destroy: vi.fn() })) }))

// Mock ECharts / vue-echarts（图表组件）
vi.mock('vue-echarts', () => ({ default: { template: '<div />' } }))
vi.mock('echarts', () => ({}))
vi.mock('echarts/core', () => ({ use: vi.fn() }))
vi.mock('echarts/renderers', () => ({ CanvasRenderer: {} }))
vi.mock('echarts/charts', () => ({ RadarChart: {} }))
vi.mock('echarts/components', () => ({ TitleComponent: {}, TooltipComponent: {}, LegendComponent: {} }))

// Mock lucide-vue-next（图标组件，全部替换为空 span）
vi.mock('lucide-vue-next', () => {
  const stub = { template: '<span />' }
  return {
    Bot: stub, Bookmark: stub, FileText: stub, MessageSquare: stub,
    Folder: stub, Settings: stub, Clock: stub, Puzzle: stub,
    Plus: stub, Search: stub, Paperclip: stub, MoreHorizontal: stub,
    ChevronDown: stub, ChevronLeft: stub, ChevronRight: stub,
    Upload: stub, CheckCircle: stub, X: stub, Loader2: stub,
    History: stub, Send: stub, Sparkles: stub, Mic: stub,
    GraduationCap: stub, Star: stub, Trash2: stub
  }
})

// Mock qrcode.vue
vi.mock('qrcode.vue', () => ({ default: { template: '<div />' } }))

// Mock @formkit/auto-animate（指令，不影响模板逻辑）
vi.mock('@formkit/auto-animate/vue', () => ({ vAutoAnimate: {} }))

// Mock marked（Markdown 渲染）
vi.mock('marked', () => ({ marked: (s) => s }))

// Mock llm_service（避免真实 fetch 调用）
vi.mock('@/services/llm_service.js', () => ({
  llmService: { chat: vi.fn() }
}))

// Mock fileConstants
vi.mock('@/utils/fileConstants.js', () => ({
  ACCEPTED_EXTENSIONS: [],
  validateFile: vi.fn(() => ({ valid: true }))
}))

// Mock ocrHelper（SetupModal 导入了 pdfjs-dist，jsdom 中 DOMMatrix 未定义会导致崩溃）
vi.mock('@/utils/ocrHelper.js', () => ({
  parseFile: vi.fn(() => Promise.resolve(''))
}))

// Mock fetch 全局（Dashboard 在 onMounted 中调用 loadHistory / loadLatestRadarData）
global.fetch = vi.fn(() =>
  Promise.resolve({
    ok: true,
    json: () => Promise.resolve({ records: [] }),
    body: null
  })
)

// Mock localStorage
const localStorageMock = (() => {
  let store = {}
  return {
    getItem: (key) => store[key] ?? null,
    setItem: (key, value) => { store[key] = String(value) },
    removeItem: (key) => { delete store[key] },
    clear: () => { store = {} }
  }
})()
Object.defineProperty(window, 'localStorage', { value: localStorageMock })

// ─── 辅助函数 ─────────────────────────────────────────────────────────────────

/**
 * 挂载 Dashboard 组件，并将 userStore 初始化为指定状态。
 * 使用 shallowMount 以避免子组件（CyberRadarChart、SetupModal 等）的渲染开销。
 */
async function mountDashboard(storeOverrides = {}) {
  // 每次挂载前重置 localStorage，避免测试间状态污染
  localStorageMock.clear()

  const pinia = createPinia()
  setActivePinia(pinia)

  // 动态导入 Dashboard（确保 mock 已注册后再导入）
  const { default: Dashboard } = await import('@/Dashboard.vue')

  const wrapper = mount(Dashboard, {
    global: {
      plugins: [pinia],
      stubs: {
        // 将所有子组件替换为空 div，专注测试 Dashboard 自身模板
        CyberRadarChart: { template: '<div data-stub="CyberRadarChart" />' },
        SetupModal: { template: '<div data-stub="SetupModal" />' },
        DataSourceModal: { template: '<div data-stub="DataSourceModal" />' },
        // lucide 图标组件统一 stub
        Bot: { template: '<span />' },
        Bookmark: { template: '<span />' },
        FileText: { template: '<span />' },
        MessageSquare: { template: '<span />' },
        Folder: { template: '<span />' },
        Settings: { template: '<span />' },
        Clock: { template: '<span />' },
        Puzzle: { template: '<span />' },
        Plus: { template: '<span />' },
        Search: { template: '<span />' },
        Paperclip: { template: '<span />' },
        MoreHorizontal: { template: '<span />' },
        ChevronDown: { template: '<span />' },
        ChevronLeft: { template: '<span />' },
        ChevronRight: { template: '<span />' },
        Upload: { template: '<span />' },
        CheckCircle: { template: '<span />' },
        X: { template: '<span />' },
        Loader2: { template: '<span />' },
        History: { template: '<span />' },
        Send: { template: '<span />' },
        Sparkles: { template: '<span />' },
        Mic: { template: '<span />' },
        GraduationCap: { template: '<span />' },
        Star: { template: '<span />' },
        Trash2: { template: '<span />' }
      }
    }
  })

  // 挂载后直接修改 store 状态（绕过 localStorage，直接驱动响应式渲染）
  const userStore = useUserStore()
  Object.assign(userStore, storeOverrides)

  // 等待 Vue 响应式更新完成
  await wrapper.vm.$nextTick()

  return { wrapper, userStore }
}

// ─── 测试套件 ─────────────────────────────────────────────────────────────────

describe('Dashboard 侧边栏 — 全局资产区块', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorageMock.clear()
  })

  // ── Test 1: 升学模式分支渲染 ──────────────────────────────────────────────

  it('Test 1: activeMode === "education" 时渲染升学模式分支（examTypeLabel 徽章 + 分数/排位）', async () => {
    const { wrapper } = await mountDashboard({
      activeMode: 'education',
      examType: 'kaoyan',
      estimatedScore: '380',
      examRank: '5000'
    })

    const html = wrapper.html()

    // 升学模式分支应包含 examTypeLabel 徽章（考研）
    expect(html).toContain('考研')

    // 应显示分数和排位
    expect(html).toContain('380')
    expect(html).toContain('5000')

    // 求职模式专属文本不应出现
    expect(html).not.toContain('点击完善个人信息')
  })

  // ── Test 2: 求职模式分支渲染 ──────────────────────────────────────────────

  it('Test 2: activeMode === "job" 时渲染求职模式分支（targetJob 文本）', async () => {
    const { wrapper } = await mountDashboard({
      activeMode: 'job',
      targetJob: 'Java 后端工程师',
      resumeText: ''
    })

    const html = wrapper.html()

    // 求职模式应显示目标岗位
    expect(html).toContain('Java 后端工程师')

    // 升学模式专属徽章不应出现（examType 为空，examTypeLabel 为 '未设置'，但整个升学分支不应渲染）
    // 验证方式：分数/排位行不应出现
    expect(html).not.toContain('分数:')
    expect(html).not.toContain('排位:')
  })

  // ── Test 3: 升学模式 estimatedScore 为空时显示 '未设置' ──────────────────

  it('Test 3: activeMode === "education" 且 estimatedScore 为空时，分数位置显示 "未设置"', async () => {
    const { wrapper } = await mountDashboard({
      activeMode: 'education',
      examType: 'gaokao',
      estimatedScore: '',   // 空值
      examRank: '12000'
    })

    const html = wrapper.html()

    // 分数位置应显示 '未设置'
    expect(html).toContain('未设置')

    // 排位有值，应正常显示
    expect(html).toContain('12000')
  })

  // ── Test 4: 升学模式 examRank 为空时显示 '未设置' ────────────────────────

  it('Test 4: activeMode === "education" 且 examRank 为空时，排位位置显示 "未设置"', async () => {
    const { wrapper } = await mountDashboard({
      activeMode: 'education',
      examType: 'zhuanchaben',
      estimatedScore: '420',
      examRank: ''   // 空值
    })

    const html = wrapper.html()

    // 排位位置应显示 '未设置'
    expect(html).toContain('未设置')

    // 分数有值，应正常显示
    expect(html).toContain('420')
  })

  // ── Test 5: 求职模式 targetJob 为空时显示占位文本 ────────────────────────

  it('Test 5: activeMode === "job" 且 targetJob 为空时，显示 "点击完善个人信息"', async () => {
    const { wrapper } = await mountDashboard({
      activeMode: 'job',
      targetJob: '',   // 空值
      resumeText: ''
    })

    const html = wrapper.html()

    expect(html).toContain('点击完善个人信息')
  })

  // ── Test 6: 求职模式 resumeText 非空时显示 '简历已就绪' ──────────────────

  it('Test 6: activeMode === "job" 且 resumeText 非空时，显示 "简历已就绪" 指示器', async () => {
    const { wrapper } = await mountDashboard({
      activeMode: 'job',
      targetJob: '前端工程师',
      resumeText: '这是一份简历内容'   // 非空
    })

    const html = wrapper.html()

    expect(html).toContain('简历已就绪')
  })

  // ── Test 7: 求职模式 resumeText 为空时不显示 '简历已就绪' ────────────────

  it('Test 7: activeMode === "job" 且 resumeText 为空时，不显示 "简历已就绪" 指示器', async () => {
    const { wrapper } = await mountDashboard({
      activeMode: 'job',
      targetJob: '前端工程师',
      resumeText: ''   // 空值
    })

    const html = wrapper.html()

    expect(html).not.toContain('简历已就绪')
  })
})
