/**
 * docxExport.js —— Tiptap JSON ↔ docx 文档 的导出工具
 *
 * 设计目标：
 *   - 仅做"基础富文本 → DOCX 段落"的最小映射，不追求完美简历模板
 *   - 浏览器端 Blob 生成（docx 包内置 Packer.toBlob），不依赖后端
 *   - 支持节点：doc / paragraph / heading(2|3) / bulletList / orderedList / listItem / blockquote / hardBreak
 *   - 支持 marks：bold / italic
 *   - 未识别节点：尽量递归提取 text；提取失败则跳过，不报错
 *
 * 由 KnowledgeBase.vue 调用：
 *   import { exportDocxFromDocument } from '@/utils/docxExport'
 *   await exportDocxFromDocument(doc, getTypeLabel)
 */

import {
  Document,
  Packer,
  Paragraph,
  TextRun,
  HeadingLevel,
  AlignmentType,
  BorderStyle
} from 'docx'

// ─────────────────────────────────────────────
// 工具：文件名安全化（与 KnowledgeBase.vue 行为一致）
// ─────────────────────────────────────────────

/**
 * 将文档标题转换为合法文件名：
 *   - 替换 Windows / POSIX 非法字符 \ / : * ? " < > | 与控制字符
 *   - 合并连续 -
 *   - 长度限制 80
 *   - 全空时回退 "未命名文档"
 */
