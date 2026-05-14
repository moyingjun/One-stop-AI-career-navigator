// @vitest-environment jsdom

/**
 * PremiumInterview.vue — sendMessage() SSE 集成单元测试
 *
 * 测试范围：Requirements 5.2, 5.3
 * - Test 1: onChunk 回调将多个片段累积追加到最后一条 AI 消息的 content 字段
 * - Test 2: onError 回调将错误文本追加到最后一条 AI 消息的 content 字段（内联展示）
 * - Test 3: 包含 [SCORE_UPDATE] 标签的 chunk 被正确解析：标签从显示内容中移除，radarScores 被更新
 *
 * 策略：
 * - vi.mock('@/services/llm_service.js') 拦截 streamInterviewChat，手动调用 onChunk / onError
 * - 挂载 PremiumInterview.vue，通过 wrapper.vm 直接操作响应式状态
 * - 所有重型依赖（Three.js、ECharts、vue-router 等）均被 mock 掉
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

// ─── 全局依赖 Mock ────────────────────────────────────────────────────────────

// Mock streamInterviewChat — 核心 mock，每个测试用例会覆盖其实现
vi.mock('@/services/llm_service.js', () => ({
  streamInterviewChat: vi.fn(),
  API_BASE_URL: 'http://127.0.0.1:8000/api',
  ensureUUID: vi.fn(() => 'test-uuid'),
  callAgent: vi.fn(),
  callAgentAsync: vi.fn(),
  llmService: {}
}))

// Mock vue-router（PremiumInterview 内部使用 useRouter / useRoute）
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useRoute: () => ({ query: {} })
}))

// Mock Three.js / Vanta（3D 背景效果，jsdom 中无法运行）
vi.mock('three', () => ({}))
vi.mock('vanta/dist/vanta.net.min', () => ({ default: vi.fn(() => ({ destroy: vi.fn() })) }))
vi.mock('vanta', () => ({ default: vi.fn(() => ({ destroy: vi.fn() })) }))

// Mock ECharts / vue-echarts（图表组件）
vi.mock('vue-echarts', () => ({ default: { template: '<div />' } }))
vi.mock('echarts', () => ({}))
vi.mock('echarts/core', () => ({ use: vi.fn() }))
vi.mock('echarts/renderers', () => ({ CanvasRenderer: {} }))
vi.mock('echarts/charts', () => ({ RadarChart: {} }))
vi.mock('echarts/components', () => ({
  TitleComponent: {},
  TooltipComponent: {},
  LegendComponent: {},
  RadarComponent: {}
}))

// Mock lucide-vue-next（图标组件，全部替换为空 span）
vi.mock('lucide-vue-next', () => {
  const stub = { template: '<span />' }
  return {
    ArrowLeft: stub, Send: stub, UserCircle: stub, Cpu: stub,
    Loader2: stub, Shield: stub, AlertTriangle: stub, X: stub,
    Sprout: stub, Briefcase: stub, Flame: stub
  }
})

// Mock marked（Markdown 渲染，直接返回原字符串）
// PremiumInterview 使用 `import { marked } from 'marked'` 后调用 `marked.parse(str)`
// 因此 mock 需要将 `marked` 导出为带有 `parse` 方法的对象
vi.mock('marked', () => ({ marked: { parse: (s) => s } }))

// Mock fetch 全局（initInterview 在 onMounted 中调用 fetch）
global.fetch = vi.fn(() =>
  Promise.resolve({
    ok: false,
    json: () => Promise.resolve({}),
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
Object.defineProperty(window, 'localStorage', { value: localStorageMock, writable: true })

// Mock window.location（llm_service.js 顶层读取 hostname）
Object.defineProperty(window, 'location', {
  value: { hostname: 'localhost' },
  writable: true
})

// ─── 辅助函数 ─────────────────────────────────────────────────────────────────

/**
 * 挂载 PremiumInterview 组件。
 * 由于组件在 onMounted 中调用 initInterview()（会弹出难度选择弹窗），
 * 我们在挂载后直接关闭弹窗并设置必要的初始状态，以便测试 sendMessage()。
 */
async function mountPremiumInterview() {
  localStorageMock.clear()

  const pinia = createPinia()
  setActivePinia(pinia)

  const { default: PremiumInterview } = await import('@/PremiumInterview.vue')

  const wrapper = mount(PremiumInterview, {
    global: {
      plugins: [pinia],
      stubs: {
        CyberGlassCard: { template: '<div><slot /></div>' },
        // lucide 图标
        ArrowLeft: { template: '<span />' },
        Send: { template: '<span />' },
        UserCircle: { template: '<span />' },
        Cpu: { template: '<span />' },
        Loader2: { template: '<span />' },
        Shield: { template: '<span />' },
        AlertTriangle: { template: '<span />' },
        X: { template: '<span />' },
        Sprout: { template: '<span />' },
        Briefcase: { template: '<span />' },
        Flame: { template: '<span />' }
      }
    }
  })

  // 关闭难度选择弹窗，避免 guard 阻止 sendMessage()
  wrapper.vm.showDifficultyModal = false
  // 确保面试未结束
  wrapper.vm.isInterviewEnded = false
  wrapper.vm.strikeTerminated = false

  await wrapper.vm.$nextTick()

  return wrapper
}

