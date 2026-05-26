/**
 * accentTheme.js —— 全站主题强调色(Accent Color)切换
 *
 * 第一版策略:
 *   - 不替换 Tailwind 颜色类名,只通过 CSS 变量改少数关键 accent 点
 *   - 5 个色板:cyan / purple / emerald / amber / pink
 *   - 选择即生效:写入 :root 上 4 个 CSS 变量
 *   - localStorage key: app_accent_theme;刷新自动恢复
 *
 * 暴露的 CSS 变量:
 *   --accent-rgb     例:34, 211, 238       (供 rgba() 使用,如 rgba(var(--accent-rgb), 0.25))
 *   --accent-color   例:rgb(34, 211, 238)  (用于 color / border-color)
 *   --accent-soft    accent 的 12% 透明背景,用于 hover/active
 *   --accent-border  accent 的 35% 透明描边
 *
 * 使用样例:
 *   .my-card { color: var(--accent-color); border-color: var(--accent-border); }
 *   .my-glow { box-shadow: 0 0 16px rgba(var(--accent-rgb), 0.35); }
 */

export const ACCENT_THEME_LS_KEY = 'app_accent_theme'

/**
 * 5 个标准 accent 色板。RGB 值取自 Tailwind 默认色阶的 *-400(更亮、视觉一致),
 * 与既有 Dark Cyberpunk + Glassmorphism 风格协调。
 */
export const THEMES = Object.freeze({
  cyan:    { name: 'cyan',    label: '赛博青',  rgb: '34, 211, 238'  },  // tailwind cyan-400
  purple:  { name: 'purple',  label: '霓虹紫',  rgb: '192, 132, 252' },  // purple-400
  emerald: { name: 'emerald', label: '翡翠绿',  rgb: '52, 211, 153'  },  // emerald-400
  amber:   { name: 'amber',   label: '琥珀橙',  rgb: '251, 191, 36'  },  // amber-400
  pink:    { name: 'pink',    label: '玫红',    rgb: '244, 114, 182' }   // pink-400
})

export const ACCENT_THEME_LIST = Object.values(THEMES)

/** 默认色:cyan(对应当前默认视觉的青色 accent) */
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
  root.style.setProperty('--accent-rgb', theme.rgb)
  root.style.setProperty('--accent-color', `rgb(${theme.rgb})`)
  root.style.setProperty('--accent-soft', `rgba(${theme.rgb}, 0.12)`)
  root.style.setProperty('--accent-border', `rgba(${theme.rgb}, 0.35)`)
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
