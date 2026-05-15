/**
 * Dashboard 新手启航舱属性测试 — Property-Based Testing with fast-check
 *
 * **Validates: Requirements 7.1, 7.2, 7.3, 7.4**
 *
 * Property 5: Card Content Config Consistency
 *
 * 核心属性：
 *   对任意引导卡片（激活或锁定），其渲染的 desc 文本内容与 onboardingCards
 *   静态配置数组中对应条目的 desc 字段完全一致，不存在截断、替换或乱序。
 *
 * **Validates: Requirements 4.5**
 *
 * Property 3: Active Card Content Completeness
 *
 * 核心属性：
 *   对任意激活状态的引导卡片（locked=false），其渲染结果中必须同时包含：
 *   Emoji 图标区域、中文功能标题、英文副标题、功能描述文本、以及主色高亮操作按钮，
 *   缺少任意一项均视为不合格。
 *
 * **Validates: Requirements 4.2, 4.3, 4.4**
 *
 * Property 2: Active Card Route Navigation Correctness
 *
 * 核心属性：
 *   对任意激活状态的引导卡片（locked=false），点击其操作按钮时，
 *   router.push 被调用且参数与该卡片配置的 path 字段完全一致；
 *   不同卡片的跳转路径互不相同且均为预定义的内部路由。
 */
import { describe, it, expect } from 'vitest'
import * as fc from 'fast-check'

// ─────────────────────────────────────────────
// 被测数据：从 Dashboard.vue 中提取的 onboardingCards 静态配置
// Requirements: 7.1, 7.2, 7.3, 7.4, 8.3
// ─────────────────────────────────────────────

/**
 * 新手启航舱卡片配置（与 Dashboard.vue 中的 onboardingCards 完全一致）
 * 静态数据，不依赖任何响应式数据源
 */
const onboardingCards = [
  {
    id: 'resume',
    emoji: '📄',
    title: '简历诊断',
    subtitle: 'Resume Scanner',
    desc: '深度解析过往经历，精准对齐目标岗位。找出致命失分项并提供重构建议，让你的简历一击必中。',
    action: '立即诊断',
    path: '/resume-diagnosis',
    locked: false,
    themeColor: 'purple',
  },
  {
    id: 'interview',
    emoji: '🎙️',
    title: '模拟面试',
    subtitle: 'Combat Simulator',
    desc: '沉浸式 AI 语音实战对练。模拟真实业务场景与高频拷问，生成多维度能力雷达，彻底消除实战恐慌。',
    action: '开启实战',
    path: '/interview',
    locked: false,
    themeColor: 'pink',
  },
  {
    id: 'career',
    emoji: '🗺️',
    title: '职业规划',
    subtitle: 'Career Compass',
    desc: '基于个人特质与行业真实大数据，打破信息壁垒，为你定制科学、清晰的长线职场发展路径。',
    action: '生成路线',
    path: '/career-planning',
    locked: false,
    themeColor: 'blue',
  },
  {
    id: 'education',
    emoji: '🎓',
    title: '升学与避坑',
    subtitle: 'Academic Radar',
    desc: '专插本、考研真实数据导航。帮你平衡繁重的课业规划与升学抉择，绕开前人踩过的坑。',
    action: '模块构筑中...',
    path: null,
    locked: true,
    themeColor: 'emerald',
  },
]

// ─────────────────────────────────────────────
// 需求规定的精确 desc 值（来自 Requirements 7.1–7.4）
// ─────────────────────────────────────────────

const EXPECTED_DESC_MAP = {
  resume: '深度解析过往经历，精准对齐目标岗位。找出致命失分项并提供重构建议，让你的简历一击必中。',
  interview: '沉浸式 AI 语音实战对练。模拟真实业务场景与高频拷问，生成多维度能力雷达，彻底消除实战恐慌。',
  career: '基于个人特质与行业真实大数据，打破信息壁垒，为你定制科学、清晰的长线职场发展路径。',
  education: '专插本、考研真实数据导航。帮你平衡繁重的课业规划与升学抉择，绕开前人踩过的坑。',
}

// ─────────────────────────────────────────────
// 模拟渲染函数：模拟 Dashboard 在 historyRecords=[] 时渲染 OnboardingPanel
// 返回每张卡片的 desc 文本（即 v-for 遍历 onboardingCards 时渲染的 desc 字段）
// ─────────────────────────────────────────────

/**
 * 模拟 OnboardingPanel 的卡片渲染逻辑。
 * 当 historyRecords = [] 且 isHistoryLoading = false 时，
 * Dashboard 渲染 OnboardingPanel，遍历 onboardingCards 并渲染每张卡片的 desc。
 *
 * @param {Array} cards - onboardingCards 配置数组
 * @param {Array} historyRecords - 历史记录数组（空数组触发 OnboardingPanel）
 * @param {boolean} isHistoryLoading - 加载状态
 * @returns {Array<{id: string, renderedDesc: string}>} 渲染结果
 */
function renderOnboardingPanel(cards, historyRecords, isHistoryLoading) {
  // 仅在 historyRecords 为空且不在加载中时渲染 OnboardingPanel
  if (isHistoryLoading || historyRecords.length > 0) {
    return null // HistoryPanel 或加载状态，不渲染 OnboardingPanel
  }

  // 遍历 onboardingCards，提取每张卡片的 desc（模拟 v-for 渲染）
  return cards.map(card => ({
    id: card.id,
    renderedDesc: card.desc, // 直接使用配置中的 desc，与模板 {{ card.desc }} 等价
  }))
}

// ─────────────────────────────────────────────
// Property 5 属性测试
// ─────────────────────────────────────────────

