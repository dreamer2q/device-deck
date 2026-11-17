<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import DeviceTable from '../components/DeviceTable.vue'
import DeviceDetails from '../components/DeviceDetails.vue'
import { mergeResources, filterResources, resourceStatus } from '../lib/deviceResources.js'
import { canStart, canStop } from '../lib/vmLifecycle.js'
import { api, internal } from '../lib/api.js'
import { platformLabel } from '../lib/platform.js'

const route = useRoute()
const router = useRouter()
const devices = ref([])
const agents = ref([])
const instances = ref([])
const loading = ref(false)
const error = ref(null)
const filter = ref('all')
const platform = ref('all')
const kind = ref('all')
const search = ref('')
const selectedId = ref('')
const busy = ref('')
const families = { android: internal.androidVms, ios_sim: internal.iosSimVms, harmony: internal.harmonyVms }
let pollTimer = null
let refreshTask = null
let active = true
const resourceErrors = ref([])

async function maintenance(device) {
  if (busy.value || device.lock) return
  busy.value = device.resource_id
  try {
    await fetch(`/api/devices/${encodeURIComponent(device.serial)}/mirror-maintenance`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ paused: !device.extra?.mirror_paused }),
    }).then(async r => { if (!r.ok) throw Error((await r.json()).detail || '维护操作失败') })
    await refresh()
  } catch (e) { error.value = String(e) }
  finally { busy.value = '' }
}

function refresh() {
  if (refreshTask) return refreshTask
  loading.value = true
  const entries = Object.entries(families)
  refreshTask = Promise.allSettled([api.listDevices(), api.listAgents(), ...entries.map(([, api]) => api.list())])
    .then(results => {
      if (!active) return
      const errors = []
      if (results[0].status === 'fulfilled') devices.value = results[0].value
      else { devices.value = []; errors.push('实时设备读取失败') }
      if (results[1].status === 'fulfilled') agents.value = results[1].value
      else { agents.value = []; errors.push('运行位置状态读取失败') }
      instances.value = entries.flatMap(([platform], index) => {
        const r = results[index + 2]
        if (r.status !== 'fulfilled' || !Array.isArray(r.value)) {
          errors.push(`${platform === 'ios_sim' ? 'iOS' : platform} 模拟器读取失败`)
          // Fail closed for stale lifecycle actions, retain visible resource IDs.
          return instances.value.filter(vm => vm.platform === platform).map(vm => ({ ...vm, lifecycle: undefined }))
        }
        return r.value.map(vm => ({ ...vm, platform }))
      })
      resourceErrors.value = errors
    }).finally(() => { refreshTask = null; loading.value = false })
  return refreshTask
}
const enrichedDevices = computed(() => mergeResources(devices.value, instances.value, agents.value))
const selected = computed(() => enrichedDevices.value.find(d => d.resource_id === selectedId.value))
const filtered = computed(() => filterResources(enrichedDevices.value, { search: search.value, platform: platform.value, kind: kind.value, status: filter.value }))
const counts = computed(() => {
  const base = { all: enrichedDevices.value.length, online: 0, not_ready: 0, busy: 0, offline: 0, stopped: 0 }
  for (const d of enrichedDevices.value) base[resourceStatus(d).group]++
  return base
})
async function vmAction(device, action) {
  if (busy.value || device.lock || !device.vm) return
  if (action === 'start' ? !canStart(device.vm) : !canStop(device.vm)) return
  if (action === 'stop' && !confirm(`停止“${device.alias}”？应用和数据将保留。`)) return
  busy.value = device.resource_id
  error.value = null
  try {
    await families[device.platform][action](device.vm.id)
    // Do not let an earlier poll overwrite the operation's resulting state.
    await refreshTask
    await refresh()
  } catch (e) { error.value = prettyErr(e) }
  finally { busy.value = '' }
}
const lockLostNotice = computed(() => {
  if (route.query.lockLost !== '1') return ''
  const serial = String(route.query.serial || '')
  return serial
    ? `设备 ${serial} 的控制权已释放或被其他任务占用，已回到设备总览。`
    : '设备控制权已释放或被其他任务占用，已回到设备总览。'
})

