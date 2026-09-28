/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** 高德地图 JS API Key（Web 端） */
  readonly VITE_AMAP_WEB_JS_KEY?: string
  /** 兼容旧命名 */
  readonly VITE_AMAP_JS_KEY?: string
  /** 后端 API 基地址 */
  readonly VITE_API_BASE_URL?: string
  readonly DEV: boolean
  readonly PROD: boolean
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}
