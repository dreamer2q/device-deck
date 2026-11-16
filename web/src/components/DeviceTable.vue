<script setup>
import { platformLabel } from '../lib/platform.js'
import { deviceStatus, deviceReadinessHint } from '../lib/deviceStatus.js'
defineProps({ devices: { type: Array, required: true } })
const emit = defineEmits(['edit-alias', 'maintenance'])
const isVirtual = device => device.extra?.is_virtual === true || device.extra?.device_kind === 'virtual'
const identity = device => isVirtual(device) ? device.extra?.vm_instance_id || device.serial : device.serial
const agentName = device => device.agent_name_current || device.agent_id_current || device.agent_id || '—'
</script>

<template>
  <div class="table-wrap">
    <table class="device-table">
      <thead><tr><th>设备 / 标识</th><th>平台</th><th>状态</th><th>型号 / 系统</th><th>所在节点</th><th class="actions">操作</th></tr></thead>
      <tbody>
        <tr v-for="d in devices" :key="d.serial">
          <td class="device-cell">
            <RouterLink :to="`/device/${encodeURIComponent(d.serial)}`" class="device-name" :title="d.alias || d.model">{{ d.alias || d.model || '未命名设备' }}</RouterLink>
            <span v-if="isVirtual(d)" class="kind">VM</span>
            <div class="secondary mono" :title="d.serial">{{ identity(d) }}</div>
          </td>
          <td><span class="platform">{{ platformLabel(d) }}</span></td>
          <td>
            <span class="status" :class="deviceStatus(d).cls"><i />{{ deviceStatus(d).label }}</span>
            <div v-if="deviceReadinessHint(d)" class="secondary readiness" :title="deviceReadinessHint(d)">{{ deviceReadinessHint(d) }}</div>
            <div v-if="d.lock" class="secondary" :title="d.lock.holder">{{ ['manual', 'session'].includes(d.lock.holder_type) ? '人工控制' : 'Agent 任务' }} · {{ d.lock.holder }}</div>
          </td>
          <td><span>{{ [d.brand, d.model].filter(Boolean).join(' ') || '—' }}</span><div class="secondary">{{ d.os_version || '—' }}<span v-if="d.screen_width"> · {{ d.screen_width }}×{{ d.screen_height }}</span></div></td>
          <td class="node-cell"><span :title="agentName(d)">{{ agentName(d) }}</span><div class="secondary"><span class="node-dot" :class="{ connected: d.agent_online }" />{{ d.agent_online ? '已连接' : '未连接' }}</div></td>
          <td class="actions"><button :disabled="!!d.lock" @click="emit('maintenance', d)">{{ d.extra?.mirror_paused ? '恢复' : '暂停镜像' }}</button> <button type="button" @click="emit('edit-alias', d)">改名</button><RouterLink class="enter" :to="`/device/${encodeURIComponent(d.serial)}`">工作台 ↗</RouterLink></td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.table-wrap { overflow: auto; border: 1px solid #dfe4ea; border-radius: 5px; background: #fff; }
.device-table { width: 100%; border-collapse: collapse; text-align: left; font-size: 12px; table-layout: fixed; min-width: 780px; }
th { padding: 9px 12px; color: #697386; font-weight: 500; background: #f8fafc; border-bottom: 1px solid #dfe4ea; white-space: nowrap; position: sticky; top: 0; z-index: 1; }
th:first-child { width: 25%; } th:nth-child(2) { width: 9%; } th:nth-child(3) { width: 16%; } th:nth-child(4) { width: 19%; } th:nth-child(5) { width: 18%; } th:last-child { width: 214px; }
td { padding: 8px 12px; border-bottom: 1px solid #edf0f3; vertical-align: middle; }
tr:last-child td { border-bottom: 0; } tbody tr:hover { background: #f8fbff; }
.device-name { font-weight: 600; color: #182b45; text-decoration: none; overflow-wrap: anywhere; }
.device-name:hover { color: #1d66c2; text-decoration: underline; }
.secondary { font-size: 11px; line-height: 1.5; color: #758094; margin-top: 3px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.mono { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
.kind { font-size: 9px; margin-left: 6px; color: #6b7280; border: 1px solid #dfe4ea; border-radius: 3px; padding: 1px 4px; }
.platform { font-size: 10px; color: #475569; letter-spacing: .03em; }
.status { display: inline-flex; align-items: center; gap: 6px; font-size: 11px; color: #64748b; }
.status i, .node-dot { display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: #94a3b8; }
.status.ok { color: #167246; } .status.ok i, .node-dot.connected { background: #26a269; }
.status.warn { color: #a16a0c; } .status.warn i { background: #d69a27; }
.status.busy { color: #2563b4; } .status.busy i { background: #3979d4; }
.node-cell > span { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.node-dot { margin-right: 5px; }
.actions { text-align: right; white-space: nowrap; }
.actions button, .enter { padding: 5px 7px; border: 1px solid #dfe4ea; border-radius: 4px; background: #fff; color: #536176; font: inherit; font-size: 11px; cursor: pointer; text-decoration: none; }
.enter { margin-left: 5px; color: #1c63b3; border-color: #c7dbf3; }
button:hover, .enter:hover { background: #eef5fe; }
</style>
