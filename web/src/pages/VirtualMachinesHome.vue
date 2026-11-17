<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import HarmonyVirtualMachines from './HarmonyVirtualMachines.vue'
import IosSimVirtualMachines from './IosSimVirtualMachines.vue'
import VirtualMachines from './VirtualMachines.vue'

const route = useRoute()
const router = useRouter()
const platform = computed({
  get: () => ['android', 'harmony', 'ios_sim'].includes(route.query.platform) ? route.query.platform : 'android',
  set: value => router.replace({ query: { ...route.query, platform: value } }),
})
const androidPage = ref(null)
const harmonyPage = ref(null)
const iosSimPage = ref(null)
const refreshing = ref(false)

const activePage = computed(() => ({
  android: androidPage.value,
  harmony: harmonyPage.value,
  ios_sim: iosSimPage.value,
}[platform.value]))

async function refreshActive() {
  refreshing.value = true
  try {
    await activePage.value?.refresh?.()
  } finally {
    refreshing.value = false
  }
}
</script>

<template>
  <section class="vm-home">
    <nav class="platform-tabs" aria-label="虚拟机平台">
      <div class="tab-buttons">
        <button
          type="button"
          :class="{ active: platform === 'android' }"
          @click="platform = 'android'"
        >
          Android 虚拟机
        </button>
        <button
          type="button"
          :class="{ active: platform === 'harmony' }"
          @click="platform = 'harmony'"
        >
          鸿蒙虚拟机
        </button>
        <button
          type="button"
          :class="{ active: platform === 'ios_sim' }"
          @click="platform = 'ios_sim'"
        >
          iOS 模拟器
        </button>
      </div>
      <button type="button" class="refresh" :disabled="refreshing" @click="refreshActive">
        {{ refreshing ? '刷新中…' : '刷新' }}
      </button>
    </nav>
    <!-- Only the active platform is mounted: hidden pages must not probe/poll. -->
    <VirtualMachines v-if="platform === 'android'" ref="androidPage" />
    <HarmonyVirtualMachines v-if="platform === 'harmony'" ref="harmonyPage" />
    <IosSimVirtualMachines v-if="platform === 'ios_sim'" ref="iosSimPage" />
  </section>
</template>

<style scoped>
.vm-home {
  min-width: 0;
}
.platform-tabs {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 22px 0;
  border-bottom: 1px solid #e5e7eb;
  background: #fff;
}
.tab-buttons {
  display: flex;
  gap: 4px;
}
.platform-tabs button {
  appearance: none;
  border: 0;
  border-bottom: 2px solid transparent;
  background: transparent;
  color: #64748b;
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
  padding: 10px 16px;
}
.platform-tabs button.active {
  border-bottom-color: #2563eb;
  color: #1d4ed8;
}
.platform-tabs .refresh {
  border: 1px solid #d1d5db;
  border-radius: 6px;
  margin-bottom: 8px;
  padding: 7px 12px;
}
.platform-tabs .refresh:disabled {
  cursor: not-allowed;
  opacity: .55;
}
</style>