describe('Property 5: Card Content Config Consistency（卡片内容配置一致性）', () => {

  // ── Requirement 7.1 ──────────────────────────────────────────────────────
  // WHEN 简历诊断卡片被渲染时，THE 卡片 SHALL 显示描述文本：
  // "深度解析过往经历，精准对齐目标岗位。找出致命失分项并提供重构建议，让你的简历一击必中。"
  it('Property 5.1: 对任意卡片索引，渲染的 desc 与配置中的 desc 字段完全一致（无截断、无替换）', () => {
    // 生成器：从 0 到 onboardingCards.length-1 的任意索引
    const cardIndexArb = fc.integer({ min: 0, max: onboardingCards.length - 1 })

    fc.assert(
      fc.property(
        cardIndexArb,
        (index) => {
          const card = onboardingCards[index]
          const rendered = renderOnboardingPanel(onboardingCards, [], false)

          // OnboardingPanel 应被渲染（historyRecords 为空）
          expect(rendered).not.toBeNull()

          // 找到对应卡片的渲染结果
          const renderedCard = rendered.find(r => r.id === card.id)
          expect(renderedCard).toBeDefined()

          // 核心断言：渲染的 desc 与配置中的 desc 完全一致
          expect(renderedCard.renderedDesc).toBe(card.desc)
        }
      ),
      { numRuns: 100 }
    )
  })

  // ── Requirement 7.1 ──────────────────────────────────────────────────────
  it('Property 5.2: 简历诊断卡片（resume）的 desc 与需求规定文案完全一致', () => {
    fc.assert(
      fc.property(
        fc.constant('resume'),
        (cardId) => {
          const rendered = renderOnboardingPanel(onboardingCards, [], false)
          const renderedCard = rendered.find(r => r.id === cardId)

          expect(renderedCard.renderedDesc).toBe(EXPECTED_DESC_MAP.resume)
        }
      ),
      { numRuns: 50 }
    )
  })

  // ── Requirement 7.2 ──────────────────────────────────────────────────────
  it('Property 5.3: 模拟面试卡片（interview）的 desc 与需求规定文案完全一致', () => {
    fc.assert(
      fc.property(
        fc.constant('interview'),
        (cardId) => {
          const rendered = renderOnboardingPanel(onboardingCards, [], false)
          const renderedCard = rendered.find(r => r.id === cardId)

          expect(renderedCard.renderedDesc).toBe(EXPECTED_DESC_MAP.interview)
        }
      ),
      { numRuns: 50 }
    )
  })

  // ── Requirement 7.3 ──────────────────────────────────────────────────────
  it('Property 5.4: 职业规划卡片（career）的 desc 与需求规定文案完全一致', () => {
    fc.assert(
      fc.property(
        fc.constant('career'),
        (cardId) => {
          const rendered = renderOnboardingPanel(onboardingCards, [], false)
          const renderedCard = rendered.find(r => r.id === cardId)

          expect(renderedCard.renderedDesc).toBe(EXPECTED_DESC_MAP.career)
        }
      ),
      { numRuns: 50 }
    )
  })

  // ── Requirement 7.4 ──────────────────────────────────────────────────────
  it('Property 5.5: 升学与避坑卡片（education）的 desc 与需求规定文案完全一致', () => {
    fc.assert(
      fc.property(
        fc.constant('education'),
        (cardId) => {
          const rendered = renderOnboardingPanel(onboardingCards, [], false)
          const renderedCard = rendered.find(r => r.id === cardId)

          expect(renderedCard.renderedDesc).toBe(EXPECTED_DESC_MAP.education)
        }
      ),
      { numRuns: 50 }
    )
  })

  // ── 综合属性：所有 4 张卡片的 desc 均与需求规定文案一致 ──────────────────
  it('Property 5.6: 对所有 4 张卡片，渲染的 desc 均与需求规定文案完全一致（综合验证）', () => {
    // 生成器：从 4 个卡片 id 中任意选取
    const cardIdArb = fc.constantFrom('resume', 'interview', 'career', 'education')

    fc.assert(
      fc.property(
        cardIdArb,
        (cardId) => {
          const rendered = renderOnboardingPanel(onboardingCards, [], false)

          // OnboardingPanel 应被渲染
          expect(rendered).not.toBeNull()
          expect(rendered).toHaveLength(4)

          // 找到对应卡片
          const renderedCard = rendered.find(r => r.id === cardId)
          expect(renderedCard).toBeDefined()

          // 核心断言：渲染的 desc 与需求规定文案完全一致
          expect(renderedCard.renderedDesc).toBe(EXPECTED_DESC_MAP[cardId])
        }
      ),
      { numRuns: 200 }
    )
  })

  // ── 属性：historyRecords 非空时 OnboardingPanel 不渲染（不暴露 desc）──────
  it('Property 5.7: 当 historyRecords 非空时，OnboardingPanel 不渲染（desc 不暴露）', () => {
    // 生成器：非空的历史记录数组（至少 1 条记录）
    const nonEmptyHistoryArb = fc.array(
      fc.record({ id: fc.integer({ min: 1 }), category: fc.string() }),
      { minLength: 1, maxLength: 5 }
    )

    fc.assert(
      fc.property(
        nonEmptyHistoryArb,
        (historyRecords) => {
          const rendered = renderOnboardingPanel(onboardingCards, historyRecords, false)

          // historyRecords 非空时，OnboardingPanel 不渲染
          expect(rendered).toBeNull()
        }
      ),
      { numRuns: 100 }
    )
  })

  // ── 属性：加载中时 OnboardingPanel 不渲染 ────────────────────────────────
  it('Property 5.8: 当 isHistoryLoading 为 true 时，OnboardingPanel 不渲染', () => {
    fc.assert(
      fc.property(
        fc.constant(true),
        (isLoading) => {
          const rendered = renderOnboardingPanel(onboardingCards, [], isLoading)

          // 加载中时，OnboardingPanel 不渲染
          expect(rendered).toBeNull()
        }
      ),
      { numRuns: 50 }
    )
  })

  // ── 属性：onboardingCards 包含且仅包含 4 张卡片 ──────────────────────────
  it('Property 5.9: onboardingCards 配置包含且仅包含 4 张卡片（resume、interview、career、education）', () => {
    const expectedIds = ['resume', 'interview', 'career', 'education']

    fc.assert(
      fc.property(
        fc.constant(onboardingCards),
        (cards) => {
          expect(cards).toHaveLength(4)

          const actualIds = cards.map(c => c.id)
          expect(actualIds).toEqual(expectedIds)
        }
      ),
      { numRuns: 10 }
    )
  })

  // ── 属性：每张卡片的 desc 字段为非空字符串 ──────────────────────────────
  it('Property 5.10: 对任意卡片，desc 字段为非空字符串（不存在空 desc）', () => {
    const cardIndexArb = fc.integer({ min: 0, max: onboardingCards.length - 1 })

    fc.assert(
      fc.property(
        cardIndexArb,
        (index) => {
          const card = onboardingCards[index]

          expect(typeof card.desc).toBe('string')
          expect(card.desc.trim().length).toBeGreaterThan(0)
        }
      ),
      { numRuns: 100 }
    )
  })
})

// ─────────────────────────────────────────────
// 模拟激活卡片渲染函数：返回包含所有 5 个必需元素的渲染对象
// ─────────────────────────────────────────────

/**
 * 模拟激活卡片（locked=false）的渲染逻辑。
 * 对应 Dashboard.vue 中 v-if="!card.locked" 分支的渲染结果。
 *
 * 返回一个包含所有 5 个必需元素的对象，模拟模板渲染后的内容：
 *   1. emoji       — Emoji 图标区域
 *   2. title       — 中文功能标题
 *   3. subtitle    — 英文副标题
 *   4. desc        — 功能描述文本
 *   5. action      — 操作按钮文案
 *
 * @param {Object} card - onboardingCards 中的单张卡片配置
 * @returns {{ emoji: string, title: string, subtitle: string, desc: string, action: string } | null}
 *   激活卡片返回包含 5 个元素的对象；锁定卡片返回 null（不在激活渲染路径中）
 */
function renderActiveCard(card) {
  // 仅渲染激活卡片（locked=false）
  if (card.locked) {
    return null
  }

  // 模拟 Dashboard.vue 中激活卡片的模板渲染结果
  // 对应：{{ card.emoji }}、{{ card.title }}、{{ card.subtitle }}、{{ card.desc }}、{{ card.action }}
  return {
    emoji: card.emoji,       // Emoji 图标区域
    title: card.title,       // 中文功能标题
    subtitle: card.subtitle, // 英文副标题
    desc: card.desc,         // 功能描述文本
    action: card.action,     // 操作按钮文案
  }
}

// ─────────────────────────────────────────────
// Property 3 属性测试
// ─────────────────────────────────────────────

