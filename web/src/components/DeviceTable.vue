<script setup>
import { platformLabel } from '../lib/platform.js'
import { resourceStatus, resourceCanOpen, isVirtual } from '../lib/deviceResources.js'
import { canStart } from '../lib/vmLifecycle.js'
defineProps({ devices: { type: Array, required: true }, busy: { type: String, default: '' } })
const emit = defineEmits(['details', 'start'])
</script>

<template>
  <div class="resource-list" role="list" aria-label="设备列表">
    <div class="list-heading" aria-hidden="true"><span>设备</span><span>类型 / 系统</span><span>当前状态</span><span>操作</span></div>
    <article v-for="d in devices" :key="d.resource_id" class="resource-row" role="listitem">
      <div class="identity"><button class="name" @click="emit('details', d)">{{ d.alias || d.model || '未命名设备' }}</button><div class="secondary">{{ [d.brand, d.model].filter(Boolean).join(' ') || '待准备实例' }}</div></div>
      <div class="type"><span class="chip">{{ platformLabel(d) }} · {{ isVirtual(d) ? '模拟器' : '真机' }}</span><div class="secondary">{{ d.os_version || '系统待检测' }}</div></div>
      <div class="state"><span class="status" :class="resourceStatus(d).cls"><i />{{ resourceStatus(d).label }}</span><div v-if="resourceStatus(d).hint" class="secondary hint" :title="resourceStatus(d).hint">{{ resourceStatus(d).hint }}</div><div v-if="d.lock" class="secondary">{{ d.lock.holder || '占用者未知' }}</div></div>
      <div class="actions">
        <button v-if="d.lock" class="primary" @click="emit('details', d)">占用详情</button>
        <RouterLink v-else-if="resourceCanOpen(d)" class="primary" :to="`/device/${encodeURIComponent(d.serial)}`">打开</RouterLink>
        <button v-else-if="d.vm && canStart(d.vm)" class="primary" :disabled="!!busy" @click="emit('start', d)">{{ busy === d.resource_id ? '提交中…' : '启动' }}</button>
        <button v-else class="primary" @click="emit('details', d)">检查状态</button>
        <button class="detail" @click="emit('details', d)">详情</button>
      </div>
    </article>
  </div>
</template>

<style scoped>
.resource-list { border: 1px solid #dfe5ed; border-radius: 7px; overflow: hidden; background: #fff; }
.list-heading,.resource-row { display: grid; grid-template-columns: minmax(180px,1.1fr) minmax(120px,.7fr) minmax(180px,1.2fr) 130px; align-items: center; gap: 16px; padding: 12px 16px; }
.list-heading { padding-top: 8px; padding-bottom: 8px; color: #748093; background: #f8fafc; font-size: 11px; }
.list-heading span:last-child { text-align: right; }
.resource-row + .resource-row { border-top: 1px solid #edf0f4; }.resource-row:hover { background: #fafcff; }
.resource-row > div { min-width: 0; }.name { border: 0; padding: 0; background: none; color: #233951; font-size: 13px; font-weight: 600; cursor: pointer; text-align: left; overflow-wrap: anywhere; }
.secondary { color: #788599; font-size: 11px; line-height: 1.5; margin-top: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }.chip { font-size: 11px; color: #53647b; }
.status { font-size: 12px; display: inline-flex; gap: 6px; align-items: center; }.status i { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }.ok { color: #15805b; }.warn { color: #a06a15; }.off { color: #8290a3; }.busy { color: #2e6eae; }
.actions { display: flex; justify-content: flex-end; align-items: center; gap: 5px; }.actions button,.primary { padding: 6px 9px; border-radius: 4px; font: inherit; font-size: 11px; cursor: pointer; text-decoration: none; border: 1px solid #cbdcf0; background: #f2f7fd; color: #2663a4; }.actions .detail { background: #fff; color: #68778b; border-color: #e0e6ee; }
@media(max-width:700px) { .list-heading { display: none; }.resource-row { grid-template-columns: 1fr auto; gap: 10px; padding: 14px; }.type { grid-column: 1; grid-row: 2; }.state { grid-column: 1; grid-row: 3; }.actions { grid-column: 2; grid-row: 1 / span 3; flex-direction: column; }.hint { white-space: normal; } }
</style>
