/**
 * 导出工具：图片 / PDF / 文本下载。
 *
 * 原实现里 html2canvas 的调用配置在 exportAsImage 与 exportAsPDF 中重复了两次，
 * 这里抽成共用函数。
 */

const HTML2CANVAS_OPTIONS = {
  backgroundColor: '#f6f8fb',
  scale: 2,
  useCORS: true,
  allowTaint: true
} as const

/** A4 纸张尺寸（毫米） */
const A4_WIDTH_MM = 210
const A4_HEIGHT_MM = 297

function resolveElement(selector: string): HTMLElement {
  const element = document.querySelector(selector) as HTMLElement | null
  if (!element) throw new Error('未找到待导出的内容元素')
  return element
}

async function renderCanvas(selector: string): Promise<HTMLCanvasElement> {
  const { default: html2canvas } = await import('html2canvas')
  return html2canvas(resolveElement(selector), HTML2CANVAS_OPTIONS)
}

/** 把指定元素导出为 PNG 图片并触发下载。 */
export async function exportElementAsImage(selector: string, filename: string): Promise<void> {
  const canvas = await renderCanvas(selector)
  const link = document.createElement('a')
  link.download = filename
  link.href = canvas.toDataURL('image/png')
  link.click()
}

/** 把指定元素导出为多页 A4 PDF 并触发下载。 */
export async function exportElementAsPdf(selector: string, filename: string): Promise<void> {
  const [{ default: jsPDF }, canvas] = await Promise.all([import('jspdf'), renderCanvas(selector)])
  const imgData = canvas.toDataURL('image/png')
  const pdf = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' })
  const imgHeight = (canvas.height * A4_WIDTH_MM) / canvas.width

  let heightLeft = imgHeight
  let position = 0
  pdf.addImage(imgData, 'PNG', 0, position, A4_WIDTH_MM, imgHeight)
  heightLeft -= A4_HEIGHT_MM

  while (heightLeft > 0) {
    position = heightLeft - imgHeight
    pdf.addPage()
    pdf.addImage(imgData, 'PNG', 0, position, A4_WIDTH_MM, imgHeight)
    heightLeft -= A4_HEIGHT_MM
  }

  pdf.save(filename)
}

/** 下载纯文本 / Markdown 文件。 */
export function downloadTextFile(content: string, filename: string, type = 'text/markdown;charset=utf-8'): void {
  const blob = new Blob([content], { type })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}

/** 生成带时间戳的导出文件名。 */
export function exportFilename(prefix: string, extension: string, city?: string): string {
  const stamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-')
  const cityPart = city ? `_${city}` : ''
  return `${prefix}${cityPart}_${stamp}.${extension}`
}
