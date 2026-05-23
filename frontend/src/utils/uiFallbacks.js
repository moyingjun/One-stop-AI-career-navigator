/**
 * uiFallbacks.js
 *
 * Toast / StreamingLoader 的「先检测复用、缺失则降级」解析模块。
 *
 * 三页（ResumeDiagnosis / CareerPlanning / PremiumInterview）统一从此模块
 * 引入 Toast 与加载态，禁止在页面内部各自实现降级（Requirement 8.8）。
 *
 * ✦ 导出 API：
 *   - resolveToast()                  → Promise<Component>
 *   - resolveLoader()                 → Promise<Component>
 *   - showToast(message, options?)    → void  (命令式，挂载到 document.body)
 *   - InlineToastFallback / InlineLoaderFallback  (内联降级组件，可被复用)
 *
 * ✦ 严格红线（用户补充约束 b 的具体化 + Requirement 7）：
 *   - 不 import services/llm_service.js
 *   - 不直接 import / 引用 fetch、EventSource、axios
 *   - 不出现任何 /api/... 字符串
 *   - 不持有业务状态、不解析 SSE
 *
 * 对应需求：Requirements 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8
 * 对应设计：design.md §Components and Interfaces §5
 *           design.md §Error Handling 中关于「Toast.vue / StreamingLoader.vue 缺失」的处理策略
 */

import { createApp, defineComponent, h, onMounted, ref } from 'vue'

// ─────────────────────────────────────────────────────────────────────────────
// 1. 内联降级组件（Inline Fallback Components）
// ─────────────────────────────────────────────────────────────────────────────

/**
 * 内联 Toast 降级组件
 *
 * 视觉：暗黑赛博毛玻璃 + cyan / red 双语义色调，与 Dashboard.vue 原生 toast 同源。
 * 行为：
 *   - 默认 3000ms 自动消失（通过 onMounted 内的 setTimeout 切换 visible 渲染为 null）
 *   - success → cyan 色调；error → red 色调
 *   - 命令式挂载场景下由外部 showToast() 负责真正的 DOM 卸载
 *
 * Validates: Requirements 8.5
 */
export const InlineToastFallback = defineComponent({
  name: 'InlineToastFallback',
  props: {
    message: { type: String, required: true },
    type: { type: String, default: 'success' }, // 'success' | 'error'
    duration: { type: Number, default: 3000 }
  },
  emits: ['dismiss'],
  setup(props, { emit }) {
    const visible = ref(true)

    onMounted(() => {
      // 内部计时器仅用于视觉淡出；DOM 卸载由命令式调用方 showToast() 控制
      setTimeout(() => {
        visible.value = false
        emit('dismiss')
      }, props.duration)
    })

    return () => {
      if (!visible.value) return null
      const isError = props.type === 'error'
      // 语义色调 class：success → cyan，error → red
      const toneClasses = isError
        ? [
            'inline-toast-fallback--error',
            'border-red-400/30',
            'bg-[#1a0808]/85',
            'text-red-100',
            'shadow-[0_0_28px_rgba(239,68,68,0.20)]'
          ]
        : [
            'inline-toast-fallback--success',
            'border-cyan-400/30',
            'bg-[#0b1020]/85',
            'text-cyan-100',
            'shadow-[0_0_28px_rgba(6,182,212,0.18)]'
          ]
      return h(
        'div',
        {
          role: 'status',
          'aria-live': 'polite',
          class: [
            'inline-toast-fallback',
            'fixed top-5 left-1/2 -translate-x-1/2 z-[120]',
            'px-4 py-2.5 rounded-full border backdrop-blur-2xl',
            'text-sm flex items-center gap-2',
            ...toneClasses
          ]
        },
        props.message
      )
    }
  }
})

/**
 * 内联 StreamingLoader 降级组件
 *
 * 视觉：毛玻璃卡片 + cyan/purple 渐变流光圆点 + 文案 shimmer。
 * 不引入新依赖，全部使用 Tailwind 4 + 既有色调。
 *
 * Validates: Requirements 8.3
 */
export const InlineLoaderFallback = defineComponent({
  name: 'InlineLoaderFallback',
  props: {
    label: { type: String, default: 'AI 思考中…' }
  },
  setup(props) {
    return () =>
      h(
        'div',
        {
          role: 'status',
          'aria-live': 'polite',
          class: [
            'inline-loader-fallback',
            'relative inline-flex items-center gap-3',
            'px-5 py-3 rounded-2xl',
            'border border-cyan-400/20',
            'bg-[#0a0a14]/60 backdrop-blur-xl',
            'shadow-[0_0_24px_rgba(6,182,212,0.18)]'
          ]
        },
        [
          // 流光圆点：cyan → purple 渐变 + pulse 动效
          h('span', {
            class: [
              'inline-loader-fallback__dot',
              'inline-block w-3 h-3 rounded-full',
              'bg-gradient-to-br from-cyan-400 to-purple-500',
              'animate-pulse'
            ]
          }),
          // shimmer 文案
          h(
            'span',
            {
              class: [
                'inline-loader-fallback__label',
                'text-sm font-medium text-cyan-100'
              ]
            },
            props.label
          )
        ]
      )
  }
})