function dismissLockNotice() {
  router.replace({ path: '/', query: {} })
}

onMounted(() => {
  refresh()
  pollTimer = setInterval(() => { if (!document.hidden) refresh() }, 3000)
})
onBeforeUnmount(() => {
  active = false
  if (pollTimer) clearInterval(pollTimer)
})

// ---------------- 别名编辑弹窗 ----------------
// 设计：单一 reactive state 驱动；"保存" / "删除绑定" / "取消" 三个动作互斥。
// Access configuration is owned by the server gateway, never a URL token.
const dlg = reactive({
  open: false,
  serial: '',
  platform: '',
  model: '',
  originalAlias: '',
  alias: '',
  note: '',
  busy: false,
  error: '',
  // 虚拟机：别名是 VM 配置的一部分（android_vm_instances.alias），改名要回写 VM
  // 而不是 device_aliases 表；真机才走 device_aliases。vm_id 是唯一锚点。
  vmInstanceId: '',
  vmPlatform: '',
})

function openEdit(device) {
  selectedId.value = ''
  dlg.open = true
  dlg.serial = device.serial
  dlg.platform = device.platform || ''
  dlg.model = `${device.brand || ''} ${device.model || ''}`.trim() || '-'
  dlg.originalAlias = device.alias || ''
  dlg.alias = device.alias || ''
  dlg.note = ''
  dlg.busy = false
  dlg.error = ''
  dlg.vmInstanceId =
    device.vm || device.extra?.device_kind === 'virtual' ? device.extra?.vm_instance_id || '' : ''
  // 用 device.platform 而不是 extra.vm_platform：后者是**产品归属**（iOS 虚拟机
  // 报的是 'ios'，因为对外只有三端），而这里要决定的是「归哪个虚拟机子系统的接口管」，
  // 那由 device.platform 决定（android / harmony / ios_sim）。
  dlg.vmPlatform = device.platform || ''
  // 如果已经绑过，异步把 note 拉回来（别名表里存了备注）
  if (device.alias && !dlg.vmInstanceId) {
    internal.deviceAliases
      .get(device.serial)
      .then((row) => {
        if (dlg.open && dlg.serial === device.serial) {
          dlg.note = row?.note || ''
        }
      })
      .catch(() => {})
  }
}

function closeEdit() {
  dlg.open = false
  dlg.error = ''
}

async function saveAlias() {
  const alias = (dlg.alias || '').trim()
  // 真机：别名必填（要解绑走"删除绑定"）。虚拟机：创建后允许改空（身份锚点是 vm_id）。
  if (!alias && !dlg.vmInstanceId) {
    dlg.error = '别名不能为空；若要解除绑定请点"删除绑定"'
    return
  }
  if (alias.length > 128) {
    dlg.error = '别名长度不能超过 128'
    return
  }
  dlg.busy = true
  dlg.error = ''
  try {
    if (dlg.vmInstanceId) {
      // 虚拟机：回写 VM 配置别名（后端同步 name + DeviceAlias 映射）
      if (dlg.vmPlatform === 'harmony') {
        await internal.harmonyVms.patch(dlg.vmInstanceId, { alias })
      } else if (dlg.vmPlatform === 'ios_sim') {
        await internal.iosSimVms.patch(dlg.vmInstanceId, { alias })
      } else {
        await internal.androidVms.patch(dlg.vmInstanceId, { alias })
      }
    } else {
      await internal.deviceAliases.put(dlg.serial, { alias, note: dlg.note || '' })
    }
    closeEdit()
    await refresh()
  } catch (e) {
    dlg.error = prettyErr(e)
  } finally {
    dlg.busy = false
  }
}

async function unbindAlias() {
  if (!dlg.originalAlias) {
    closeEdit()
    return
  }
  if (!confirm(`确定解除设备 ${dlg.serial} 与别名 "${dlg.originalAlias}" 的绑定？解除后该设备只能走"不指定别名"的随机派发。`)) {
    return
  }
  dlg.busy = true
  dlg.error = ''
  try {
    await internal.deviceAliases.remove(dlg.serial)
    closeEdit()
    await refresh()
  } catch (e) {
    dlg.error = prettyErr(e)
  } finally {
    dlg.busy = false
  }
}

