<template>
  <a-layout class="app-shell">
    <a-layout-header class="app-header">
      <router-link class="brand" to="/">
        <span class="brand-mark">HT</span>
        <span class="brand-text">Hello-Travel Agent</span>
      </router-link>

      <nav class="top-nav">
        <router-link to="/">规划</router-link>
        <router-link to="/explore">互动地图</router-link>
        <router-link to="/history">历史</router-link>
      </nav>
    </a-layout-header>

    <a-layout-content class="app-content">
      <router-view />
    </a-layout-content>

    <a-layout-footer class="app-footer">
      Hello-Travel Agent 智能旅行规划工作台
    </a-layout-footer>
  </a-layout>
</template>

<script setup lang="ts">
</script>

<style>
:root {
  color: #1f2937;
  background: #edf3f6;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial,
    'Noto Sans SC', 'Noto Sans', sans-serif;
  font-synthesis: none;
  text-rendering: optimizeLegibility;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  min-width: 320px;
  background: #edf3f6;
}

a {
  color: inherit;
  text-decoration: none;
}

#app {
  min-height: 100vh;
}

.app-shell {
  min-height: 100vh;
  background: linear-gradient(180deg, #f8fafc 0%, #eef3f6 54%, #f7f9fb 100%);
}

.app-header {
  position: sticky;
  top: 0;
  z-index: 20;
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 64px;
  padding: 0 clamp(16px, 4vw, 48px);
  background: rgba(255, 255, 255, 0.92);
  border-bottom: 1px solid #dbe3ea;
  backdrop-filter: blur(14px);
}

.brand {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  color: #111827;
  font-weight: 700;
}

.brand-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: 8px;
  background: #0f766e;
  color: #ffffff;
  font-size: 12px;
  letter-spacing: 0;
}

.brand-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 17px;
}

.top-nav {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px;
  border: 1px solid #dbe3ea;
  border-radius: 8px;
  background: #ffffff;
}

.top-nav a {
  min-width: 64px;
  padding: 7px 14px;
  border-radius: 6px;
  color: #64748b;
  font-size: 14px;
  font-weight: 600;
  line-height: 1;
  text-align: center;
}

.top-nav a.router-link-active {
  background: #0f766e;
  color: #ffffff;
}

.app-content {
  min-height: calc(100vh - 112px);
}

.app-footer {
  padding: 18px 16px;
  background: transparent;
  color: #64748b;
  font-size: 13px;
  text-align: center;
}

@media (max-width: 640px) {
  .app-header {
    height: 58px;
  }

  .brand-text {
    max-width: 170px;
    font-size: 15px;
  }

  .top-nav a {
    min-width: 48px;
    padding-inline: 10px;
  }
}
</style>
