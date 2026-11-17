<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterLink, RouterView } from 'vue-router'
import { api } from './lib/api.js'

const version = ref(null)
const infraDemo = import.meta.env.VITE_INFRA_DEMO === 'true'
const healthErr = ref(null)
let healthTimer = null

// 顶栏 badge：成功 → 显示版本号，失败 → 显示"后端不可达"。
// 以前只在 onMounted 拉一次，首次失败后即使后端再起来也不会自愈。
// 现在每 5s 轮询一次；任何一次成功都清空错误，失败才重置 badge。
async function pollHealth() {
  try {
    const h = await api.health()
    version.value = h.version
    healthErr.value = null
  } catch (e) {
    version.value = null
    healthErr.value = String(e)
  }
}

onMounted(() => {
  pollHealth()
  healthTimer = setInterval(pollHealth, 5000)
})

onBeforeUnmount(() => {
  if (healthTimer) clearInterval(healthTimer)
})
</script>

<template>
  <div class="shell">
    <header class="top">
      <RouterLink to="/" class="brand">
        <span class="logo">◎</span>
        <span class="name">DeviceDeck</span><span class="edition">MVP</span>
      </RouterLink>
      <nav aria-label="主导航">
        <RouterLink to="/" class="tab" active-class="on" exact>设备</RouterLink>
        <RouterLink to="/queue" class="tab" active-class="on">任务</RouterLink>
        <details class="more"><summary class="tab">工具与设置</summary><div class="more-menu" @click="e => { if (e.target.closest('a')) e.currentTarget.parentElement.open = false }">
          <RouterLink to="/app-distribution">应用分发</RouterLink>
          <RouterLink to="/virtual-machines">模拟器管理</RouterLink>
          <RouterLink to="/device-config">设备设置</RouterLink>
          <RouterLink to="/analytics">任务统计</RouterLink>
        </div></details>
      </nav>
      <div class="meta">
        <span v-if="infraDemo">设备管理测试 · AI 未启用</span>
        <span v-if="version">v{{ version }}</span>
        <span v-else-if="healthErr" class="bad">后端不可达</span>
      </div>
    </header>
    <main>
      <RouterView />
    </main>
  </div>
</template>

<style>
:root {
  color-scheme: light;
}
html, body, #app {
  margin: 0;
  padding: 0;
  background: #f4f6f9;
  color: #1f2937;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial,
    'PingFang SC', 'Microsoft YaHei', sans-serif;
  height: 100%;
  font-size: 13px;
}
button, input, textarea, select { font-family: inherit; }
button:focus-visible, a:focus-visible { outline: 2px solid #85b7f2; outline-offset: 2px; }
* {
  box-sizing: border-box;
}
a {
  color: inherit;
}
</style>

<style scoped>
.shell {
  height: 100vh;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.top {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 0 16px;
  min-height: 42px;
  flex-shrink: 0;
  background: #fff;
  border-bottom: 1px solid #e5e7eb;
  position: sticky;
  top: 0;
  z-index: 10;
}
.brand {
  display: flex;
  align-items: center;
  gap: 6px;
  text-decoration: none;
  color: #111;
}
.logo {
  font-size: 17px;
  color: #1976d2;
}
.name {
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 0.02em;
}
.edition { font-size: 8px; letter-spacing: .06em; color: #64748b; border: 1px solid #dce3ec; border-radius: 3px; padding: 2px 4px; margin-left: 3px; }
nav {
  display: flex;
  gap: 4px;
}
.tab {
  padding: 5px 9px;
  border-radius: 4px;
  text-decoration: none;
  color: #4b5563;
  font-size: 12px;
}
.tab:hover {
  background: #f2f4f7;
}
.tab.on {
  background: #e8f1fe;
  color: #1565c0;
}
.more { position: relative; }.more summary { cursor: pointer; list-style: none; }.more-menu { position: absolute; top: 30px; left: 0; width: 150px; border: 1px solid #dce4ee; background: #fff; border-radius: 5px; padding: 5px; box-shadow: 0 5px 18px #21314a15; }.more-menu a { display: block; padding: 9px; text-decoration: none; font-size: 12px; color: #596b82; }.more-menu a:hover { background: #f0f6fd; }
.meta {
  margin-left: auto;
  color: #6b7280;
  font-size: 10px;
}
.meta .bad {
  color: #b91c1c;
}
main {
  flex: 1;
  min-height: 0;
  overflow: auto;
}
@media (max-width: 760px) {
  .top { flex-wrap: wrap; gap: 5px 12px; padding: 7px 10px; }
  nav { order: 3; width: 100%; flex-shrink: 0; white-space: nowrap; padding-bottom: 2px; }
  .tab { flex-shrink: 0; padding: 7px 9px; }
}
</style>