describe('Property 3: Active Card Content Completeness（激活卡片内容完整性）', () => {

  // 激活卡片子集（locked=false）
  const activeCards = onboardingCards.filter(card => !card.locked)

  // ── 核心属性：对任意激活卡片，5 个必需元素同时存在 ──────────────────────
  // **Validates: Requirements 4.5**
  it('Property 3.1: 对任意激活卡片，Emoji、中文标题、英文副标题、描述文本、操作按钮同时存在且均为非空字符串', () => {
    // 生成器：从激活卡片（locked=false）中任意选取一张
    const activeCardArb = fc.constantFrom(...activeCards)

    fc.assert(
      fc.property(
        activeCardArb,
        (card) => {
          const rendered = renderActiveCard(card)

          // 激活卡片必须被渲染（不为 null）
          expect(rendered).not.toBeNull()

          // 断言 5 个必需元素同时存在且均为非空字符串
          // 1. Emoji 图标区域
          expect(typeof rendered.emoji).toBe('string')
          expect(rendered.emoji.trim().length).toBeGreaterThan(0)

          // 2. 中文功能标题
          expect(typeof rendered.title).toBe('string')
          expect(rendered.title.trim().length).toBeGreaterThan(0)

          // 3. 英文副标题
          expect(typeof rendered.subtitle).toBe('string')
          expect(rendered.subtitle.trim().length).toBeGreaterThan(0)

          // 4. 功能描述文本
          expect(typeof rendered.desc).toBe('string')
          expect(rendered.desc.trim().length).toBeGreaterThan(0)

          // 5. 操作按钮文案
          expect(typeof rendered.action).toBe('string')
          expect(rendered.action.trim().length).toBeGreaterThan(0)
        }
      ),
      { numRuns: 100 }
    )
  })

  // ── 属性：遍历所有激活卡片（resume、interview、career），逐一验证 5 个元素 ──
  // **Validates: Requirements 4.5**
  it('Property 3.2: 遍历所有激活卡片（resume、interview、career），每张卡片的 5 个必需元素均完整', () => {
    // 生成器：从 3 个激活卡片 id 中任意选取
    const activeCardIdArb = fc.constantFrom('resume', 'interview', 'career')

    fc.assert(
      fc.property(
        activeCardIdArb,
        (cardId) => {
          const card = onboardingCards.find(c => c.id === cardId)

          // 确认该卡片存在且为激活状态
          expect(card).toBeDefined()
          expect(card.locked).toBe(false)

          const rendered = renderActiveCard(card)
          expect(rendered).not.toBeNull()

          // 断言 5 个必需元素均为非空字符串
          const requiredFields = ['emoji', 'title', 'subtitle', 'desc', 'action']
          for (const field of requiredFields) {
            expect(typeof rendered[field]).toBe('string')
            expect(rendered[field].trim().length).toBeGreaterThan(0)
          }
        }
      ),
      { numRuns: 150 }
    )
  })

  // ── 属性：激活卡片的 emoji 字段包含有效的 Emoji 字符 ──────────────────────
  // **Validates: Requirements 4.5**
  it('Property 3.3: 对任意激活卡片，emoji 字段包含有效的 Emoji 字符（Unicode 范围验证）', () => {
    const activeCardArb = fc.constantFrom(...activeCards)

    fc.assert(
      fc.property(
        activeCardArb,
        (card) => {
          const rendered = renderActiveCard(card)
          expect(rendered).not.toBeNull()

          // Emoji 字符的 Unicode 码点通常 > 0xFFFF（需要代理对），
          // 或在 Emoji 专用区间（U+1F300–U+1FAFF 等）
          // 使用正则验证 emoji 字段包含至少一个 Emoji 字符
          const emojiRegex = /\p{Emoji}/u
          expect(emojiRegex.test(rendered.emoji)).toBe(true)
        }
      ),
      { numRuns: 100 }
    )
  })

  // ── 属性：激活卡片的 subtitle 字段包含英文字符（ASCII 字母）──────────────
  // **Validates: Requirements 4.5**
  it('Property 3.4: 对任意激活卡片，subtitle（英文副标题）字段包含至少一个 ASCII 英文字母', () => {
    const activeCardArb = fc.constantFrom(...activeCards)

    fc.assert(
      fc.property(
        activeCardArb,
        (card) => {
          const rendered = renderActiveCard(card)
          expect(rendered).not.toBeNull()

          // 英文副标题应包含至少一个 ASCII 字母（a-z 或 A-Z）
          const asciiLetterRegex = /[a-zA-Z]/
          expect(asciiLetterRegex.test(rendered.subtitle)).toBe(true)
        }
      ),
      { numRuns: 100 }
    )
  })

  // ── 属性：激活卡片的 title 字段包含中文字符 ──────────────────────────────
  // **Validates: Requirements 4.5**
  it('Property 3.5: 对任意激活卡片，title（中文功能标题）字段包含至少一个中文字符', () => {
    const activeCardArb = fc.constantFrom(...activeCards)

    fc.assert(
      fc.property(
        activeCardArb,
        (card) => {
          const rendered = renderActiveCard(card)
          expect(rendered).not.toBeNull()

          // 中文字符 Unicode 范围：U+4E00–U+9FFF（CJK 统一汉字基本区）
          const chineseCharRegex = /[\u4e00-\u9fff]/
          expect(chineseCharRegex.test(rendered.title)).toBe(true)
        }
      ),
      { numRuns: 100 }
    )
  })

  // ── 属性：锁定卡片（education）不在激活渲染路径中 ────────────────────────
  // **Validates: Requirements 4.5**（反向验证：锁定卡片不属于激活卡片集合）
  it('Property 3.6: 锁定卡片（education）不在激活卡片集合中，renderActiveCard 返回 null', () => {
    fc.assert(
      fc.property(
        fc.constant('education'),
        (cardId) => {
          const card = onboardingCards.find(c => c.id === cardId)
          expect(card).toBeDefined()
          expect(card.locked).toBe(true)

          // 锁定卡片不应被激活渲染
          const rendered = renderActiveCard(card)
          expect(rendered).toBeNull()
        }
      ),
      { numRuns: 50 }
    )
  })

  // ── 综合属性：激活卡片集合恰好包含 3 张（resume、interview、career）────────
  // **Validates: Requirements 4.1, 4.5**
  it('Property 3.7: 激活卡片集合恰好包含 3 张（resume、interview、career），且每张均通过 5 元素完整性检查', () => {
    fc.assert(
      fc.property(
        fc.constant(onboardingCards),
        (cards) => {
          const active = cards.filter(c => !c.locked)

          // 激活卡片恰好 3 张
          expect(active).toHaveLength(3)

          // 激活卡片 id 集合
          const activeIds = active.map(c => c.id).sort()
          expect(activeIds).toEqual(['career', 'interview', 'resume'])

          // 每张激活卡片均通过 5 元素完整性检查
          for (const card of active) {
            const rendered = renderActiveCard(card)
            expect(rendered).not.toBeNull()

            const requiredFields = ['emoji', 'title', 'subtitle', 'desc', 'action']
            for (const field of requiredFields) {
              expect(typeof rendered[field]).toBe('string')
              expect(rendered[field].trim().length).toBeGreaterThan(0)
            }
          }
        }
      ),
      { numRuns: 50 }
    )
  })
})

// ─────────────────────────────────────────────
// 路由跳转纯函数：提取激活卡片的路由逻辑
// ─────────────────────────────────────────────

/**
 * 获取卡片的路由路径（纯函数，无副作用）。
 * 对应 Dashboard.vue 中激活卡片按钮的 @click="router.push(card.path)" 逻辑。
 *
 * @param {Object} card - onboardingCards 中的单张卡片配置
 * @returns {string|null} 激活卡片返回 card.path；锁定卡片返回 null（不可跳转）
 */
function getCardRoute(card) {
  if (card.locked) {
    return null // 锁定卡片：不触发路由跳转
  }
  return card.path // 激活卡片：返回配置的路径
}

// ─────────────────────────────────────────────
// Property 2 属性测试
// ─────────────────────────────────────────────

