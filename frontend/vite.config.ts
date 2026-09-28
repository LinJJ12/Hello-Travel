import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import Components from 'unplugin-vue-components/vite'
import { AntDesignVueResolver } from 'unplugin-vue-components/resolvers'
import { resolve } from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    // ant-design-vue 按需自动引入：
    // 原先 `app.use(Antd)` 会把整个组件库打进单个 chunk（约 1.4MB）。
    // 这里改用官方推荐的 unplugin-vue-components 解析器，只打包模板里真正用到的组件。
    // ant-design-vue v4 采用 CSS-in-JS，无需再按组件引入样式文件。
    Components({
      resolvers: [AntDesignVueResolver({ importStyle: false })],
      dts: 'src/components.d.ts'
    })
  ],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          vue: ['vue', 'vue-router'],
          amap: ['@amap/amap-jsapi-loader']
        }
      }
    },
    // antd 按需引入后主 chunk 已大幅缩小；jspdf / html2canvas 属按需异步加载，
    // 单独放宽阈值避免构建时产生无意义告警。
    chunkSizeWarningLimit: 500
  }
})
