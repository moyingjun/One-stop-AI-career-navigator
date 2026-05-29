/**
 * accentTheme.js —— 全站主题强调色(Accent Color)切换
 *
 * 演进:
 *   v1: 单点强调色(--accent-rgb / --accent-color / --accent-soft / --accent-border)
 *   v2: 加入 secondary + 渐变变量,用于品牌装饰色(ChatDock 外壳光晕 / KnowledgeBase 主 CTA 等)
 *
 * 不替换 Tailwind 类、不改 Tailwind config、不引依赖。
 * 只渐进式迁移品牌装饰色;语义色(success/error/warning/数据色/状态灯)保持原样。
 *
 * localStorage key: app_accent_theme,刷新自动恢复。
 *
 * 暴露的 CSS 变量(写在 :root):
 *   ── 主色(单点)──
 *   --accent-rgb            "34, 211, 238"            (供 rgba(var(...), x) 使用)
 *   --accent-color          rgb(34, 211, 238)         (color / border-color)
 *   --accent-soft           rgba(..., 0.12)           (hover/active 软底)
 *   --accent-border         rgba(..., 0.35)           (描边)
 *   ── 次色 + 渐变(本轮新增)──
 *   --accent-secondary-rgb   "129, 140, 248"
 *   --accent-secondary-color rgb(129, 140, 248)
 *   --accent-gradient        linear-gradient(135deg, primary, secondary)        实色按钮 / 强 CTA
 *   --accent-gradient-soft   linear-gradient(135deg, primary 14%, secondary 14%) 卡片底色 / 玻璃毛感
 *
 * 使用示例:
 *   .cta { background: var(--accent-gradient); color:#fff; }
 *   .pill { background: var(--accent-gradient-soft); border:1px solid var(--accent-border); }
 *   .shell { box-shadow: 0 0 18px rgba(var(--accent-rgb), 0.30); }
 */

export const ACCENT_THEME_LS_KEY = 'app_accent_theme'

/**
 * 5 套主题。primaryRgb 与之前 v1 保持一致以保证兼容,新增 secondaryRgb 用于渐变第二色。
 * 颜色对照表(对应用户给定的 hex,均为 Tailwind 400 级):
 *   cyan    primary #22d3ee  + secondary #818cf8  (cyan + indigo)
 *   purple  primary #c084fc  + secondary #60a5fa  (purple + blue)
 *   emerald primary #34d399  + secondary #22d3ee  (emerald + cyan)
 *   amber   primary #fbbf24  + secondary #a78bfa  (amber + violet)
 *   pink    primary #f472b6  + secondary #c084fc  (pink + purple)
 */
export const THEMES = Object.freeze({
  cyan:    { name: 'cyan',    label: '赛博青', primaryRgb: '34, 211, 238',  secondaryRgb: '129, 140, 248' },
  purple:  { name: 'purple',  label: '霓虹紫', primaryRgb: '192, 132, 252', secondaryRgb: '96, 165, 250'  },
  emerald: { name: 'emerald', label: '翡翠绿', primaryRgb: '52, 211, 153',  secondaryRgb: '34, 211, 238'  },
  amber:   { name: 'amber',   label: '琥珀橙', primaryRgb: '251, 191, 36',  secondaryRgb: '167, 139, 250' },
  pink:    { name: 'pink',    label: '玫红',   primaryRgb: '244, 114, 182', secondaryRgb: '192, 132, 252' }
})

/**
 * 兼容旧 v1 调用方:rgb 字段是 primaryRgb 的别名。
 * 既有页面(Dashboard 5 swatch 显示 rgb(...))无需任何改动。
 */
for (const t of Object.values(THEMES)) {
  Object.defineProperty(t, 'rgb', { value: t.primaryRgb, enumerable: true })
}

export const ACCENT_THEME_LIST = Object.values(THEMES)

/** 默认色:cyan */
export const DEFAULT_ACCENT = 'cyan'

/** 给定 name 取 theme,未知值兜底为默认 */
export function resolveTheme(name) {
  return THEMES[name] || THEMES[DEFAULT_ACCENT]
}

/**
 * 把指定 accent 色写到 :root 上的 CSS 变量。
 * 立即对所有引用 var(--accent-*) 的 DOM 元素生效。
 */
export function applyAccentTheme(name) {
  const theme = resolveTheme(name)
  if (typeof document === 'undefined') return theme
  const root = document.documentElement

  // ── v1 单点变量(保留,向后兼容)──
  root.style.setProperty('--accent-rgb',     theme.primaryRgb)
  root.style.setProperty('--accent-color',   `rgb(${theme.primaryRgb})`)
  root.style.setProperty('--accent-soft',    `rgba(${theme.primaryRgb}, 0.12)`)
  root.style.setProperty('--accent-border',  `rgba(${theme.primaryRgb}, 0.35)`)

  // ── v2 secondary + 渐变(本轮新增)──
  root.style.setProperty('--accent-secondary-rgb',   theme.secondaryRgb)
  root.style.setProperty('--accent-secondary-color', `rgb(${theme.secondaryRgb})`)
  // 实色渐变:用于按钮 / 强 CTA(色彩饱和)
  root.style.setProperty(
    '--accent-gradient',
    `linear-gradient(135deg, rgb(${theme.primaryRgb}) 0%, rgb(${theme.secondaryRgb}) 100%)`
  )
  // 软渐变:14% / 6% 双色玻璃毛感,用于卡片底色 / pill / 顶部高亮线等装饰区
  root.style.setProperty(
    '--accent-gradient-soft',
    `linear-gradient(135deg, rgba(${theme.primaryRgb}, 0.14) 0%, rgba(${theme.secondaryRgb}, 0.06) 100%)`
  )
  return theme
}

/** 持久化用户选择;失败兜底不抛(localStorage 配额 / 隐身模式 安全) */
function persistAccentTheme(name) {
  try {
    localStorage.setItem(ACCENT_THEME_LS_KEY, name)
  } catch (e) {
    console.warn('[accentTheme] localStorage 写入失败:', e)
  }
}

/**
 * 用户切换主题色入口:
 *   1. apply(立即生效)
 *   2. persist(刷新后保留)
 *
 * @param {string} name 'cyan' | 'purple' | 'emerald' | 'amber' | 'pink'
 * @returns {object} 实际应用的 theme(若 name 无效会兜底为默认)
 */
export function setAccentTheme(name) {
  const theme = applyAccentTheme(name)
  persistAccentTheme(theme.name)
  return theme
}

/**
 * 应用启动时调用一次:从 localStorage 读取 → apply。
 * 没有读到或值无效都会回落到默认色。
 *
 * @returns {string} 当前 accent 名
 */
export function loadAccentTheme() {
  let name = DEFAULT_ACCENT
  try {
    const raw = localStorage.getItem(ACCENT_THEME_LS_KEY)
    if (raw && THEMES[raw]) name = raw
  } catch (e) {
    /* 读取失败:走默认 */
  }
  applyAccentTheme(name)
  return name
}

/**
 * 取当前 accent 名(只读 localStorage,不写)。
 * 如果还没保存过,返回默认色名。
 */
export function getCurrentAccentName() {
  try {
    const raw = localStorage.getItem(ACCENT_THEME_LS_KEY)
    if (raw && THEMES[raw]) return raw
  } catch (e) {
    /* noop */
  }
  return DEFAULT_ACCENT
}