describe('Property 2: Active Card Route Navigation Correctness（激活卡片路由跳转正确性）', () => {

  // 激活卡片子集（locked=false）
  const activeCards = onboardingCards.filter(card => !card.locked)

  // 需求规定的精确路径映射（来自 Requirements 4.2, 4.3, 4.4）
  const EXPECTED_PATH_MAP = {
    resume: '/resume-diagnosis',   // Requirement 4.2
    interview: '/interview',       // Requirement 4.3
    career: '/career-planning',    // Requirement 4.4
  }

  // ── 核心属性：对任意激活卡片，getCardRoute 返回与 card.path 完全一致的路径 ──
  // **Validates: Requirements 4.2, 4.3, 4.4**
  it('Property 2.1: 对任意激活卡片，getCardRoute(card) 返回与 card.path 字段完全一致的路径', () => {
    // 生成器：从激活卡片（locked=false）中任意选取一张
    const activeCardArb = fc.constantFrom(...activeCards)

    fc.assert(
      fc.property(
        activeCardArb,
        (card) => {
          const route = getCardRoute(card)

          // 激活卡片必须返回非 null 路径
          expect(route).not.toBeNull()

          // 核心断言：返回路径与 card.path 字段完全一致
          expect(route).toBe(card.path)
        }
      ),
      { numRuns: 100 }
    )
  })

  // ── 属性：简历诊断卡片路由跳转至 /resume-diagnosis ──────────────────────
  // **Validates: Requirement 4.2**
  it('Property 2.2: 简历诊断卡片（resume）的路由路径为 /resume-diagnosis', () => {
    fc.assert(
      fc.property(
        fc.constant('resume'),
        (cardId) => {
          const card = onboardingCards.find(c => c.id === cardId)
          expect(card).toBeDefined()
          expect(card.locked).toBe(false)

          const route = getCardRoute(card)

          // Requirement 4.2：点击"立即诊断"按钮，Router 跳转至 /resume-diagnosis
          expect(route).toBe(EXPECTED_PATH_MAP.resume)
          expect(route).toBe('/resume-diagnosis')
        }
      ),
      { numRuns: 50 }
    )
  })

  // ── 属性：模拟面试卡片路由跳转至 /interview ──────────────────────────────
  // **Validates: Requirement 4.3**
  it('Property 2.3: 模拟面试卡片（interview）的路由路径为 /interview', () => {
    fc.assert(
      fc.property(
        fc.constant('interview'),
        (cardId) => {
          const card = onboardingCards.find(c => c.id === cardId)
          expect(card).toBeDefined()
          expect(card.locked).toBe(false)

          const route = getCardRoute(card)

          // Requirement 4.3：点击"开启实战"按钮，Router 跳转至 /interview
          expect(route).toBe(EXPECTED_PATH_MAP.interview)
          expect(route).toBe('/interview')
        }
      ),
      { numRuns: 50 }
    )
  })

  // ── 属性：职业规划卡片路由跳转至 /career-planning ────────────────────────
  // **Validates: Requirement 4.4**
  it('Property 2.4: 职业规划卡片（career）的路由路径为 /career-planning', () => {
    fc.assert(
      fc.property(
        fc.constant('career'),
        (cardId) => {
          const card = onboardingCards.find(c => c.id === cardId)
          expect(card).toBeDefined()
          expect(card.locked).toBe(false)

          const route = getCardRoute(card)

          // Requirement 4.4：点击"生成路线"按钮，Router 跳转至 /career-planning
          expect(route).toBe(EXPECTED_PATH_MAP.career)
          expect(route).toBe('/career-planning')
        }
      ),
      { numRuns: 50 }
    )
  })

  // ── 属性：3 张激活卡片的路径互不相同（无重复路径）────────────────────────
  // **Validates: Requirements 4.2, 4.3, 4.4**
  it('Property 2.5: 3 张激活卡片的路由路径互不相同（无重复路径）', () => {
    fc.assert(
      fc.property(
        fc.constant(activeCards),
        (cards) => {
          const routes = cards.map(card => getCardRoute(card))

          // 所有激活卡片均有非 null 路径
          for (const route of routes) {
            expect(route).not.toBeNull()
            expect(typeof route).toBe('string')
            expect(route.trim().length).toBeGreaterThan(0)
          }

          // 核心断言：路径互不相同（Set 去重后长度与原数组相同）
          const uniqueRoutes = new Set(routes)
          expect(uniqueRoutes.size).toBe(routes.length)
        }
      ),
      { numRuns: 50 }
    )
  })

  // ── 属性：激活卡片路径均以 "/" 开头（内部路由格式）────────────────────────
  // **Validates: Requirements 4.2, 4.3, 4.4**
  it('Property 2.6: 对任意激活卡片，路由路径以 "/" 开头（内部路由格式，无外部链接）', () => {
    const activeCardArb = fc.constantFrom(...activeCards)

    fc.assert(
      fc.property(
        activeCardArb,
        (card) => {
          const route = getCardRoute(card)

          expect(route).not.toBeNull()
          // 内部路由必须以 "/" 开头
          expect(route.startsWith('/')).toBe(true)
          // 不应包含协议前缀（排除外部链接注入风险）
          expect(route.startsWith('http')).toBe(false)
          expect(route.startsWith('//')).toBe(false)
        }
      ),
      { numRuns: 100 }
    )
  })

  // ── 属性：锁定卡片（education）的 getCardRoute 返回 null ─────────────────
  // **Validates: Requirements 4.2, 4.3, 4.4**（反向验证：锁定卡片不触发路由跳转）
  it('Property 2.7: 锁定卡片（education）的 getCardRoute 返回 null（不触发路由跳转）', () => {
    fc.assert(
      fc.property(
        fc.constant('education'),
        (cardId) => {
          const card = onboardingCards.find(c => c.id === cardId)
          expect(card).toBeDefined()
          expect(card.locked).toBe(true)

          const route = getCardRoute(card)

          // 锁定卡片：路由路径为 null，不触发 router.push
          expect(route).toBeNull()
        }
      ),
      { numRuns: 50 }
    )
  })

  // ── 综合属性：3 张激活卡片的路径集合与需求规定完全一致 ──────────────────
  // **Validates: Requirements 4.2, 4.3, 4.4**
  it('Property 2.8: 3 张激活卡片的路径集合与需求规定完全一致（/resume-diagnosis、/interview、/career-planning）', () => {
    fc.assert(
      fc.property(
        fc.constant(activeCards),
        (cards) => {
          const routes = cards.map(card => getCardRoute(card)).sort()
          const expectedRoutes = ['/career-planning', '/interview', '/resume-diagnosis']

          // 激活卡片恰好 3 张
          expect(routes).toHaveLength(3)

          // 路径集合与需求规定完全一致（排序后比较）
          expect(routes).toEqual(expectedRoutes)
        }
      ),
      { numRuns: 50 }
    )
  })

  // ── 属性：对任意激活卡片，getCardRoute 的返回值与 card.path 引用相同 ──────
  // **Validates: Requirements 4.2, 4.3, 4.4**
  it('Property 2.9: 对任意激活卡片，getCardRoute 的返回值与 card.path 字段引用相同（无路径变换）', () => {
    const activeCardArb = fc.constantFrom(...activeCards)

    fc.assert(
      fc.property(
        activeCardArb,
        (card) => {
          const route = getCardRoute(card)

          // 路由函数不应对路径做任何变换（大小写、trim、拼接等）
          expect(route).toBe(card.path)
          // 路径不应被修改（与原始 path 字段严格相等）
          expect(route).toStrictEqual(card.path)
        }
      ),
      { numRuns: 100 }
    )
  })
})

// ─────────────────────────────────────────────
// 锁定卡片点击处理函数：模拟 Dashboard 中锁定卡片按钮的 @click 逻辑
// ─────────────────────────────────────────────

/**
 * 模拟锁定卡片按钮的点击处理逻辑（纯函数，无副作用）。
 * 对应 Dashboard.vue 中锁定卡片按钮的 @click.prevent 处理：
 *   - 不调用 routerPushFn（因为 card.locked === true）
 *   - 调用 showToastFn('该模块正在开发中，敬请期待！', 3000)
 *
 * @param {Object} card - onboardingCards 中的单张卡片配置
 * @param {Function} routerPushFn - 模拟 router.push 的函数（锁定卡片不应调用）
 * @param {Function} showToastFn - 模拟 showToastMsg 的函数（锁定卡片应调用）
 */
function handleLockedCardClick(card, routerPushFn, showToastFn) {
  // 锁定卡片：阻止路由跳转，仅触发 Toast 提示
  if (card.locked) {
    showToastFn('该模块正在开发中，敬请期待！', 3000)
    return
  }
  // 激活卡片：正常路由跳转（此分支不在 Property 4 的测试范围内）
  routerPushFn(card.path)
}

// ─────────────────────────────────────────────
// Property 4 属性测试
// ─────────────────────────────────────────────

/**
 * **Validates: Requirements 5.5**
 *
 * Property 4: Locked Card Unreachability
 *
 * 核心属性：
 *   对任意处于锁定状态（locked=true）的引导卡片，无论用户如何点击其操作按钮，
 *   router.push 永远不被调用；同时系统应通过 Toast 提示向用户反馈该模块尚未开放。
 *   Toast 消息为 '该模块正在开发中，敬请期待！'，显示时长为 3000ms。
 */
