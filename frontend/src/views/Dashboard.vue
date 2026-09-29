<template>
  <section class="page">
    <header class="page-head">
      <div>
        <h2>运营概览</h2>
        <p class="page-desc">汇总各业务模块的关键指标，先看总量再看异常；值班缺口与排班看板同源。</p>
      </div>
    </header>
    <div class="stat-row">
      <article v-for="card in cards" :key="card.label" class="stat-card">
        <span class="stat-label">{{ card.label }}</span>
        <strong class="stat-value">{{ card.value }}</strong>
      </article>
    </div>

    <section v-if="gaps" class="gap-panel">
      <header class="gap-head">
        <h3>本周值班缺口</h3>
        <span class="gap-week">{{ gaps.weekStart }} ~ {{ gaps.weekEnd }}</span>
      </header>
      <div class="stat-row">
        <article class="stat-card">
          <span class="stat-label">未排班天数</span>
          <strong class="stat-value warn">{{ gaps.unscheduledDays }}</strong>
        </article>
        <article class="stat-card">
          <span class="stat-label">缺口格子（无人顶岗）</span>
          <strong class="stat-value danger">{{ gaps.gapCount }}</strong>
        </article>
        <article class="stat-card">
          <span class="stat-label">替班缺失格子</span>
          <strong class="stat-value missing">{{ gaps.substituteMissingCount }}</strong>
        </article>
      </div>
      <table class="data-table">
        <thead>
          <tr><th>班次时段</th><th>缺口格子</th><th>替班缺失格子</th></tr>
        </thead>
        <tbody>
          <tr v-for="row in gaps.byShift" :key="row.shift">
            <td>{{ row.shift }}</td>
            <td :class="{ 'cell-danger': row.gapCount > 0 }">{{ row.gapCount }}</td>
            <td :class="{ 'cell-missing': row.substituteMissingCount > 0 }">{{ row.substituteMissingCount }}</td>
          </tr>
        </tbody>
      </table>
      <p class="gap-tip">各班次缺口随值班看板格子里的排班实时变化，登记、替班或作废旧排班后此处同步更新。</p>
    </section>

    <table class="data-table">
      <thead>
        <tr><th>业务模块</th><th>今日新增</th><th>待处理</th><th>异常量</th></tr>
      </thead>
      <tbody>
        <tr v-for="row in moduleRows" :key="row.name">
          <td>{{ moduleLabel(row.name) }}</td>
          <td>{{ row.created }}</td>
          <td>{{ row.pending }}</td>
          <td>{{ row.abnormal }}</td>
        </tr>
      </tbody>
    </table>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { fetchJson } from '@/api/client'
import type { StaffshiftGaps } from '@/views/staffshift/types'

type Overview = {
  cards: { label: string; value: number }[]
  modules: { name: string; created: number; pending: number; abnormal: number }[]
  staffshiftGaps?: StaffshiftGaps | null
}

const cards = ref<Overview['cards']>([])
const moduleRows = ref<Overview['modules']>([])
const gaps = ref<StaffshiftGaps | null>(null)

const LABELS: Record<string, string> = {
  flightstand: '机位分配', marshalling: '引导入位', bridge: '廊桥对接', baggage: '行李装卸',
  catering: '航食配餐', fueling: '航油加注', deicing: '除冰作业', lavatory: '清水排污',
  pushback: '推出开车', gse: '地面设备', cargo: '货物装卸', clearance: '放行签派',
  turnaround: '过站保障', ramp: '机坪巡查', weather2: '航空气象', vehicle: '特种车辆',
  staffshift: '人员排班', runway: '跑道灯光', emergencyplan: '应急处置', qualitycheck: '质量监察',
  staffshift_roster: '班组台账',
}

function moduleLabel(name: string): string {
  return LABELS[name] ?? name
}

onMounted(async () => {
  try {
    const payload = await fetchJson<Overview>('/api/overview')
    cards.value = payload.cards
    moduleRows.value = payload.modules
    gaps.value = payload.staffshiftGaps ?? null
  } catch {
    cards.value = [{ label: '业务模块', value: 0 }, { label: '今日新增', value: 0 }]
  }
})
</script>

<style scoped>
.gap-panel { background: #fff; border: 1px solid var(--border); border-radius: 8px; padding: 12px 14px; margin-bottom: 14px; }
.gap-head { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 8px; }
.gap-head h3 { margin: 0; font-size: 15px; }
.gap-week { font-size: 12px; color: var(--muted); }
.gap-panel .stat-row { margin-bottom: 10px; }
.stat-value.danger { color: #b42318; }
.stat-value.missing { color: #b54708; }
.stat-value.warn { color: #475467; }
.cell-danger { color: #b42318; font-weight: 600; }
.cell-missing { color: #b54708; font-weight: 600; }
.gap-tip { font-size: 12px; color: var(--muted); margin: 8px 0 0; }
</style>
