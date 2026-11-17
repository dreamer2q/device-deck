import { vmLifecycle, stateLabel } from './vmLifecycle.js'
import { familyOf } from './platform.js'

export const isVirtual = d => !!d.vm || d.extra?.is_virtual === true || d.extra?.device_kind === 'virtual'

export function mergeResources(devices, instances, agents) {
  const byAgent = new Map(agents.map(a => [a.agent_id, a]))
  const remaining = new Set(devices)
  const rows = instances.map(vm => {
    // Match VM identity AND host ownership, never a serial alone.
    const live = devices.find(d => d.platform === vm.platform
      && d.extra?.vm_instance_id === vm.id && d.agent_id === vm.assigned_agent_id)
    if (live) remaining.delete(live)
    const host = byAgent.get(vm.assigned_agent_id)
    return { ...(live || {}), resource_id: `vm:${vm.platform}:${vm.id}`, vm,
      serial: live?.serial || '', alias: vm.alias || live?.alias || vm.name,
      platform: vm.platform, model: live?.model || vm.device_type_name || vm.device_model || vm.profile_name || '模拟器',
      os_version: live?.os_version || vm.os_version || vm.runtime_name || '',
      extra: { ...live?.extra, is_virtual: true, device_kind: 'virtual', vm_instance_id: vm.id },
      host, agent_online: !!host, agent_id: vm.assigned_agent_id,
      agent_name_current: host?.agent_name || vm.assigned_agent_id || '未选择', live: !!live }
  })
  for (const d of remaining) {
    const host = byAgent.get(d.agent_id)
    rows.push({ ...d, resource_id: `device:${d.platform}:${d.serial}`, host,
      agent_online: !!host, agent_name_current: host?.agent_name || d.agent_id || '—', live: true })
  }
  return rows
}

export function resourceStatus(d) {
  const life = d.vm ? vmLifecycle(d.vm) : null
  if (isVirtual(d) && !d.vm) return { label: '实例状态待确认', cls: 'warn', group: 'not_ready', hint: '未关联到模拟器配置，刷新后再操作。' }
  if (life && ['starting', 'stopping'].includes(life.state)) return { label: stateLabel(d.vm), cls: 'busy', group: 'not_ready', hint: life.notice }
  if (!d.agent_online && (d.agent_id || !d.vm)) return { label: '运行位置离线', cls: 'off', group: 'offline', hint: '等待设备所在机器重新连接。' }
  if (life && life.state === null) return { label: '状态待确认', cls: 'warn', group: 'not_ready', hint: life.error || life.notice }
  if (life && ['draft', 'stopped'].includes(life.state)) return { label: life.state === 'draft' ? '待准备' : '已关机', cls: 'off', group: 'stopped', hint: life.error || life.notice }
  if (d.extra?.mirror_paused) return { label: '镜像已暂停', cls: 'warn', group: 'not_ready', hint: '恢复镜像后才能重新控制。' }
  if (d.status !== 'online' || !d.live) return { label: '设备未连接', cls: 'off', group: 'offline', hint: d.extra?.reason || '' }
  if (d.extra?.readiness?.ready !== true) {
    const blocked = ['ios', 'ios_sim'].includes(d.platform) ? d.host?.ios_environment?.checks?.find(c => c.status === 'blocked' && (d.platform === 'ios' ? c.id !== 'simulator_runtime' : c.id !== 'device_signing')) : null
    return { label: blocked ? `${blocked.title}待准备` : '控制未就绪', cls: 'warn', group: 'not_ready', hint: blocked?.next_step || d.extra?.wda_stage?.hint || d.extra?.readiness?.hint || '查看环境与诊断了解当前条件。' }
  }
  if (d.lock) return { label: ['manual', 'session'].includes(d.lock.holder_type) ? '人工占用中' : 'Agent 执行中', cls: 'busy', group: 'busy', hint: d.lock.holder || '占用者未知' }
  return { label: '可操作', cls: 'ok', group: 'online', hint: life?.error || '' }
}

export function resourceCanOpen(d) {
  if (isVirtual(d) && !d.vm) return false
  return !!d.serial && d.live && d.agent_online && d.status === 'online'
    && d.extra?.readiness?.ready === true && !d.extra?.mirror_paused
    && (!d.vm || (vmLifecycle(d.vm).state === 'running' && vmLifecycle(d.vm).agent_online))
}

export function filterResources(rows, { search = '', platform = 'all', kind = 'all', status = 'all' } = {}) {
  const term = search.trim().toLowerCase()
  return rows.filter(d => (platform === 'all' || familyOf(d) === platform)
    && (kind === 'all' || isVirtual(d) === (kind === 'virtual'))
    && (status === 'all' || resourceStatus(d).group === status)
    && (!term || [d.alias, d.model, d.brand, d.serial, d.os_version, d.agent_name_current].some(v => String(v || '').toLowerCase().includes(term))))
}