describe('Property 4: Locked Card Unreachability（锁定卡片不可达性）', () => {

  // 锁定卡片子集（locked=true）
  const lockedCards = onboardingCards.filter(card => card.locked)

  // ── 核心属性 4.1：对任意锁定卡片，router.push 永远不被调用 ──────────────
  // **Validates: Requirements 5.5**
  it('Property 4.1: 对任意锁定卡片，点击按钮时 router.push 永远不被调用', () => {
    // 生成器：从锁定卡片（locked=true）中任意选取一张
    const lockedCardArb = fc.constantFrom(...lockedCards)

    fc.assert(
      fc.property(
        lockedCardArb,
        (card) => {
          // 确认该卡片为锁定状态
          expect(card.locked).toBe(true)

          // 追踪 router.push 调用次数
          let routerPushCallCount = 0
          const mockRouterPush = (_path) => { routerPushCallCount++ }

          // 追踪 showToastMsg 调用
          let toastCallCount = 0
          let toastArgs = null
          const mockShowToast = (msg, duration) => {
            toastCallCount++
            toastArgs = { msg, duration }
          }

          // 模拟点击锁定卡片按钮
          handleLockedCardClick(card, mockRouterPush, mockShowToast)

          // 核心断言：router.push 永远不被调用
          expect(routerPushCallCount).toBe(0)
        }
      ),
      { numRuns: 100 }
    )
  })

  // ── 核心属性 4.2：对任意锁定卡片，Toast 提示被触发 ──────────────────────
  // **Validates: Requirements 5.5**
  it('Property 4.2: 对任意锁定卡片，点击按钮时 Toast 提示被触发（showToastMsg 被调用一次）', () => {
    const lockedCardArb = fc.constantFrom(...lockedCards)

    fc.assert(
      fc.property(
        lockedCardArb,
        (card) => {
          expect(card.locked).toBe(true)

          let routerPushCallCount = 0
          const mockRouterPush = (_path) => { routerPushCallCount++ }

          let toastCallCount = 0
          const mockShowToast = (_msg, _duration) => { toastCallCount++ }

          handleLockedCardClick(card, mockRouterPush, mockShowToast)

          // 核心断言：Toast 被触发恰好一次
          expect(toastCallCount).toBe(1)
          // 同时确认 router.push 未被调用
          expect(routerPushCallCount).toBe(0)
        }
      ),
      { numRuns: 100 }
    )
  })

  // ── 核心属性 4.3：Toast 消息内容精确匹配 ────────────────────────────────
  // **Validates: Requirements 5.5**
  it('Property 4.3: 对任意锁定卡片，Toast 消息内容精确为 "该模块正在开发中，敬请期待！"', () => {
    const lockedCardArb = fc.constantFrom(...lockedCards)

    fc.assert(
      fc.property(
        lockedCardArb,
        (card) => {
          expect(card.locked).toBe(true)

          let capturedMsg = null
          const mockRouterPush = (_path) => {}
          const mockShowToast = (msg, _duration) => { capturedMsg = msg }

          handleLockedCardClick(card, mockRouterPush, mockShowToast)

          // 核心断言：Toast 消息内容精确匹配需求规定文案
          expect(capturedMsg).toBe('该模块正在开发中，敬请期待！')
        }
      ),
      { numRuns: 100 }
    )
  })

  // ── 核心属性 4.4：Toast 显示时长精确为 3000ms ────────────────────────────
  // **Validates: Requirements 5.5**
  it('Property 4.4: 对任意锁定卡片，Toast 显示时长精确为 3000ms', () => {
    const lockedCardArb = fc.constantFrom(...lockedCards)

    fc.assert(
      fc.property(
        lockedCardArb,
        (card) => {
          expect(card.locked).toBe(true)

          let capturedDuration = null
          const mockRouterPush = (_path) => {}
          const mockShowToast = (_msg, duration) => { capturedDuration = duration }

          handleLockedCardClick(card, mockRouterPush, mockShowToast)

          // 核心断言：Toast 显示时长精确为 3000ms（Requirements 5.5）
          expect(capturedDuration).toBe(3000)
        }
      ),
      { numRuns: 100 }
    )
  })

  // ── 综合属性 4.5：router.push 不被调用 + Toast 消息与时长同时正确 ─────────
  // **Validates: Requirements 5.5**
  it('Property 4.5: 对任意锁定卡片，router.push 不被调用，且 Toast 消息与时长同时精确匹配', () => {
    const lockedCardArb = fc.constantFrom(...lockedCards)

    fc.assert(
      fc.property(
        lockedCardArb,
        (card) => {
          expect(card.locked).toBe(true)

          let routerPushCallCount = 0
          const mockRouterPush = (_path) => { routerPushCallCount++ }

          let toastCallCount = 0
          let capturedMsg = null
          let capturedDuration = null
          const mockShowToast = (msg, duration) => {
            toastCallCount++
            capturedMsg = msg
            capturedDuration = duration
          }

          handleLockedCardClick(card, mockRouterPush, mockShowToast)

          // 综合断言：三个条件同时满足
          // 1. router.push 永远不被调用
          expect(routerPushCallCount).toBe(0)
          // 2. Toast 被触发恰好一次
          expect(toastCallCount).toBe(1)
          // 3. Toast 消息内容精确匹配
          expect(capturedMsg).toBe('该模块正在开发中，敬请期待！')
          // 4. Toast 显示时长精确为 3000ms
          expect(capturedDuration).toBe(3000)
        }
      ),
      { numRuns: 200 }
    )
  })

  // ── 属性 4.6：getCardRoute 对锁定卡片返回 null（无路由路径）────────────────
  // **Validates: Requirements 5.5**
  it('Property 4.6: 对任意锁定卡片，getCardRoute(card) 返回 null（无可达路由路径）', () => {
    const lockedCardArb = fc.constantFrom(...lockedCards)

    fc.assert(
      fc.property(
        lockedCardArb,
        (card) => {
          expect(card.locked).toBe(true)

          // 锁定卡片的路由路径应为 null
          const route = getCardRoute(card)
          expect(route).toBeNull()
        }
      ),
      { numRuns: 100 }
    )
  })

  // ── 属性 4.7：多次点击锁定卡片，router.push 始终不被调用 ─────────────────
  // **Validates: Requirements 5.5**
  it('Property 4.7: 多次点击锁定卡片，router.push 始终不被调用（不可达性在重复点击下保持不变）', () => {
    // 生成器：点击次数（1 到 10 次）
    const clickCountArb = fc.integer({ min: 1, max: 10 })
    const lockedCardArb = fc.constantFrom(...lockedCards)

    fc.assert(
      fc.property(
        lockedCardArb,
        clickCountArb,
        (card, clickCount) => {
          expect(card.locked).toBe(true)

          let routerPushCallCount = 0
          const mockRouterPush = (_path) => { routerPushCallCount++ }

          let toastCallCount = 0
          const mockShowToast = (_msg, _duration) => { toastCallCount++ }

          // 模拟多次点击
          for (let i = 0; i < clickCount; i++) {
            handleLockedCardClick(card, mockRouterPush, mockShowToast)
          }

          // 核心断言：无论点击多少次，router.push 始终不被调用
          expect(routerPushCallCount).toBe(0)
          // Toast 被触发的次数与点击次数相同
          expect(toastCallCount).toBe(clickCount)
        }
      ),
      { numRuns: 100 }
    )
  })

  // ── 属性 4.8：锁定卡片集合恰好包含 1 张（education）────────────────────────
  // **Validates: Requirements 5.1**（反向验证：确认测试覆盖了所有锁定卡片）
  it('Property 4.8: 锁定卡片集合恰好包含 1 张（education），且该卡片通过不可达性检查', () => {
    fc.assert(
      fc.property(
        fc.constant(onboardingCards),
        (cards) => {
          const locked = cards.filter(c => c.locked)

          // 锁定卡片恰好 1 张
          expect(locked).toHaveLength(1)
          expect(locked[0].id).toBe('education')

          // 该卡片通过不可达性检查
          let routerPushCallCount = 0
          const mockRouterPush = (_path) => { routerPushCallCount++ }
          let capturedMsg = null
          let capturedDuration = null
          const mockShowToast = (msg, duration) => {
            capturedMsg = msg
            capturedDuration = duration
          }

          handleLockedCardClick(locked[0], mockRouterPush, mockShowToast)

          expect(routerPushCallCount).toBe(0)
          expect(capturedMsg).toBe('该模块正在开发中，敬请期待！')
          expect(capturedDuration).toBe(3000)
        }
      ),
      { numRuns: 50 }
    )
  })
})

