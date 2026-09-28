/**
 * 统一日志工具。
 *
 * 生产环境只输出 warn / error，避免把调试信息（含请求地址等）泄露到用户控制台。
 */

import { IS_DEV } from '@/config'

const PREFIX = '[hello-travel]'

export const logger = {
  debug(...args: unknown[]): void {
    if (IS_DEV) console.debug(PREFIX, ...args)
  },
  info(...args: unknown[]): void {
    if (IS_DEV) console.info(PREFIX, ...args)
  },
  warn(...args: unknown[]): void {
    console.warn(PREFIX, ...args)
  },
  error(...args: unknown[]): void {
    console.error(PREFIX, ...args)
  }
}

export default logger