function prettyErr(e) {
  const msg = String(e?.message || e)
  if (msg.includes('alias_conflict')) {
    try {
      const m = msg.match(/\{[\s\S]*\}$/)
      if (m) {
        const parsed = JSON.parse(m[0])
        const detail = parsed?.detail
        if (detail?.conflictSerial) {
          return `别名 "${detail.alias}" 已绑定到另一台设备 (${detail.conflictSerial})，请换一个名字或先解除那台的绑定。`
        }
      }
    } catch (_) { /* fallback */ }
    return '别名冲突：该名字已被另一台设备占用。'
  }
  if (msg.includes('401') || msg.includes('403')) {
    return '服务访问配置异常，请检查服务端网关设置。'
  }
  return msg
}
</script>

<template>
  <section class="page">
    <header class="head">
      <h2>设备 <span class="total-count">{{ counts.all }}</span></h2>
      <RouterLink class="library-link" to="/virtual-machines">＋ 添加模拟器</RouterLink>
      <div class="toolbar">
        <input v-model="search" type="search" class="device-search" placeholder="搜索名称、型号或系统" aria-label="搜索设备" />
        <div class="filters">
          <button
            v-for="f in ['all', 'online', 'not_ready', 'busy', 'stopped', 'offline']"
            :key="f"
            :class="{ active: filter === f }"
            @click="filter = f"
          >
            {{ { all: '全部', online: '可操作', not_ready: '待处理', busy: '占用中', stopped: '未启动', offline: '离线' }[f] }}
            <span class="n">{{ counts[f] }}</span>
          </button>
        </div>
        <button class="refresh" :disabled="loading" @click="refresh">
          {{ loading ? '刷新中…' : '刷新' }}
        </button>
      </div>
    </header>

    <p v-if="lockLostNotice" class="notice">
      <span>{{ lockLostNotice }}</span>
      <button @click="dismissLockNotice">知道了</button>
    </p>
    <p v-if="error" class="err">加载失败：{{ error }}</p>

    <div class="resource-filters">
      <div><span>平台</span><button v-for="p in ['all', 'android', 'ios', 'harmony']" :key="p" :class="{ chosen: platform === p }" @click="platform = p">{{ { all: '全部', android: 'Android', ios: 'iOS', harmony: '鸿蒙' }[p] }}</button></div>
      <div><span>类型</span><button v-for="k in ['all', 'physical', 'virtual']" :key="k" :class="{ chosen: kind === k }" @click="kind = k">{{ { all: '全部', physical: '真机', virtual: '模拟器' }[k] }}</button></div>
    </div>
    <p v-if="resourceErrors.length" class="err">{{ resourceErrors.join('；') }}。受影响的操作暂不可用。</p>
    <DeviceTable v-if="filtered.length" :devices="filtered" :busy="busy" @details="d => selectedId = d.resource_id" @start="d => vmAction(d, 'start')" />
    <p v-else class="empty">{{ loading ? '正在读取设备…' : '没有符合条件的设备。可调整筛选，或添加一个模拟器。' }}</p>
    <DeviceDetails v-if="selected" :device="selected" :busy="busy" @close="selectedId = ''" @edit="openEdit" @maintenance="maintenance" @start="d => vmAction(d, 'start')" @stop="d => vmAction(d, 'stop')" @refresh="refresh" />

    <!-- 别名编辑弹窗 -->
    <div v-if="dlg.open" class="modal-mask" @click.self="closeEdit">
      <div class="modal">
        <div class="modal-hd">
          <h3>{{ dlg.originalAlias ? '修改别名 / 备注' : '绑定别名' }}</h3>
          <button class="modal-x" @click="closeEdit" title="关闭">×</button>
        </div>
        <div class="modal-body">
          <div class="field">
            <label>设备</label>
            <div class="readonly">
              <span class="tag">{{ platformLabel(dlg.platform) }}</span>
              <span class="readonly-model">{{ dlg.model }}</span>
            </div>
            <div class="serial-line" :title="dlg.serial">serial: {{ dlg.serial }}</div>
          </div>

          <div class="field">
            <label>
              别名 <span class="req">*</span>
              <span class="hint">使用便于识别的名称</span>
            </label>
            <input
              v-model="dlg.alias"
              type="text"
              maxlength="128"
              placeholder="例如：iPhone 回归测试"
              :disabled="dlg.busy"
              @keyup.enter="saveAlias"
            />
          </div>

          <div v-if="!dlg.vmInstanceId" class="field">
            <label>备注（可选）</label>
            <textarea
              v-model="dlg.note"
              rows="3"
              maxlength="1000"
              placeholder="比如摆放工位、负责人、用途……"
              :disabled="dlg.busy"
            />
          </div>
          <p v-else class="hint" style="margin: -4px 0 0">
            修改模拟器名称，不改变实例身份或应用数据。
          </p>

          <p v-if="dlg.error" class="err-inline">{{ dlg.error }}</p>
        </div>
        <div class="modal-ft">
          <button
            v-if="dlg.originalAlias && !dlg.vmInstanceId"
            class="btn danger"
            :disabled="dlg.busy"
            @click="unbindAlias"
          >
            删除绑定
          </button>
          <span class="ft-spacer" />
          <button class="btn" :disabled="dlg.busy" @click="closeEdit">取消</button>
          <button class="btn primary" :disabled="dlg.busy" @click="saveAlias">
            {{ dlg.busy ? '保存中…' : '保存' }}
          </button>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.resource-filters { display: flex; gap: 28px; flex-wrap: wrap; align-items: center; margin-bottom: 16px; }