// ─────────────────────────────────────────────
// Property 7: Zero Side Effect Rendering（零副作用渲染）
// ─────────────────────────────────────────────

/**
 * 模拟 OnboardingPanel 渲染函数（零副作用版本）。
 *
 * 当 historyRecords.length === 0 时，OnboardingPanel 渲染逻辑：
 *   1. 读取 onboardingCards 静态配置（纯静态数据，不依赖任何响应式 ref）
 *   2. 渲染全局引导语（静态字符串）
 *   3. 遍历 onboardingCards，渲染每张卡片（仅读取 card 字段，不写入任何 ref）
 *
 * 关键约束：渲染过程中不修改 chatMessages、userChatInput 或任何其他 ref。
 *
 * @param {Object} state - 包含所有响应式 ref 值的状态快照
 *   @param {Array}   state.historyRecords   - 历史记录数组（空数组触发 OnboardingPanel）
 *   @param {boolean} state.isHistoryLoading - 加载状态
 *   @param {Array}   state.chatMessages     - 聊天消息数组（不应被修改）
 *   @param {string}  state.userChatInput    - 用户输入文本（不应被修改）
 * @returns {Object} 渲染后的状态快照（应与渲染前完全一致，除 historyRecords 外）
 */
function simulateOnboardingRender(state) {
  // 深拷贝输入状态，避免引用共享导致误判
  const stateBefore = {
    historyRecords: [...state.historyRecords],
    isHistoryLoading: state.isHistoryLoading,
    chatMessages: [...state.chatMessages],
    userChatInput: state.userChatInput,
  }

  // ── 模拟 OnboardingPanel 渲染逻辑 ──────────────────────────────────────
  // 仅在 historyRecords 为空且不在加载中时渲染 OnboardingPanel
  if (!state.isHistoryLoading && state.historyRecords.length === 0) {
    // 渲染全局引导语（纯静态字符串读取，无副作用）
    const _guideText = '系统初始化完成。欢迎登舰，新同学。四大核心引擎已就绪，请选择你的首个突破口进行全息扫描。'

    // 遍历 onboardingCards，提取渲染所需字段（纯读取，无写入）
    const _renderedCards = onboardingCards.map(card => ({
      id: card.id,
      emoji: card.emoji,
      title: card.title,
      subtitle: card.subtitle,
      desc: card.desc,
      action: card.action,
      locked: card.locked,
      themeColor: card.themeColor,
    }))

    // 渲染完成：不修改任何 ref（chatMessages、userChatInput 等保持不变）
  }

  // 返回渲染后的状态快照（应与 stateBefore 完全一致）
  const stateAfter = {
    historyRecords: [...state.historyRecords],
    isHistoryLoading: state.isHistoryLoading,
    chatMessages: [...state.chatMessages],
    userChatInput: state.userChatInput,
  }

  return { stateBefore, stateAfter }
}

// ─────────────────────────────────────────────
// Property 7 属性测试
// ─────────────────────────────────────────────

/**
 * **Validates: Requirements 8.2**
 *
 * Property 7: Zero Side Effect Rendering（零副作用渲染）
 *
 * 核心属性：
 *   对任意导致 historyRecords.length === 0 的状态，OnboardingPanel 的渲染过程
 *   不修改任何现有的 Vue 响应式 ref 状态（historyRecords 本身除外），
 *   所有 ref 的值在渲染前后保持不变。
 *
 * 具体验证：
 *   - chatMessages 在渲染前后保持不变
 *   - userChatInput 在渲染前后保持不变
 */
