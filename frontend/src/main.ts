import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import 'ant-design-vue/dist/reset.css'
import './styles/global.css'
import App from './App.vue'
import { i18n } from './i18n'

// 合并说明：这里不再 `import Antd from 'ant-design-vue'` + `app.use(Antd)`。
// 全量注册会把整个组件库打进单个 chunk（约 1.4MB）；现改由
// unplugin-vue-components 的 AntDesignVueResolver 在 vite.config.ts 中按需自动引入，
// 只打包模板里真正用到的组件。ant-design-vue v4 使用 CSS-in-JS，
// 无需再按组件引入样式文件，仅保留全局 reset.css。

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'Landing',
      // 懒加载：结果页会带上 echarts / html2canvas / swiper / 地图 SDK。
      // 首页首屏不应该为这些结果页依赖付出加载成本。
      component: () => import('./views/Landing.vue')
    },
    {
      path: '/result',
      name: 'Result',
      component: () => import('./views/Result.vue')
    }
  ]
})

const app = createApp(App)

app.use(router)
app.use(i18n)

app.mount('#app')
