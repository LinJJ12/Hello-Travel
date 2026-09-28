import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import Components from 'unplugin-vue-components/vite'
import { AntDesignVueResolver } from 'unplugin-vue-components/resolvers'
import { resolve } from 'path'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  // 以空前缀加载全部变量，兼容 Docker/CI 直接注入的 VITE_* 环境变量。
  const env = loadEnv(mode, process.cwd(), '')
  const amapSecurityJsCode = env.VITE_AMAP_SECURITY_JS_CODE || ''

  return {
    plugins: [
      vue(),
      // ant-design-vue 按需自动引入：
      // 原先 `app.use(Antd)` 会把整个组件库打进单个 chunk（约 1.4MB）。
      // 这里改用官方推荐的 unplugin-vue-components 解析器，只打包模板里真正用到的组件。
      // ant-design-vue v4 采用 CSS-in-JS，无需再按组件引入样式文件。
      // 注意：`message` / `Modal` 等命令式 API 不走模板解析，需在源码中显式 import。
      Components({
        resolvers: [AntDesignVueResolver({ importStyle: false })],
        dts: 'src/components.d.ts'
      }),
      {
        // 使用普通占位符，避免触发 Vite 对 %ENV% 的内置扫描告警。
        name: 'tripstar-inject-amap-security-code',
        transformIndexHtml(html: string) {
          return html.replaceAll('__AMAP_SECURITY_JS_CODE__', amapSecurityJsCode)
        },
      },
    ],
    resolve: {
      alias: {
        '@': resolve(__dirname, 'src')
      }
    },
    build: {
      rollupOptions: {
        output: {
          manualChunks(id: string) {
            if (!id.includes('node_modules')) return
            if (id.includes('echarts') || id.includes('zrender')) return 'echarts'
            if (id.includes('html2canvas')) return 'html2canvas'
            if (id.includes('swiper')) return 'swiper'
            if (id.includes('amap-jsapi-loader') || id.includes('@googlemaps')) return 'maps'
            // 精确匹配 Vue 运行时，避免把 ant-design-vue 也卷进 vue chunk
            if (/node_modules[\\/](vue|@vue|vue-router|vue-i18n)[\\/]/.test(id)) return 'vue'
          },
        },
      },
      // antd 按需引入后业务 chunk 已明显缩小；echarts 属于结果页懒加载的重依赖，
      // 单独放宽阈值，避免构建时产生无意义告警。
      chunkSizeWarningLimit: 1000
    },
    server: {
      port: 5173,
      proxy: {
        '/api': {
          target: 'http://localhost:8000',
          changeOrigin: true
        }
      }
    }
  }
})
