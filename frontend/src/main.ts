import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import 'ant-design-vue/dist/reset.css'
import App from './App.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'Home',
      component: () => import('./views/Home.vue')
    },
    {
      path: '/result',
      name: 'Result',
      component: () => import('./views/Result.vue')
    },
    {
      path: '/explore',
      name: 'Explore',
      component: () => import('./views/Explore.vue')
    },
    {
      path: '/history',
      name: 'History',
      component: () => import('./views/History.vue')
    }
  ]
})

const app = createApp(App)

// 说明：不再全量 `app.use(Antd)`。
// ant-design-vue 组件由 unplugin-vue-components 按需自动注册（见 vite.config.ts），
// 命令式 API（message 等）在各视图内按需 import，因此这里无需注册全局插件。
app.use(router)

app.mount('#app')
