/**
 * resumeDocxBuilder.js — 基于 Resume_JSON 直接构造 DOCX
 *
 * 严格满足 Requirement 9.3 / 9.4 / 9.8:
 *   - 不通过 Tiptap HTML → DOCX 直管道
 *   - 保留段落 / 列表 / 标题层级 / 字符级排版(加粗、斜体)
 *   - 失败时抛 ResumeDocxBuildError,由 ExportToolbar 捕获
 *
 * 依赖:已有 `docx` 包(见 package.json)
 */

import {
  Document,
  Packer,
  Paragraph,
  TextRun,
  HeadingLevel,
  AlignmentType,
  Tab,
  LevelFormat,
  convertInchesToTwip
} from 'docx'

export class ResumeDocxBuildError extends Error {
  constructor(message, options) {
    super(message)
    this.name = 'ResumeDocxBuildError'
    if (options && options.cause) this.cause = options.cause
  }
}

const SECTION_HEADERS = {
  experience: '工作经历',
  projects: '项目经历',
  education: '教育经历',
  skills: '技能',
  awards: '获奖',
  certificates: '证书'
}

function cellText(cell) {
  if (!cell) return ''
  if (typeof cell.value === 'string') return cell.value.trim()
  if (Array.isArray(cell.value)) return cell.value.filter(Boolean).join(', ')
  if (typeof cell.value === 'number') return String(cell.value)
  return ''
}

function cellList(cell) {
  if (!cell) return []
  if (Array.isArray(cell.value)) return cell.value.filter((v) => typeof v === 'string' && v.trim())
  if (typeof cell.value === 'string' && cell.value.trim()) return [cell.value.trim()]
  return []
}

function dateRange(item) {
  const a = cellText(item?.startDate)
  const b = cellText(item?.endDate)
  if (a && b) return `${a} — ${b}`
  if (a) return a
  if (b) return b
  return ''
}

// ─── 段落工厂 ──

function plain(text, opts = {}) {
  return new Paragraph({
    children: [new TextRun({ text, ...opts })],
    spacing: { after: 80 }
  })
}

function heading(text, level = HeadingLevel.HEADING_2) {
  return new Paragraph({
    children: [new TextRun({ text, bold: true })],
    heading: level,
    spacing: { before: 200, after: 80 }
  })
}

function namedTitle(text) {
  return new Paragraph({
    children: [new TextRun({ text, bold: true, size: 32 })],
    heading: HeadingLevel.HEADING_1,
    alignment: AlignmentType.LEFT,
    spacing: { after: 120 }
  })
}

function bulletItem(text) {
  return new Paragraph({
    children: [new TextRun({ text })],
    bullet: { level: 0 },
    spacing: { after: 60 }
  })
}

function itemHead(parts) {
  // parts: [{text, bold?}, ...]
  return new Paragraph({
    children: parts
      .filter((p) => p && p.text)
      .map((p) => new TextRun({ text: p.text, bold: !!p.bold, italics: !!p.italics })),
    spacing: { after: 60 }
  })
}

// ─── Section 构造 ──

function buildBasicsParagraphs(basics) {
  if (!basics) return []
  const out = []
  const name = cellText(basics.name)
  if (name) out.push(namedTitle(name))
  const role = cellText(basics.targetRole)
  if (role) {
    out.push(
      new Paragraph({
        children: [new TextRun({ text: role, italics: true, size: 22 })],
        spacing: { after: 60 }
      })
    )
  }
  const contactBits = ['email', 'phone', 'city', 'websiteOrRepo']
    .map((f) => cellText(basics[f]))
    .filter(Boolean)
  if (contactBits.length > 0) {
    out.push(plain(contactBits.join(' · ')))
  }
  return out
}