.resource-filters > div { display: flex; align-items: center; gap: 4px; }.resource-filters span { color: #8592a3; font-size: 11px; margin-right: 7px; }
.resource-filters button { padding: 5px 9px; border: 0; border-radius: 4px; background: transparent; color: #6c7a8c; font: inherit; font-size: 11px; cursor: pointer; }.resource-filters button.chosen { color: #286eb7; background: #e9f2fc; }

.page {
  padding: 16px 18px 24px;
}
.head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  flex-wrap: wrap;
  gap: 12px;
}
h2 {
  margin: 0;
  font-size: 16px;
}
.toolbar {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-left: auto;
  flex-wrap: wrap;
}
.total-count { font-size: 11px; color: #66758a; background: #e8edf3; border-radius: 4px; padding: 2px 6px; margin-left: 5px; font-weight: 500; }
.library-link { color: #64748b; font-size: 11px; text-decoration: none; }
.device-search { width: 205px; height: 30px; padding: 5px 9px; border: 1px solid #d7dfe8; background: #fff; border-radius: 4px; font: inherit; font-size: 12px; }
.device-search:focus { outline: 2px solid #b7d5f8; outline-offset: 1px; }
.agent-panel summary { display: flex; align-items: center; gap: 7px; cursor: pointer; list-style: none; font-size: 11px; color: #46576d; }
.agent-panel summary::-webkit-details-marker { display: none; }
.agent-summary { color: #8490a0; margin-left: 5px; }
.agent-expand { margin-left: auto; color: #66758a; }
.agent-expand::after { content: ' ▾'; }
.agent-panel[open] .agent-expand::after { content: ' ▴'; }
.agent-panel[open] .agent-list { margin-top: 10px; padding-top: 10px; border-top: 1px solid #e5eaf0; }
@media(max-width: 900px) { .toolbar { width: 100%; } .device-search { flex: 1; min-width: 160px; } .filters { overflow-x: auto; } }
.filters {
  display: flex;
  gap: 4px;
  padding: 2px;
  background: #f2f4f7;
  border-radius: 8px;
}
.filters button {
  padding: 5px 8px;
  font-size: 11px;
  background: transparent;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  color: #4b5563;
}
.filters button.active {
  background: #fff;
  color: #111;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.08);
}
.filters .n {
  color: #9aa3b0;
  margin-left: 4px;
  font-size: 12px;
}
.refresh {
  padding: 5px 10px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: #fff;
  cursor: pointer;
  font-size: 11px;
}
.refresh:hover {
  background: #f5f7fa;
}
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 16px;
}
.empty {
  margin-top: 48px;
  text-align: center;
  color: #6b7280;
}
.err {
  padding: 10px 14px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #991b1b;
  border-radius: 6px;
}
.notice {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 14px;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  color: #1e3a8a;
  border-radius: 6px;
}
.notice button {
  border: 1px solid #93c5fd;
  border-radius: 6px;
  background: #fff;
  color: #1d4ed8;
  cursor: pointer;
  padding: 5px 10px;
  white-space: nowrap;
}
.notice button:hover {
  background: #dbeafe;
}
.agent-panel {
  margin-bottom: 10px;
  padding: 9px 11px;
  background: #fff;
  border: 1px solid #e2e6ec;
  border-radius: 4px;
}
.agent-panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}
.agent-title {
  font-size: 14px;
  font-weight: 700;
  color: #111827;
}
.agent-sub,
.agent-tip {
  margin-top: 2px;
  font-size: 12px;
  color: #6b7280;
}
.agent-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 8px;
}
.agent-item {
  display: flex;
  align-items: center;
  gap: 9px;
  min-width: 0;
  padding: 8px 10px;
  background: #f9fafb;
  border: 1px solid #eef1f5;
  border-radius: 8px;
}
.agent-dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: #22c55e;
  flex-shrink: 0;
}
.agent-main {
  min-width: 0;
}
.agent-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
  font-weight: 700;
  color: #1f2937;
}
.agent-meta,
.agent-empty {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12px;
  color: #6b7280;
}

/* ---- 弹窗 ---- */
.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.55);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  padding: 16px;
}
.modal {
  width: min(480px, 100%);
  background: #fff;
  border-radius: 10px;
  box-shadow: 0 18px 48px rgba(15, 23, 42, 0.28);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.modal-hd {
  padding: 14px 18px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid #eef1f5;
}
.modal-hd h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  color: #111827;
}
.modal-x {
  background: transparent;
  border: none;
  font-size: 22px;
  line-height: 1;
  color: #9aa3b0;
  cursor: pointer;
}
.modal-x:hover {
  color: #374151;
}
.modal-body {
  padding: 14px 18px 4px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.field label {
  font-size: 12px;
  color: #4b5563;
  font-weight: 600;
}
.field label .req {
  color: #dc2626;
  margin: 0 2px;
}
.field label .hint {
  margin-left: 6px;
  font-weight: 400;
  color: #9aa3b0;
}
.field input,
.field textarea {
  font: inherit;
  font-size: 14px;
  padding: 8px 10px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  outline: none;
  resize: vertical;
}
.field input:focus,
.field textarea:focus {
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15);
}
.readonly {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
}
.readonly-model {
  color: #1f2937;
  font-weight: 500;
}
.tag {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  background: #eef2ff;
  color: #4338ca;
  font-weight: 700;
  letter-spacing: 0.06em;
}
.serial-line {
  font-family: ui-monospace, SF Mono, Menlo, monospace;
  font-size: 11px;
  color: #6b7280;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.err-inline {
  margin: 4px 0 0;
  padding: 8px 10px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #991b1b;
  border-radius: 6px;
  font-size: 13px;
  line-height: 1.45;
}
.modal-ft {
  padding: 12px 18px 16px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.ft-spacer {
  flex: 1;
}
.btn {
  padding: 7px 14px;
  border: 1px solid #d1d5db;
  background: #fff;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
  color: #374151;
}
.btn:hover:not(:disabled) {
  background: #f3f4f6;
}
.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.btn.primary {
  background: #2563eb;
  border-color: #1d4ed8;
  color: #fff;
}
.btn.primary:hover:not(:disabled) {
  background: #1d4ed8;
}
.btn.danger {
  color: #b91c1c;
  border-color: #fecaca;
  background: #fff5f5;
}
.btn.danger:hover:not(:disabled) {
  background: #fee2e2;
}
</style>
