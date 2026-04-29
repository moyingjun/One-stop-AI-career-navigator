import * as pdfjsLib from 'pdfjs-dist/build/pdf.mjs'
import pdfjsWorker from 'pdfjs-dist/build/pdf.worker.mjs?url'
import mammoth from 'mammoth/mammoth.browser.js'

pdfjsLib.GlobalWorkerOptions.workerSrc = pdfjsWorker

const API_BASE_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? 'http://127.0.0.1:8000/api'
  : '/api'

const cleanText = (raw) => {
  return raw
    .replace(/[^\u4e00-\u9fff\u3400-\u4dbfa-zA-Z0-9\s.,;:!?@#$%&*()\-_+=\[\]{}<>\/\\|"'·、，。；：！？（）【】《》—…\n\r]/g, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim()
}

const fileToBase64 = (file) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = (e) => resolve(e.target.result || '')
    reader.onerror = () => reject(new Error('文件读取失败'))
    reader.readAsDataURL(file)
  })
}

const ocrImageViaBackend = async (file) => {
  const base64 = await fileToBase64(file)

  const response = await fetch(`${API_BASE_URL}/ocr/recognize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ image_base64: base64 })
  })

  if (!response.ok) {
    const errBody = await response.json().catch(() => ({}))
    throw new Error(errBody.detail || '图片识别失败，请重试')
  }

  const data = await response.json()
  return data.extracted_text || ''
}

export const parseTxtFile = (file) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = (e) => resolve(e.target.result || '')
    reader.onerror = () => reject(new Error('TXT 文件读取失败'))
    reader.readAsText(file)
  })
}

export const parseDocxFile = async (file) => {
  const arrayBuffer = await file.arrayBuffer()
  const result = await mammoth.extractRawText({ arrayBuffer })
  return result.value || ''
}

export const parsePdfFile = async (file, onScanDetected = null) => {
  const arrayBuffer = await file.arrayBuffer()
  const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise
  const textPages = []

  for (let i = 1; i <= pdf.numPages; i++) {
    const page = await pdf.getPage(i)
    const textContent = await page.getTextContent()
    const pageText = textContent.items.map(item => item.str).join(' ')
    textPages.push(pageText)
  }

  let fullText = textPages.join('\n')

  if (fullText.trim().length < 50) {
    if (onScanDetected) onScanDetected()

    const ocrTexts = []
    for (let i = 1; i <= pdf.numPages; i++) {
      const page = await pdf.getPage(i)
      const viewport = page.getViewport({ scale: 2 })

      const canvas = document.createElement('canvas')
      canvas.width = viewport.width
      canvas.height = viewport.height
      const ctx = canvas.getContext('2d')

      await page.render({ canvasContext: ctx, viewport }).promise
      const imageData = canvas.toDataURL('image/png')

      const response = await fetch(`${API_BASE_URL}/ocr/recognize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image_base64: imageData })
      })

      if (response.ok) {
        const data = await response.json()
        ocrTexts.push(data.extracted_text || '')
      }
    }

    const ocrText = ocrTexts.join('\n')
    fullText = fullText.trim() + '\n' + ocrText.trim()
  }

  return cleanText(fullText)
}

export const parseFile = async (file, { onScanDetected } = {}) => {
  if (file.type.startsWith('image/')) {
    const text = await ocrImageViaBackend(file)
    return cleanText(text)
  }

  const ext = file.name.split('.').pop().toLowerCase()

  if (ext === 'txt') {
    return await parseTxtFile(file)
  } else if (ext === 'docx') {
    return await parseDocxFile(file)
  } else if (ext === 'pdf') {
    return await parsePdfFile(file, onScanDetected)
  }

  throw new Error('不支持的文件格式，仅支持 TXT / PDF / DOCX 或图片')
}