function buildExperienceSection(items) {
  if (!items || items.length === 0) return []
  const out = [heading(SECTION_HEADERS.experience)]
  items.forEach((item) => {
    const head = []
    if (cellText(item.title)) head.push({ text: cellText(item.title), bold: true })
    if (cellText(item.company)) head.push({ text: ` · ${cellText(item.company)}` })
    if (dateRange(item)) head.push({ text: ` · ${dateRange(item)}`, italics: true })
    if (cellText(item.location)) head.push({ text: ` · ${cellText(item.location)}` })
    if (head.length > 0) out.push(itemHead(head))
    if (cellText(item.summary)) out.push(plain(cellText(item.summary)))
    cellList(item.highlights).forEach((h) => out.push(bulletItem(h)))
  })
  return out
}

function buildProjectsSection(items) {
  if (!items || items.length === 0) return []
  const out = [heading(SECTION_HEADERS.projects)]
  items.forEach((item) => {
    const head = []
    if (cellText(item.name)) head.push({ text: cellText(item.name), bold: true })
    if (cellText(item.role)) head.push({ text: ` · ${cellText(item.role)}` })
    if (dateRange(item)) head.push({ text: ` · ${dateRange(item)}`, italics: true })
    if (cellText(item.link)) head.push({ text: ` · ${cellText(item.link)}` })
    if (head.length > 0) out.push(itemHead(head))
    const stack = cellList(item.stack)
    if (stack.length > 0) out.push(plain(`技术栈:${stack.join(', ')}`))
    if (cellText(item.summary)) out.push(plain(cellText(item.summary)))
    cellList(item.highlights).forEach((h) => out.push(bulletItem(h)))
  })
  return out
}

function buildEducationSection(items) {
  if (!items || items.length === 0) return []
  const out = [heading(SECTION_HEADERS.education)]
  items.forEach((item) => {
    const head = []
    if (cellText(item.school)) head.push({ text: cellText(item.school), bold: true })
    if (cellText(item.degree)) head.push({ text: ` · ${cellText(item.degree)}` })
    if (cellText(item.major)) head.push({ text: ` · ${cellText(item.major)}` })
    if (dateRange(item)) head.push({ text: ` · ${dateRange(item)}`, italics: true })
    if (cellText(item.gpa)) head.push({ text: ` · GPA ${cellText(item.gpa)}` })
    if (head.length > 0) out.push(itemHead(head))
    cellList(item.highlights).forEach((h) => out.push(bulletItem(h)))
  })
  return out
}

function buildSkillsSection(groups) {
  if (!groups || groups.length === 0) return []
  const out = [heading(SECTION_HEADERS.skills)]
  groups.forEach((g) => {
    if (!g) return
    const items = (g.items || []).filter((s) => s && (s.name || '').trim())
    if (!g.category && items.length === 0) return
    const lineParts = []
    if (g.category) lineParts.push({ text: `${g.category}:`, bold: true })
    if (items.length > 0) lineParts.push({ text: items.map((s) => s.name).join(', ') })
    if (lineParts.length > 0) out.push(itemHead(lineParts))
  })
  return out
}

function buildAwardsSection(items) {
  if (!items || items.length === 0) return []
  const out = [heading(SECTION_HEADERS.awards)]
  items.forEach((item) => {
    const parts = []
    if (cellText(item.name)) parts.push({ text: cellText(item.name), bold: true })
    if (cellText(item.issuer)) parts.push({ text: ` · ${cellText(item.issuer)}` })
    if (cellText(item.date)) parts.push({ text: ` · ${cellText(item.date)}`, italics: true })
    if (cellText(item.summary)) parts.push({ text: ` · ${cellText(item.summary)}` })
    if (parts.length > 0) out.push(itemHead(parts))
  })
  return out
}

function buildCertificatesSection(items) {
  if (!items || items.length === 0) return []
  const out = [heading(SECTION_HEADERS.certificates)]
  items.forEach((item) => {
    const parts = []
    if (cellText(item.name)) parts.push({ text: cellText(item.name), bold: true })
    if (cellText(item.issuer)) parts.push({ text: ` · ${cellText(item.issuer)}` })
    if (cellText(item.issueDate)) parts.push({ text: ` · ${cellText(item.issueDate)}`, italics: true })
    if (cellText(item.expireDate)) parts.push({ text: ` ~ ${cellText(item.expireDate)}` })
    if (cellText(item.credentialId)) parts.push({ text: ` · 编号 ${cellText(item.credentialId)}` })
    if (parts.length > 0) out.push(itemHead(parts))
  })
  return out
}