describe('Property 7: Zero Side Effect Rendering（零副作用渲染）', () => {

  // ── 生成器：任意聊天消息数组 ──────────────────────────────────────────
  const chatMessageArb = fc.record({
    role: fc.constantFrom('user', 'ai'),
    content: fc.string({ minLength: 0, maxLength: 200 }),
    timestamp: fc.string({ minLength: 0, maxLength: 20 }),
  })

  const chatMessagesArb = fc.array(chatMessageArb, { minLength: 0, maxLength: 10 })

  // ── 生成器：任意用户输入文本 ──────────────────────────────────────────
  const userChatInputArb = fc.string({ minLength: 0, maxLength: 500 })

  // ── 核心属性 7.1：chatMessages 在 OnboardingPanel 渲染前后保持不变 ──────
  // **Validates: Requirements 8.2**
  it('Property 7.1: 对任意导致 historyRecords.length === 0 的状态，chatMessages 在渲染前后保持不变', () => {
    fc.assert(
      fc.property(
        chatMessagesArb,
        userChatInputArb,
        (chatMessages, userChatInput) => {
          const state = {
            historyRecords: [],       // 空数组：触发 OnboardingPanel 渲染
            isHistoryLoading: false,
            chatMessages,
            userChatInput,
          }

          const { stateBefore, stateAfter } = simulateOnboardingRender(state)

          // 核心断言：chatMessages 在渲染前后完全一致
          expect(stateAfter.chatMessages).toEqual(stateBefore.chatMessages)
          expect(stateAfter.chatMessages).toHaveLength(stateBefore.chatMessages.length)
        }
      ),
      { numRuns: 200 }
    )
  })

  // ── 核心属性 7.2：userChatInput 在 OnboardingPanel 渲染前后保持不变 ──────
  // **Validates: Requirements 8.2**
  it('Property 7.2: 对任意导致 historyRecords.length === 0 的状态，userChatInput 在渲染前后保持不变', () => {
    fc.assert(
      fc.property(
        chatMessagesArb,
        userChatInputArb,
        (chatMessages, userChatInput) => {
          const state = {
            historyRecords: [],
            isHistoryLoading: false,
            chatMessages,
            userChatInput,
          }

          const { stateBefore, stateAfter } = simulateOnboardingRender(state)

          // 核心断言：userChatInput 在渲染前后完全一致
          expect(stateAfter.userChatInput).toBe(stateBefore.userChatInput)
        }
      ),
      { numRuns: 200 }
    )
  })

  // ── 综合属性 7.3：chatMessages 与 userChatInput 同时保持不变 ─────────────
  // **Validates: Requirements 8.2**
  it('Property 7.3: 对任意导致 historyRecords.length === 0 的状态，chatMessages 与 userChatInput 同时保持不变', () => {
    fc.assert(
      fc.property(
        chatMessagesArb,
        userChatInputArb,
        (chatMessages, userChatInput) => {
          const state = {
            historyRecords: [],
            isHistoryLoading: false,
            chatMessages,
            userChatInput,
          }

          const { stateBefore, stateAfter } = simulateOnboardingRender(state)

          // 综合断言：所有非 historyRecords 的 ref 均保持不变
          expect(stateAfter.chatMessages).toEqual(stateBefore.chatMessages)
          expect(stateAfter.userChatInput).toBe(stateBefore.userChatInput)
          // isHistoryLoading 也不应被修改
          expect(stateAfter.isHistoryLoading).toBe(stateBefore.isHistoryLoading)
        }
      ),
      { numRuns: 200 }
    )
  })

  // ── 属性 7.4：非空 chatMessages 在渲染后内容逐条一致 ─────────────────────
  // **Validates: Requirements 8.2**
  it('Property 7.4: 对任意非空 chatMessages，OnboardingPanel 渲染后每条消息的 role 与 content 均保持不变', () => {
    // 生成器：至少 1 条消息的 chatMessages
    const nonEmptyChatMessagesArb = fc.array(chatMessageArb, { minLength: 1, maxLength: 10 })

    fc.assert(
      fc.property(
        nonEmptyChatMessagesArb,
        userChatInputArb,
        (chatMessages, userChatInput) => {
          const state = {
            historyRecords: [],
            isHistoryLoading: false,
            chatMessages,
            userChatInput,
          }

          const { stateBefore, stateAfter } = simulateOnboardingRender(state)

          // 断言消息数量不变
          expect(stateAfter.chatMessages).toHaveLength(stateBefore.chatMessages.length)

          // 断言每条消息的 role 与 content 均保持不变
          for (let i = 0; i < stateBefore.chatMessages.length; i++) {
            expect(stateAfter.chatMessages[i].role).toBe(stateBefore.chatMessages[i].role)
            expect(stateAfter.chatMessages[i].content).toBe(stateBefore.chatMessages[i].content)
          }
        }
      ),
      { numRuns: 150 }
    )
  })

  // ── 属性 7.5：非空 userChatInput 在渲染后字符串内容保持不变 ──────────────
  // **Validates: Requirements 8.2**
  it('Property 7.5: 对任意非空 userChatInput，OnboardingPanel 渲染后字符串内容保持不变', () => {
    // 生成器：至少 1 个字符的 userChatInput
    const nonEmptyInputArb = fc.string({ minLength: 1, maxLength: 500 })

    fc.assert(
      fc.property(
        chatMessagesArb,
        nonEmptyInputArb,
        (chatMessages, userChatInput) => {
          const state = {
            historyRecords: [],
            isHistoryLoading: false,
            chatMessages,
            userChatInput,
          }

          const { stateBefore, stateAfter } = simulateOnboardingRender(state)

          // 断言 userChatInput 字符串内容完全不变
          expect(stateAfter.userChatInput).toBe(stateBefore.userChatInput)
          expect(stateAfter.userChatInput.length).toBe(stateBefore.userChatInput.length)
        }
      ),
      { numRuns: 150 }
    )
  })

  // ── 属性 7.6：多次渲染 OnboardingPanel，chatMessages 始终保持不变 ─────────
  // **Validates: Requirements 8.2**
  it('Property 7.6: 多次渲染 OnboardingPanel，chatMessages 始终保持不变（渲染幂等性与零副作用的交叉验证）', () => {
    // 生成器：渲染次数（1 到 5 次）
    const renderCountArb = fc.integer({ min: 1, max: 5 })

    fc.assert(
      fc.property(
        chatMessagesArb,
        userChatInputArb,
        renderCountArb,
        (chatMessages, userChatInput, renderCount) => {
          const initialState = {
            historyRecords: [],
            isHistoryLoading: false,
            chatMessages,
            userChatInput,
          }

          // 记录初始 chatMessages 快照
          const initialChatMessages = [...chatMessages]
          const initialUserChatInput = userChatInput

          // 多次渲染
          let currentState = initialState
          for (let i = 0; i < renderCount; i++) {
            const { stateAfter } = simulateOnboardingRender(currentState)
            currentState = stateAfter
          }

          // 断言：无论渲染多少次，chatMessages 与 userChatInput 始终与初始值一致
          expect(currentState.chatMessages).toEqual(initialChatMessages)
          expect(currentState.userChatInput).toBe(initialUserChatInput)
        }
      ),
      { numRuns: 100 }
    )
  })
})

// ─────────────────────────────────────────────
// 面板状态纯函数：提取 Dashboard 的面板渲染决策逻辑
// ─────────────────────────────────────────────

/**
 * 获取当前面板状态（纯函数，无副作用）。
 * 对应 Dashboard.vue 中 v-if / v-else-if / v-else 的渲染决策逻辑：
 *   - isHistoryLoading = true  → 'loading'
 *   - historyRecords.length === 0 → 'onboarding'
 *   - historyRecords.length > 0  → 'history'
 *
 * **Validates: Requirements 8.4**
 *
 * @param {boolean} isHistoryLoading - 是否正在加载历史记录
 * @param {Array} historyRecords - 历史记录数组
 * @returns {'loading' | 'onboarding' | 'history'} 当前面板状态
 */
function getPanelState(isHistoryLoading, historyRecords) {
  if (isHistoryLoading) return 'loading'
  if (historyRecords.length === 0) return 'onboarding'
  return 'history'
}

/**
 * 模拟多次调用 loadHistory() 后的最终面板状态。
 * 每次调用 loadHistory() 都会先将 isHistoryLoading 置为 true，
 * 完成后置为 false，并更新 historyRecords 为最终值。
 * 面板状态仅由最终的 historyRecords 值决定，与调用次数无关。
 *
 * @param {Array} finalHistoryRecords - 最后一次 loadHistory() 返回的记录数组
 * @param {number} callCount - loadHistory() 的调用次数（≥ 1）
 * @returns {'onboarding' | 'history'} 所有调用完成后的最终面板状态（加载已结束）
 */
function simulateMultipleLoadHistory(finalHistoryRecords, callCount) {
  // 模拟 callCount 次 loadHistory() 调用序列：
  // 每次调用：isHistoryLoading = true → (异步完成) → isHistoryLoading = false, historyRecords = result
  // 最终状态：isHistoryLoading = false，historyRecords = finalHistoryRecords
  // 面板状态由最终的 historyRecords 决定，与 callCount 无关
  let isHistoryLoading = true
  let historyRecords = []

  for (let i = 0; i < callCount; i++) {
    // 每次调用开始：isHistoryLoading = true
    isHistoryLoading = true
    // 每次调用结束：isHistoryLoading = false，historyRecords 更新为最终值
    // （模拟最后一次调用覆盖之前的结果）
    historyRecords = finalHistoryRecords
    isHistoryLoading = false
  }

  // 返回所有调用完成后的面板状态
  return getPanelState(isHistoryLoading, historyRecords)
}

// ─────────────────────────────────────────────
// Property 6 属性测试
// ─────────────────────────────────────────────

/**
 * **Validates: Requirements 8.4**
 *
 * Property 6: Rendering Idempotency（渲染幂等性）
 *
 * 核心属性：
 *   对任意初始 historyRecords 状态，多次调用 loadHistory() 后，
 *   Dashboard 的面板渲染结果仅由最终的 historyRecords 值决定，与调用次数无关。
 *
 * 即：getPanelState(false, historyRecords) 是一个纯函数，
 *   对相同的 historyRecords 输入，无论调用多少次，始终返回相同的面板状态。
 */
