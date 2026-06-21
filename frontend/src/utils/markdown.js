export function escapeHtml(value = '') {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;')
}

export function roleLabel(role) {
  if (role === 'admin') return '管理员'
  return role === 'teacher' ? '教师' : '学生'
}

export function displayCoursewareTitle(value = '') {
  const text = String(value || '').trim()
  if (!text) return ''
  return text
    .replace(/^[0-9a-f]{12,}_/i, '')
    .replace(/^\d+[._-]+/, '')
    .trim()
}

export function truncateText(text = '', limit = 120) {
  const value = String(text || '').trim()
  if (value.length <= limit) return value
  return `${value.slice(0, limit).trimEnd()}...`
}

export function formatCount(value) {
  return value == null ? '-' : String(value)
}

export function joinRequestLabel(status) {
  if (status === 'pending') return '待审核'
  if (status === 'rejected') return '已拒绝'
  if (status === 'approved') return '已通过'
  return '可申请'
}

function renderInlineRichText(text = '') {
  return escapeHtml(text)
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\*([^*\n]+)\*/g, '<em>$1</em>')
}

export function renderRichText(content = '') {
  const lines = String(content).replace(/\r\n?/g, '\n').split('\n')
  const blocks = []
  let paragraph = []
  let listItems = []
  let listTag = ''

  const flushParagraph = () => {
    if (!paragraph.length) return
    blocks.push(`<p>${renderInlineRichText(paragraph.join(' '))}</p>`)
    paragraph = []
  }

  const flushList = () => {
    if (!listItems.length || !listTag) return
    blocks.push(
      `<${listTag}>${listItems.map((item) => `<li>${renderInlineRichText(item)}</li>`).join('')}</${listTag}>`
    )
    listItems = []
    listTag = ''
  }

  lines.forEach((line) => {
    const trimmed = line.trim()
    if (!trimmed) {
      flushParagraph()
      flushList()
      return
    }

    const headingMatch = trimmed.match(/^(#{1,3})\s+(.*)$/)
    if (headingMatch) {
      flushParagraph()
      flushList()
      const level = Math.min(5, 2 + headingMatch[1].length)
      blocks.push(`<h${level}>${renderInlineRichText(headingMatch[2])}</h${level}>`)
      return
    }

    const ulMatch = trimmed.match(/^[-*]\s+(.*)$/)
    if (ulMatch) {
      flushParagraph()
      if (listTag && listTag !== 'ul') flushList()
      listTag = 'ul'
      listItems.push(ulMatch[1])
      return
    }

    const olMatch = trimmed.match(/^\d+\.\s+(.*)$/)
    if (olMatch) {
      flushParagraph()
      if (listTag && listTag !== 'ol') flushList()
      listTag = 'ol'
      listItems.push(olMatch[1])
      return
    }

    paragraph.push(trimmed)
  })

  flushParagraph()
  flushList()

  return blocks.join('') || `<p>${renderInlineRichText(content)}</p>`
}