// ─── 测试套件 ─────────────────────────────────────────────────────────────────

describe('PremiumInterview — sendMessage() SSE 集成', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorageMock.clear()
  })

  // ── Test 1: onChunk 多片段累积 ────────────────────────────────────────────

  it('Test 1: streamInterviewChat 依次调用 onChunk("Hello")、onChunk(" World")、onChunk("!")，最后一条 AI 消息的 content 应为 "Hello World!"', async () => {
    // 导入 mock 后的 streamInterviewChat，以便配置其行为
    const { streamInterviewChat } = await import('@/services/llm_service.js')

    // 配置 mock：同步调用 onChunk 三次，然后 resolve
    streamInterviewChat.mockImplementation(async (_endpoint, _payload, onChunk, _onError) => {
      onChunk('Hello')
      onChunk(' World')
      onChunk('!')
    })

    const wrapper = await mountPremiumInterview()

    // 设置用户输入并触发 sendMessage
    wrapper.vm.userInput = '请介绍一下你自己'
    await wrapper.vm.sendMessage()

    // 等待所有异步更新完成
    await wrapper.vm.$nextTick()

    // 找到最后一条 AI 消息
    const messages = wrapper.vm.messages
    const lastAiMsg = [...messages].reverse().find(m => m.role === 'ai')

    expect(lastAiMsg).toBeDefined()
    expect(lastAiMsg.content).toBe('Hello World!')
  })

  // ── Test 2: onError 错误文本追加 ──────────────────────────────────────────

  it('Test 2: streamInterviewChat 调用 onError("[网络连接异常，请重试]")，错误文本应追加到最后一条 AI 消息的 content 字段', async () => {
    const { streamInterviewChat } = await import('@/services/llm_service.js')

    // 配置 mock：调用 onError，模拟网络异常
    streamInterviewChat.mockImplementation(async (_endpoint, _payload, _onChunk, onError) => {
      onError('[网络连接异常，请重试]')
    })

    const wrapper = await mountPremiumInterview()

    wrapper.vm.userInput = '你好'
    await wrapper.vm.sendMessage()
    await wrapper.vm.$nextTick()

    const messages = wrapper.vm.messages
    const lastAiMsg = [...messages].reverse().find(m => m.role === 'ai')

    expect(lastAiMsg).toBeDefined()
    // 错误文本应被追加到 content（内联展示，不弹窗）
    expect(lastAiMsg.content).toContain('[网络连接异常，请重试]')
  })

  // ── Test 3: [SCORE_UPDATE] 标签解析与 radarScores 更新 ───────────────────

  it('Test 3: onChunk 内容包含 [SCORE_UPDATE]{...}[/SCORE_UPDATE] 时，标签从显示内容中移除，radarScores 被更新', async () => {
    const { streamInterviewChat } = await import('@/services/llm_service.js')

    const scorePayload = JSON.stringify({
      professional: 80,
      logic: 75,
      communication: 70,
      problemSolving: 85,
      potential: 90,
      resilience: 65
    })

    // 配置 mock：先发送正常文本，再发送带评分标签的 chunk
    streamInterviewChat.mockImplementation(async (_endpoint, _payload, onChunk, _onError) => {
      onChunk('回答得不错。')
      onChunk(`[SCORE_UPDATE]${scorePayload}[/SCORE_UPDATE]`)
    })

    const wrapper = await mountPremiumInterview()

    // 记录初始 radarScores（默认值均为 2）
    const initialScores = { ...wrapper.vm.radarScores }

    wrapper.vm.userInput = '请问您对我的回答有什么评价？'
    await wrapper.vm.sendMessage()
    await wrapper.vm.$nextTick()

    const messages = wrapper.vm.messages
    const lastAiMsg = [...messages].reverse().find(m => m.role === 'ai')

    expect(lastAiMsg).toBeDefined()

    // [SCORE_UPDATE] 标签不应出现在显示内容中
    expect(lastAiMsg.content).not.toContain('[SCORE_UPDATE]')
    expect(lastAiMsg.content).not.toContain('[/SCORE_UPDATE]')

    // 正常文本内容应保留
    expect(lastAiMsg.content).toContain('回答得不错。')

    // radarScores 应已更新为 chunk 中的评分值
    expect(wrapper.vm.radarScores.professional).toBe(80)
    expect(wrapper.vm.radarScores.logic).toBe(75)
    expect(wrapper.vm.radarScores.communication).toBe(70)
    expect(wrapper.vm.radarScores.problemSolving).toBe(85)
    expect(wrapper.vm.radarScores.potential).toBe(90)
    expect(wrapper.vm.radarScores.resilience).toBe(65)

    // 确认确实发生了变化（与初始值不同）
    expect(wrapper.vm.radarScores.professional).not.toBe(initialScores.professional)
  })
})