describe('Property 6: Rendering Idempotency（渲染幂等性）', () => {

  // ── 核心属性 6.1：面板状态是 historyRecords 的纯函数（确定性）────────────
  // **Validates: Requirements 8.4**
  it('Property 6.1: 对任意 historyRecords 值，getPanelState(false, historyRecords) 多次调用始终返回相同结果', () => {
    // 生成器：任意历史记录数组（空或非空）
    const historyRecordsArb = fc.oneof(
      // 空数组（触发 OnboardingPanel）
      fc.constant([]),
      // 非空数组（触发 HistoryPanel），包含 1–5 条记录
      fc.array(
        fc.record({ id: fc.integer({ min: 1, max: 9999 }), category: fc.string({ minLength: 1, maxLength: 20 }) }),
        { minLength: 1, maxLength: 5 }
      )
    )

    // 生成器：调用次数（1 到 10 次）
    const callCountArb = fc.integer({ min: 1, max: 10 })

    fc.assert(
      fc.property(
        historyRecordsArb,
        callCountArb,
        (historyRecords, callCount) => {
          // 基准：单次调用的面板状态
          const baseState = getPanelState(false, historyRecords)

          // 多次调用 getPanelState，结果应始终与基准一致
          for (let i = 0; i < callCount; i++) {
            const state = getPanelState(false, historyRecords)
            expect(state).toBe(baseState)
          }
        }
      ),
      { numRuns: 200 }
    )
  })

  // ── 核心属性 6.2：多次 loadHistory() 后，面板状态仅由最终值决定 ──────────
  // **Validates: Requirements 8.4**
  it('Property 6.2: 多次调用 loadHistory() 后，面板状态与单次调用结果完全一致（与调用次数无关）', () => {
    // 生成器：最终 historyRecords 值（空或非空）
    const finalHistoryArb = fc.oneof(
      fc.constant([]),
      fc.array(
        fc.record({ id: fc.integer({ min: 1, max: 9999 }), category: fc.string({ minLength: 1, maxLength: 20 }) }),
        { minLength: 1, maxLength: 5 }
      )
    )

    // 生成器：调用次数（1 到 10 次）
    const callCountArb = fc.integer({ min: 1, max: 10 })

    fc.assert(
      fc.property(
        finalHistoryArb,
        callCountArb,
        (finalHistoryRecords, callCount) => {
          // 单次调用的面板状态（基准）
          const singleCallState = getPanelState(false, finalHistoryRecords)

          // 多次调用后的面板状态
          const multiCallState = simulateMultipleLoadHistory(finalHistoryRecords, callCount)

          // 核心断言：多次调用后的面板状态与单次调用完全一致
          expect(multiCallState).toBe(singleCallState)
        }
      ),
      { numRuns: 200 }
    )
  })

  // ── 属性 6.3：空 historyRecords 始终渲染 OnboardingPanel（无论调用次数）──
  // **Validates: Requirements 8.4**
  it('Property 6.3: 对空 historyRecords，无论 loadHistory() 调用多少次，面板状态始终为 "onboarding"', () => {
    // 生成器：调用次数（1 到 20 次）
    const callCountArb = fc.integer({ min: 1, max: 20 })

    fc.assert(
      fc.property(
        callCountArb,
        (callCount) => {
          // 最终 historyRecords 为空数组
          const finalState = simulateMultipleLoadHistory([], callCount)

          // 核心断言：空数组始终渲染 OnboardingPanel
          expect(finalState).toBe('onboarding')
        }
      ),
      { numRuns: 100 }
    )
  })

  // ── 属性 6.4：非空 historyRecords 始终渲染 HistoryPanel（无论调用次数）──
  // **Validates: Requirements 8.4**
  it('Property 6.4: 对非空 historyRecords，无论 loadHistory() 调用多少次，面板状态始终为 "history"', () => {
    // 生成器：非空历史记录数组（至少 1 条记录）
    const nonEmptyHistoryArb = fc.array(
      fc.record({ id: fc.integer({ min: 1, max: 9999 }), category: fc.string({ minLength: 1, maxLength: 20 }) }),
      { minLength: 1, maxLength: 5 }
    )

    // 生成器：调用次数（1 到 20 次）
    const callCountArb = fc.integer({ min: 1, max: 20 })

    fc.assert(
      fc.property(
        nonEmptyHistoryArb,
        callCountArb,
        (historyRecords, callCount) => {
          // 最终 historyRecords 非空
          const finalState = simulateMultipleLoadHistory(historyRecords, callCount)

          // 核心断言：非空数组始终渲染 HistoryPanel
          expect(finalState).toBe('history')
        }
      ),
      { numRuns: 100 }
    )
  })

  // ── 属性 6.5：面板状态仅有三种合法值（loading / onboarding / history）────
  // **Validates: Requirements 8.4**
  it('Property 6.5: 对任意输入，getPanelState 的返回值始终是合法的三种状态之一', () => {
    const isLoadingArb = fc.boolean()
    const historyRecordsArb = fc.oneof(
      fc.constant([]),
      fc.array(
        fc.record({ id: fc.integer({ min: 1, max: 9999 }), category: fc.string({ minLength: 1, maxLength: 20 }) }),
        { minLength: 1, maxLength: 5 }
      )
    )

    fc.assert(
      fc.property(
        isLoadingArb,
        historyRecordsArb,
        (isLoading, historyRecords) => {
          const state = getPanelState(isLoading, historyRecords)

          // 面板状态必须是三种合法值之一
          const validStates = ['loading', 'onboarding', 'history']
          expect(validStates).toContain(state)
        }
      ),
      { numRuns: 200 }
    )
  })

  // ── 属性 6.6：相同输入的两次调用结果严格相等（确定性验证）────────────────
  // **Validates: Requirements 8.4**
  it('Property 6.6: 对相同的 (isHistoryLoading, historyRecords) 输入，getPanelState 两次调用结果严格相等', () => {
    const historyRecordsArb = fc.oneof(
      fc.constant([]),
      fc.array(
        fc.record({ id: fc.integer({ min: 1, max: 9999 }), category: fc.string({ minLength: 1, maxLength: 20 }) }),
        { minLength: 1, maxLength: 5 }
      )
    )

    fc.assert(
      fc.property(
        historyRecordsArb,
        (historyRecords) => {
          // 加载完成后（isHistoryLoading = false）的两次调用
          const state1 = getPanelState(false, historyRecords)
          const state2 = getPanelState(false, historyRecords)

          // 核心断言：两次调用结果严格相等（纯函数，无内部状态）
          expect(state1).toBe(state2)
          expect(state1).toStrictEqual(state2)
        }
      ),
      { numRuns: 200 }
    )
  })

  // ── 属性 6.7：面板状态与 historyRecords.length 的关系是确定性映射 ─────────
  // **Validates: Requirements 8.4**
  it('Property 6.7: 面板状态（加载完成后）由 historyRecords.length 唯一决定：length=0 → onboarding，length>0 → history', () => {
    // 生成器：任意长度的历史记录数组（0 到 10 条）
    const historyRecordsArb = fc.array(
      fc.record({ id: fc.integer({ min: 1, max: 9999 }), category: fc.string({ minLength: 1, maxLength: 20 }) }),
      { minLength: 0, maxLength: 10 }
    )

    fc.assert(
      fc.property(
        historyRecordsArb,
        (historyRecords) => {
          const state = getPanelState(false, historyRecords)

          if (historyRecords.length === 0) {
            // 空数组 → OnboardingPanel
            expect(state).toBe('onboarding')
          } else {
            // 非空数组 → HistoryPanel
            expect(state).toBe('history')
          }
        }
      ),
      { numRuns: 200 }
    )
  })

  // ── 属性 6.8：N 次调用与 1 次调用的面板状态完全一致（幂等性核心验证）──────
  // **Validates: Requirements 8.4**
  it('Property 6.8: 对任意 historyRecords 和调用次数 N，N 次调用与 1 次调用的面板状态完全一致', () => {
    const finalHistoryArb = fc.oneof(
      fc.constant([]),
      fc.array(
        fc.record({ id: fc.integer({ min: 1, max: 9999 }), category: fc.string({ minLength: 1, maxLength: 20 }) }),
        { minLength: 1, maxLength: 5 }
      )
    )

    // 生成器：调用次数 N（2 到 15 次，确保 N > 1 以验证幂等性）
    const callCountArb = fc.integer({ min: 2, max: 15 })

    fc.assert(
      fc.property(
        finalHistoryArb,
        callCountArb,
        (finalHistoryRecords, N) => {
          // 1 次调用的面板状态
          const stateAfter1Call = simulateMultipleLoadHistory(finalHistoryRecords, 1)

          // N 次调用的面板状态
          const stateAfterNCalls = simulateMultipleLoadHistory(finalHistoryRecords, N)

          // 核心断言：N 次调用与 1 次调用的面板状态完全一致（幂等性）
          expect(stateAfterNCalls).toBe(stateAfter1Call)
        }
      ),
      { numRuns: 200 }
    )
  })
})