export function sanitizeDocxFilename(raw) {
  const fallback = '未命名文档'
  const src = (raw || '').trim() || fallback
  let cleaned = src.replace(/[\\/:*?"<>|\x00-\x1F]/g, '-').trim()
  cleaned = cleaned.replace(/-{2,}/g, '-')
  if (cleaned.length > 80) cleaned = cleaned.slice(0, 80).trim()
  return cleaned || fallback
}

// ─────────────────────────────────────────────
// 内部：Tiptap text node + marks → docx TextRun
// ─────────────────────────────────────────────

/**
 * 把 Tiptap 的 text node 转成一个或多个 TextRun。
 * - bold / italic mark → 对应的 docx 选项
 * - 未识别 mark：忽略（保留 text）
 */
function textNodeToRuns(node, extra = {}) {
  const text = node && typeof node.text === 'string' ? node.text : ''
  if (!text) return []

  const marks = Array.isArray(node.marks) ? node.marks : []
  const opts = { text, ...extra }

  for (const mark of marks) {
    if (!mark || typeof mark.type !== 'string') continue
    if (mark.type === 'bold') opts.bold = true
    else if (mark.type === 'italic') opts.italics = true
    // 未识别 mark 静默忽略
  }

  return [new TextRun(opts)]
}

/**
 * 把 Tiptap inline children 数组转成 TextRun[] 列表。
 * 处理：
 *   - text 节点
 *   - hardBreak 节点（→ 换行 TextRun({ break: 1 })）
 *   - 其他未知 inline：尽量递归提取 text
 */
function inlineChildrenToRuns(children, extra = {}) {
  if (!Array.isArray(children)) return []
  const runs = []

  for (const child of children) {
    if (!child || typeof child !== 'object') continue
    const t = child.type

    if (t === 'text') {
      runs.push(...textNodeToRuns(child, extra))
    } else if (t === 'hardBreak') {
      runs.push(new TextRun({ break: 1 }))
    } else if (Array.isArray(child.content)) {
      // 兜底：递归继续提取 text
      runs.push(...inlineChildrenToRuns(child.content, extra))
    } else if (typeof child.text === 'string' && child.text) {
      runs.push(new TextRun({ text: child.text, ...extra }))
    }
    // 其他未识别 inline 节点：跳过
  }

  return runs
}

// ─────────────────────────────────────────────
// 内部：块级节点 → Paragraph[]
// ─────────────────────────────────────────────

/**
 * 段落（普通正文）
 */
function paragraphNodeToParagraphs(node) {
  const runs = inlineChildrenToRuns(node.content)
  return [new Paragraph({ children: runs })]
}

/**
 * 标题（heading）。Tiptap StarterKit 默认 level 为 1 / 2 / 3。
 * 我们仅显式支持 h2 / h3；其他 level 退化为 h2。
 */
function headingNodeToParagraphs(node) {
  const level = node.attrs && typeof node.attrs.level === 'number' ? node.attrs.level : 2
  const headingLevel = level === 3 ? HeadingLevel.HEADING_3 : HeadingLevel.HEADING_2

  const runs = inlineChildrenToRuns(node.content)
  return [new Paragraph({ heading: headingLevel, children: runs })]
}

/**
 * 列表（bulletList / orderedList）。
 * 通过 docx 的 numbering 配置（外部 Document 注入）让 Word / WPS 渲染编号或项目符号。
 */
function listNodeToParagraphs(node, ordered) {
  const items = Array.isArray(node.content) ? node.content : []
  const paragraphs = []

  for (const item of items) {
    if (!item || item.type !== 'listItem' || !Array.isArray(item.content)) continue

    // listItem 内部通常是 paragraph（可能多个）；逐个转换为 Paragraph，但只有第一个 Paragraph 套上 bullet/numbering
    let firstParaApplied = false

    for (const child of item.content) {
      if (!child || typeof child !== 'object') continue

      if (child.type === 'paragraph') {
        const runs = inlineChildrenToRuns(child.content)
        const opts = { children: runs }
        if (!firstParaApplied) {
          if (ordered) opts.numbering = { reference: 'docx-export-ordered', level: 0 }
          else opts.bullet = { level: 0 }
          firstParaApplied = true
        }
        paragraphs.push(new Paragraph(opts))
      } else {
        // listItem 里出现嵌套块，递归一次（深度 1，不展开嵌套列表为新编号序列）
        const inner = blockNodeToParagraphs(child)
        for (const p of inner) paragraphs.push(p)
      }
    }
  }

  return paragraphs
}

/**
 * 引用块（blockquote）。
 * docx 没有原生 quote 样式；用左侧灰色边框 + 缩进 + 斜体的段落组合模拟。
 */
function blockquoteNodeToParagraphs(node) {
  const inner = Array.isArray(node.content) ? node.content : []
  const paragraphs = []

  for (const child of inner) {
    if (!child || typeof child !== 'object') continue

    if (child.type === 'paragraph') {
      const runs = inlineChildrenToRuns(child.content, { italics: true })
      paragraphs.push(
        new Paragraph({
          children: runs,
          indent: { left: 360 }, // 0.25 inch
          border: {
            left: { color: '888888', size: 18, style: BorderStyle.SINGLE, space: 8 }
          }
        })
      )
    } else {
      // 兜底：递归
      const inner2 = blockNodeToParagraphs(child)
      for (const p of inner2) paragraphs.push(p)
    }
  }

  return paragraphs
}

/**
 * 块级派发。未知节点尝试递归提取 text，失败则跳过。
 */
function blockNodeToParagraphs(node) {
  if (!node || typeof node !== 'object') return []
  switch (node.type) {
    case 'paragraph':
      return paragraphNodeToParagraphs(node)
    case 'heading':
      return headingNodeToParagraphs(node)
    case 'bulletList':
      return listNodeToParagraphs(node, /* ordered */ false)
    case 'orderedList':
      return listNodeToParagraphs(node, /* ordered */ true)
    case 'blockquote':
      return blockquoteNodeToParagraphs(node)
    case 'horizontalRule':
      // 简单实现：一段空段落 + 下边框，避免引入新 import
      return [
        new Paragraph({
          children: [],
          border: {
            bottom: { color: 'BBBBBB', size: 6, style: BorderStyle.SINGLE, space: 4 }
          }
        })
      ]
    case 'codeBlock': {
      // 退化为等宽字体段落
      const text = (node.content || [])
        .map((c) => (c && typeof c.text === 'string' ? c.text : ''))
        .join('')
      return [
        new Paragraph({
          children: [new TextRun({ text, font: 'Consolas' })]
        })
      ]
    }
    default:
      // 未知节点：尝试递归提取 text，至少避免内容丢失
      if (Array.isArray(node.content)) {
        const runs = inlineChildrenToRuns(node.content)
        if (runs.length > 0) return [new Paragraph({ children: runs })]
        // 若全是块级子节点，逐个递归
        const out = []
        for (const child of node.content) {
          out.push(...blockNodeToParagraphs(child))
        }
        return out
      }
      return []
  }
}

// ─────────────────────────────────────────────
// 内部：构造 Header（标题 + 类型 + 更新时间 + 空行）
// ─────────────────────────────────────────────

function buildHeaderParagraphs(doc, typeLabel, updatedAtStr) {
  return [
    new Paragraph({
      heading: HeadingLevel.HEADING_1,
      alignment: AlignmentType.LEFT,
      children: [new TextRun({ text: doc.title || '未命名文档', bold: true })]
    }),
    new Paragraph({
      children: [new TextRun({ text: `类型：${typeLabel}`, color: '555555' })]
    }),
    new Paragraph({
      children: [new TextRun({ text: `更新时间：${updatedAtStr}`, color: '555555' })]
    }),
    // 空行（分隔）
    new Paragraph({ children: [] })
  ]
}

// ─────────────────────────────────────────────
// 公共入口：currentDocument → Blob 下载
// ─────────────────────────────────────────────

/**
 * 将 Tiptap contentJson 转为 Paragraph[]。
 * 输入约束：node.type === 'doc'，否则按"未知节点"递归处理。
 */
export function tiptapJsonToParagraphs(contentJson) {
  if (!contentJson || typeof contentJson !== 'object') return []
  if (contentJson.type === 'doc' && Array.isArray(contentJson.content)) {
    const out = []
    for (const child of contentJson.content) {
      out.push(...blockNodeToParagraphs(child))
    }
    return out
  }
  // 兜底：直接当未知块处理
  return blockNodeToParagraphs(contentJson)
}

/**
 * 从一份 Document 草稿生成 .docx Blob。
 *
 * @param {Object} doc 文档对象（KnowledgeBase.vue 的 Document 数据结构）
 * @param {string} typeLabel 文档类型的中文 label（如 '简历草稿'）
 * @param {string} updatedAtStr 已格式化的更新时间字符串
 * @returns {Promise<Blob>}
 */
export async function buildDocxBlobFromDocument(doc, typeLabel, updatedAtStr) {
  if (!doc) throw new Error('Document is null')

  const headerParas = buildHeaderParagraphs(doc, typeLabel, updatedAtStr)
  const bodyParas = tiptapJsonToParagraphs(doc.contentJson)

  // 内容为空时，至少给一个空段落，让 Word 不报"文档已损坏"
  const allParas = headerParas.concat(bodyParas.length > 0 ? bodyParas : [new Paragraph({ children: [] })])

  const document = new Document({
    creator: 'Document Workbench',
    title: doc.title || '未命名文档',
    description: typeLabel || '',
    // 有序列表共享同一个 numbering 引用
    numbering: {
      config: [
        {
          reference: 'docx-export-ordered',
          levels: [
            {
              level: 0,
              format: 'decimal',
              text: '%1.',
              alignment: AlignmentType.START,
              style: {
                paragraph: { indent: { left: 720, hanging: 260 } }
              }
            }
          ]
        }
      ]
    },
    styles: {
      default: {
        document: {
          run: { font: 'Microsoft YaHei', size: 22 } // 11pt（22 half-points）
        }
      }
    },
    sections: [
      {
        properties: {},
        children: allParas
      }
    ]
  })

  return await Packer.toBlob(document)
}

/**
 * 触发浏览器下载（与 KnowledgeBase.vue 复用同样的 Blob → <a download> 流程）。
 */
export function downloadBlobAs(blob, filename) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.rel = 'noopener'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

/**
 * 顶层入口：从一份 Document 草稿生成 .docx 并触发下载。
 * 失败时抛出异常，由调用方决定 toast 文案。
 */
export async function exportDocxFromDocument(doc, typeLabel, updatedAtStr) {
  const blob = await buildDocxBlobFromDocument(doc, typeLabel, updatedAtStr)
  const filename = sanitizeDocxFilename(doc?.title) + '.docx'
  downloadBlobAs(blob, filename)
}
