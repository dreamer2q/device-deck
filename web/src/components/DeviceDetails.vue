<script setup>
import { computed, onMounted, onBeforeUnmount, ref } from 'vue'
import { platformLabel } from '../lib/platform.js'
import { isVirtual, resourceStatus, resourceCanOpen } from '../lib/deviceResources.js'
import { canStart, canStop, vmLifecycle } from '../lib/vmLifecycle.js'
const props = defineProps({ device: { type: Object, required: true }, busy: { type: String, default: '' } })
const emit = defineEmits(['close', 'edit', 'maintenance', 'start', 'stop', 'refresh'])
const dialog = ref(null)
const tab = ref('overview')
const environment = computed(() => props.device.host?.ios_environment)
const checks = computed(() => (environment.value?.checks || []).filter(c => props.device.platform === 'ios' ? c.id !== 'simulator_runtime' : c.id !== 'device_signing'))
const life = computed(() => props.device.vm ? vmLifecycle(props.device.vm) : null)
let previousFocus
onMounted(() => { previousFocus = document.activeElement; dialog.value.showModal() })
onBeforeUnmount(() => previousFocus?.focus?.())
function timeLabel(value) { return value ? new Date(value).toLocaleString() : '尚无检查记录' }
</script>

<template>
  <dialog ref="dialog" class="details" @close="emit('close')" @click="e => { if (e.target === dialog) dialog.close() }">
    <header><div><span class="eyebrow">{{ platformLabel(device) }} · {{ isVirtual(device) ? '模拟器' : '真机' }}</span><h2>{{ device.alias || device.model }}</h2></div><button aria-label="关闭设备详情" @click="dialog.close()">×</button></header>
    <nav aria-label="设备详情"><button :class="{ active: tab === 'overview' }" @click="tab = 'overview'">概况</button><button :class="{ active: tab === 'diagnostics' }" @click="tab = 'diagnostics'">环境与诊断</button></nav>
    <section v-if="tab === 'overview'">
      <div class="status-box" :class="resourceStatus(device).cls"><strong>{{ resourceStatus(device).label }}</strong><p>{{ resourceStatus(device).hint || '可以打开工作台查看画面，并按需取得控制权。' }}</p></div>
      <dl><dt>型号 / 系统</dt><dd>{{ device.model }} · {{ device.os_version || '待检测' }}</dd><dt>运行位置</dt><dd>{{ device.agent_name_current }}</dd><dt>当前占用</dt><dd>{{ device.lock ? device.lock.holder || '占用者未知' : '无占用' }}</dd><dt>控制检查</dt><dd>{{ device.extra?.readiness?.ready === true ? '已就绪' : '未确认可控制' }}</dd><dt>画面检查</dt><dd>打开工作台后独立检查</dd></dl>
      <p v-if="life?.error" class="failure">上次操作：{{ life.error }}</p>
      <details><summary>设备标识</summary><p class="mono">{{ device.serial || device.vm?.id }}</p><p v-if="device.vm">实例：{{ device.vm.id }}（启停保留数据）</p></details>
      <div class="tools"><button @click="emit('edit', device)">修改名称</button><button v-if="device.serial && device.live" :disabled="!!device.lock || !!busy" @click="emit('maintenance', device)">{{ device.extra?.mirror_paused ? '恢复镜像' : '暂停镜像' }}</button><button v-if="device.vm && canStop(device.vm)" :disabled="!!device.lock || !!busy" @click="emit('stop', device)">停止模拟器</button></div>
      <div class="related"><RouterLink to="/app-distribution">应用安装与分发</RouterLink><RouterLink to="/queue">任务与操作记录</RouterLink><RouterLink v-if="device.vm" :to="{ path: '/virtual-machines', query: { platform: device.platform } }">模拟器配置</RouterLink></div>
    </section>
    <section v-else>
      <p class="help">检查只读取当前环境，不会启动、安装或重启设备服务。</p>
      <template v-if="['ios', 'ios_sim'].includes(device.platform)">
        <p class="checked">环境记录：{{ timeLabel(environment?.checked_at) }}<span v-if="environment?.xcode_version"> · {{ environment.xcode_version }}</span></p>
        <div v-for="check in checks" :key="check.id" class="check"><span class="check-icon" :class="check.status">{{ check.status === 'ok' ? '✓' : '!' }}</span><div><strong>{{ check.title }}</strong><p>{{ check.status === 'ok' ? '检查通过' : check.next_step }}</p></div></div>
        <p v-if="!checks.length" class="help">运行位置尚未上报环境检查，请等待 Agent 重连后刷新；不能据此判断 WDA 已就绪。</p>
        <div class="check"><span class="check-icon" :class="device.extra?.readiness?.ready ? 'ok' : 'blocked'">{{ device.extra?.readiness?.ready ? '✓' : '!' }}</span><div><strong>当前设备控制通道</strong><p>{{ device.extra?.readiness?.hint || device.extra?.wda_stage?.hint || (device.extra?.readiness?.ready ? 'WDA 探活通过' : '尚未确认 WDA 可操作；工具链通过不代表设备控制已通过。') }}</p></div></div>
        <p v-if="device.extra?.wda_stage?.title" class="failure">{{ device.extra.wda_stage.title }}</p>
        <p class="help">真机需完成配对、开发者模式与签名；模拟器不需要真机开发证书。</p>
      </template>
      <p v-else class="help">{{ device.extra?.readiness?.hint || device.extra?.reason || '控制状态来自设备探活；画面解码与输入诊断位于工作台。' }}</p>
      <button @click="emit('refresh')">刷新已上报状态</button>
    </section>
    <footer><button @click="dialog.close()">关闭</button><RouterLink v-if="resourceCanOpen(device)" class="primary" :to="`/device/${encodeURIComponent(device.serial)}`">{{ device.lock ? '查看工作台' : '打开工作台' }}</RouterLink><button v-else-if="device.vm && canStart(device.vm)" class="primary" :disabled="!!busy" @click="emit('start', device)">启动模拟器</button></footer>
  </dialog>
