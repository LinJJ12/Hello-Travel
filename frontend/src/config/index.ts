/**
 * 前端统一配置。
 *
 * 集中管理环境变量读取与默认值，避免散落在各个视图里硬编码。
 */

const env = import.meta.env

/**
 * 高德地图 JS API Key。
 *
 * 注意：代码历史上读取的是 `VITE_AMAP_WEB_JS_KEY`，而 `.env.example` 里写的是
 * `VITE_AMAP_JS_KEY`，两者不一致会导致地图加载失败。这里同时兼容两种命名。
 */
export const AMAP_JS_KEY: string = env.VITE_AMAP_WEB_JS_KEY || env.VITE_AMAP_JS_KEY || ''

/**
 * 后端 API 基地址。
 *
 * 默认留空表示使用相对路径 —— 开发环境由 Vite proxy 转发 `/api` 到后端，
 * 生产环境由 Nginx 反向代理，因此无需硬编码主机名。
 * 如果后端部署在其他域名，可通过 `VITE_API_BASE_URL` 指定绝对地址。
 */
export const API_BASE_URL: string = env.VITE_API_BASE_URL || ''

/** 高德地图默认中心（中国全域） */
export const DEFAULT_MAP_CENTER: [number, number] = [104.195397, 35.86166]

/** 高德地图默认缩放级别 */
export const DEFAULT_MAP_ZOOM = 4

/** 聚焦单个地点时的缩放级别 */
export const FOCUS_MAP_ZOOM = 15

/** 是否为开发环境 */
export const IS_DEV = Boolean(env.DEV)

/** 历史记录最多保留条数 */
export const MAX_HISTORY_ITEMS = 50