// ─────────────────────────────────────────────────────────────────────────────
// 2. 异步解析函数（resolveToast / resolveLoader）
// ─────────────────────────────────────────────────────────────────────────────

/**
 * 解析 Toast 组件：优先复用真实 `@/components/Toast.vue`，
 * 解析失败（文件不存在 / 抛错）则返回内联 `InlineToastFallback`。
 *
 * 对应需求：Requirements 8.1, 8.4, 8.7
 * Validates: design.md Property 12（降级模块解析顺序优先级）
 *
 * @returns {Promise<import('vue').Component>}
 */
export async function resolveToast() {
  try {
    const componentName = 'Toast';
    const mod = await import(`@/components/${componentName}.vue`);
    return mod.default || mod;
  } catch (_err) {
    return InlineToastFallback;
  }
}

/**
 * 解析 StreamingLoader 组件：优先复用真实 `@/components/StreamingLoader.vue`，
 * 解析失败则返回内联 `InlineLoaderFallback`。
 *
 * 对应需求：Requirements 8.1, 8.2, 8.6
 * Validates: design.md Property 12（降级模块解析顺序优先级）
 *
 * @returns {Promise<import('vue').Component>}
 */
export async function resolveLoader() {
  try {
    // 使用字符串拼接避开 Vite 在编译期的强依赖检查
    const componentName = 'StreamingLoader';
    const mod = await import(`@/components/${componentName}.vue`);
    return mod.default || mod;
  } catch (_err) {
    return InlineLoaderFallback;
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// 3. 命令式 showToast：业务页面无需挂组件即可触发轻提示
// ─────────────────────────────────────────────────────────────────────────────

/**
 * 命令式轻提示。
 *
 * 解析顺序（对齐 Requirement 8.7「存在则优先复用」）：
 *   1. 通过 resolveToast() 异步拿到组件解析结果
 *   2. 若解析到的是真实 `@/components/Toast.vue`（即非 InlineToastFallback），
 *      则尝试用同一套 props { message, type, duration } 挂载真实组件
 *   3. 真实组件 props 不兼容 / 挂载抛错 / 文件缺失 → 自动回落到 InlineToastFallback
 *
 * 在 `document.body` 上挂载一个临时实例，`duration` 毫秒后由本函数负责卸载
 * Vue 应用并移除宿主节点。
 *
 * 行为契约：
 *   - 在虚拟时间 < duration 的任一时刻，DOM 中存在含 message 文案的 toast 节点
 *   - 在虚拟时间 ≥ duration 时，该节点已从 DOM 中移除
 *   - type === 'success' → 节点 class 含 cyan 色调（InlineToastFallback 路径）
 *   - type === 'error'   → 节点 class 含 red 色调（InlineToastFallback 路径）
 *
 * 对应需求：Requirements 8.4, 8.5, 8.7, 8.8
 * Validates: design.md Property 13（Toast Fallback 自动消失 + 语义色调）
 *
 * @param {string} message - 提示文案（非空字符串）
 * @param {{ type?: 'success'|'error', duration?: number }} [options]
 */
export function showToast(message, options) {
  // SSR 与防御性短路：浏览器环境之外（jsdom 仍视为浏览器环境）/ 非法 message 直接返回
  if (typeof document === 'undefined') return
  if (typeof message !== 'string' || message.length === 0) return

  const opts = options || {}
  const type = opts.type === 'error' ? 'error' : 'success'
  const duration =
    typeof opts.duration === 'number' && Number.isFinite(opts.duration) && opts.duration > 0
      ? opts.duration
      : 3000

  // 异步解析组件：先尝试真实 Toast.vue，缺失/不兼容则自动降级到 InlineToastFallback
  resolveToast()
    .then((Component) => mountToastInstance(Component, { message, type, duration }))
    .catch(() => mountToastInstance(InlineToastFallback, { message, type, duration }))
}

/**
 * 内部辅助：把指定 Toast 组件挂载到 body 上的临时宿主节点，
 * 并在 duration 毫秒后卸载 Vue 应用、移除宿主节点。
 *
 * 对真实 Toast.vue 与 InlineToastFallback 都使用同一套 props
 * { message, type, duration }；如果真实组件的 props 不兼容（例如缺少 message 或抛错），
 * 挂载失败时会自动重新尝试 InlineToastFallback，确保用户始终能看到提示。
 */
function mountToastInstance(Component, props) {
  const host = document.createElement('div')
  host.setAttribute('data-inline-toast-host', '')
  document.body.appendChild(host)

  let app
  try {
    app = createApp(Component, props)
    app.mount(host)
  } catch (_mountErr) {
    // 真实 Toast.vue 不兼容（props 缺失等） → 清理后降级到 InlineToastFallback
    if (host.parentNode) host.parentNode.removeChild(host)
    if (Component !== InlineToastFallback) {
      mountToastInstance(InlineToastFallback, props)
    }
    return
  }

  // 由本函数负责真正的 DOM 卸载，确保即便组件内部 emit('dismiss') 没被外部捕获
  // 也能在 duration 毫秒后从 DOM 中彻底移除节点（属性测试断言依赖此行为）
  setTimeout(() => {
    try {
      app.unmount()
    } catch (_unmountErr) {
      /* noop */
    }
    if (host.parentNode) host.parentNode.removeChild(host)
  }, props.duration)
}
