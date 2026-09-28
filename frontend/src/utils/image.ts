/**
 * 图片相关工具。
 */

const FALLBACK_COLORS = [
  { start: '#0f766e', end: '#2563eb' },
  { start: '#f97316', end: '#0f766e' },
  { start: '#1d4ed8', end: '#7c3aed' },
  { start: '#334155', end: '#0f766e' }
]

/** UTF-8 安全的 base64 编码（替代已废弃的 unescape + btoa 组合）。 */
function toBase64(input: string): string {
  const bytes = new TextEncoder().encode(input)
  let binary = ''
  bytes.forEach(byte => {
    binary += String.fromCharCode(byte)
  })
  return btoa(binary)
}

/**
 * 生成一张带渐变背景与景点名的占位图（SVG DataURL）。
 *
 * 当 Unsplash 未配置或请求失败时使用，避免出现破图。
 */
export function buildFallbackImage(name: string, index = 0): string {
  const { start, end } = FALLBACK_COLORS[index % FALLBACK_COLORS.length]
  const safeName = (name || '旅行计划').replace(/[<>&"']/g, '')
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="800" height="520">
    <defs><linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="${start}"/><stop offset="100%" stop-color="${end}"/>
    </linearGradient></defs>
    <rect width="800" height="520" fill="url(#g)"/>
    <circle cx="650" cy="120" r="110" fill="rgba(255,255,255,0.16)"/>
    <text x="56" y="270" font-family="Arial, sans-serif" font-size="48" font-weight="700" fill="white">${safeName}</text>
  </svg>`
  return `data:image/svg+xml;base64,${toBase64(svg)}`
}

/** `<img>` 加载失败时替换为占位图。 */
export function handleImageError(event: Event): void {
  const img = event.target as HTMLImageElement
  if (!img || img.dataset.fallbackApplied === '1') return
  img.dataset.fallbackApplied = '1'
  img.src = buildFallbackImage(img.alt || '旅行计划', 0)
}