function filterNonEmpty(items, fields) {
  return (items || []).filter((item) => {
    if (!item) return false
    for (const f of fields) {
      if (cellText(item[f])) return true
      if (cellList(item[f]).length > 0) return true
    }
    return false
  })
}

/**
 * 把 Resume_JSON 构造为 DOCX Document 对象。
 *
 * 模板差异:
 *   - ats_single_column:experience → projects → education → skills → awards → certificates
 *   - tech_two_column:左栏(basics + skills + certificates)+ 右栏(experience + projects + education + awards)
 *     由于 docx 包对双栏布局支持有限,MVP 阶段两个模板都输出"线性"结构,但工作 / 项目顺序与模板一致。
 */
export async function buildDocxBlob(resumeJson, templateId = 'ats_single_column') {
  if (!resumeJson || typeof resumeJson !== 'object') {
    throw new ResumeDocxBuildError('Resume_JSON 不合法')
  }

  try {
    const basicsParas = buildBasicsParagraphs(resumeJson.basics)
    const expItems = filterNonEmpty(resumeJson.experience?.items, [
      'company',
      'title',
      'startDate',
      'endDate',
      'location',
      'summary',
      'highlights'
    ])
    const projItems = filterNonEmpty(resumeJson.projects?.items, [
      'name',
      'role',
      'stack',
      'startDate',
      'endDate',
      'summary',
      'highlights',
      'link'
    ])
    const eduItems = filterNonEmpty(resumeJson.education?.items, [
      'school',
      'degree',
      'major',
      'startDate',
      'endDate',
      'gpa',
      'highlights'
    ])
    const skillGroups = (resumeJson.skills?.items || []).filter((g) => {
      if (!g) return false
      const cat = (g.category || '').trim()
      const subs = (g.items || []).filter((s) => s && (s.name || '').trim())
      return cat || subs.length > 0
    })
    const awardItems = filterNonEmpty(resumeJson.awards?.items, ['name', 'issuer', 'date', 'summary'])
    const certItems = filterNonEmpty(resumeJson.certificates?.items, [
      'name',
      'issuer',
      'issueDate',
      'expireDate',
      'credentialId'
    ])

    let body
    if (templateId === 'tech_two_column') {
      body = [
        ...basicsParas,
        ...buildSkillsSection(skillGroups),
        ...buildExperienceSection(expItems),
        ...buildProjectsSection(projItems),
        ...buildEducationSection(eduItems),
        ...buildAwardsSection(awardItems),
        ...buildCertificatesSection(certItems)
      ]
    } else {
      body = [
        ...basicsParas,
        ...buildExperienceSection(expItems),
        ...buildProjectsSection(projItems),
        ...buildEducationSection(eduItems),
        ...buildSkillsSection(skillGroups),
        ...buildAwardsSection(awardItems),
        ...buildCertificatesSection(certItems)
      ]
    }

    if (body.length === 0) {
      body.push(plain('(空简历)'))
    }

    const doc = new Document({
      creator: 'AI 职业领航员',
      title: cellText(resumeJson?.basics?.name) || '简历',
      sections: [
        {
          properties: {
            page: {
              margin: {
                top: convertInchesToTwip(0.7),
                right: convertInchesToTwip(0.7),
                bottom: convertInchesToTwip(0.7),
                left: convertInchesToTwip(0.7)
              }
            }
          },
          children: body
        }
      ]
    })

    const blob = await Packer.toBlob(doc)
    return blob
  } catch (err) {
    if (err instanceof ResumeDocxBuildError) throw err
    throw new ResumeDocxBuildError('docx 写入失败', { cause: err })
  }
}
