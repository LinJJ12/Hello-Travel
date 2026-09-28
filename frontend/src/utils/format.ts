/**
 * 通用格式化工具。
 */

/** 把 ISO 时间字符串格式化为 `YYYY-MM-DD HH:mm`。 */
export function formatDateTime(value?: string | null): string {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '-'
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}

/** 把分钟数格式化为「x小时y分钟」。 */
export function formatDuration(minutes?: number | null): string {
  const total = Math.max(0, Math.round(minutes ?? 0))
  if (total < 60) return `${total}分钟`
  const hours = Math.floor(total / 60)
  const rest = total % 60
  return rest === 0 ? `${hours}小时` : `${hours}小时${rest}分钟`
}

/** 把米数格式化为「x.x 公里」或「x 米」。 */
export function formatDistance(meters?: number | null): string {
  const value = Math.max(0, meters ?? 0)
  if (value < 1000) return `${Math.round(value)} 米`
  return `${(value / 1000).toFixed(1)} 公里`
}

/** 金额格式化：`¥1,200`。 */
export function formatCurrency(amount?: number | null): string {
  const value = Number(amount ?? 0)
  return `¥${value.toLocaleString('zh-CN')}`
}