</template>

<style scoped>
.details { margin: 0 0 0 auto; padding: 0; width: min(490px,100vw); max-width: 100vw; height: 100dvh; max-height: 100dvh; border: 0; border-left: 1px solid #dce3ed; color: #26364a; background: #fff; box-shadow: -8px 0 35px #17283b17; }.details::backdrop { background: #17283b30; }header { display: flex; justify-content: space-between; align-items: center; padding: 23px 24px 17px; }h2 { font-size: 17px; margin: 6px 0 0; overflow-wrap: anywhere; }.eyebrow,.checked { font-size: 11px; color: #7c899a; }button { cursor: pointer; border: 1px solid #dce3ec; background: #fff; color: #52657c; border-radius: 4px; padding: 7px 10px; font: inherit; font-size: 12px; }header button { border: 0; font-size: 23px; }nav { display: flex; border-bottom: 1px solid #e4eaf2; padding: 0 24px; gap: 15px; }nav button { border: 0; border-radius: 0; padding: 10px 0; }nav .active { border-bottom: 2px solid #347dc6; color: #2667a8; }section { padding: 20px 24px; }p { line-height: 1.65; font-size: 12px; margin: 7px 0; }.status-box { padding: 12px; border-radius: 5px; background: #f5f8fc; }.status-box strong { font-size: 13px; }.status-box p { margin-bottom: 0; color: #708197; }.ok { color: #15805b; }.warn,.blocked,.failure { color: #a06a15; }dl { display: grid; grid-template-columns: 94px 1fr; gap: 14px 10px; font-size: 12px; margin: 23px 0; }dt { color: #8290a0; }dd { margin: 0; overflow-wrap: anywhere; }summary { color: #798697; font-size: 11px; cursor: pointer; }.mono { font-family: monospace; overflow-wrap: anywhere; }.tools { display: flex; gap: 7px; flex-wrap: wrap; margin-top: 24px; }.related { display: flex; gap: 15px; flex-wrap: wrap; margin-top: 20px; font-size: 11px; color: #467db4; }footer { display: flex; justify-content: flex-end; padding: 15px 24px; gap: 8px; border-top: 1px solid #e8edf4; }.primary { background: #276db6; color: #fff; padding: 7px 12px; text-decoration: none; border: 0; border-radius: 4px; font-size: 12px; }.help { color: #7e8b9c; }.check { display: flex; gap: 10px; border-bottom: 1px solid #edf1f6; padding: 14px 0; }.check strong { font-size: 12px; }.check p { margin: 4px 0 0; color: #77869a; }.check-icon { font-weight: 700; }.failure { overflow-wrap: anywhere; }
</style>
