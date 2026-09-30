<template>
  <section class="page">
    <header class="page-head">
      <div>
        <h2>运营概览</h2>
        <p class="page-desc">汇总各业务模块的关键指标，先看总量再看异常；各班次缺口与值班看板格子同源。</p>
      </div>
    </header>
    <div class="stat-row">
      <article v-for="card in cards" :key="card.label" class="stat-card">
        <span class="stat-label">{{ card.label }}</span>
        <strong class="stat-value">{{ card.value }}</strong>
      </article>
    </div>

    <div class="gap-panel">
      <div class="gap-panel-head">
        <h3>本周各班次缺口（{{ shiftBoard?.weekStart }} ~ {{ shiftBoard?.weekEnd }}）</h3>
        <span class="week-tip">
          缺替班格子 {{ shiftBoard?.缺替班总数 ?? 0 }} 个 ·
          未排班 {{ shiftBoard?.未排班日期.length ?? 0 }} 天
        </span>
      </div>
      <div class="stat-row">
        <article v-for="gap in shiftBoard?.缺口 ?? []" :key="gap.班次时段" class="stat-card"
                 :class="{ 'stat-alert': gap.缺口数 > 0 }">
          <span class="stat-label">{{ gap.班次时段 }}缺口</span>
          <strong class="stat-value">{{ gap.缺口数 }}</strong>
        </article>
        <article class="stat-card" :class="{ 'stat-alert': (shiftBoard?.缺口总数 ?? 0) > 0 }">
          <span class="stat-label">缺口总数</span>
          <strong class="stat-value">{{ shiftBoard?.缺口总数 ?? 0 }}</strong>
        </article>
      </div>
      <p v-if="shiftBoard && shiftBoard.未排班日期.length" class="gap-note">
        未排班日期按"未排班"呈现，不计缺口：{{ shiftBoard.未排班日期.join('、') }}
      </p>
    </div>

    <table class="data-table">
      <thead>
        <tr><th>业务模块</th><th>今日新增</th><th>待处理</th><th>异常量</th></tr>
      </thead>
      <tbody>
        <tr v-for="row in moduleRows" :key="row.name">
          <td>{{ row.name }}</td>
          <td>{{ row.created }}</td>
          <td>{{ row.pending }}</td>
          <td>{{ row.abnormal }}</td>
        </tr>
      </tbody>
    </table>
  </section>
</template>

<script setup lang="ts">
import { onActivated, onMounted, ref } from 'vue'

import { fetchJson } from '@/api/client'

type Overview = {
  cards: { label: string; value: number }[]
  modules: { name: string; created: number; pending: number; abnormal: number }[]
}

type ShiftBoard = {
  weekStart: string
  weekEnd: string
  缺口: { 班次时段: string; 缺口数: number }[]
  缺口总数: number
  缺替班总数: number
  未排班日期: string[]
}

const cards = ref<Overview['cards']>([])
const moduleRows = ref<Overview['modules']>([])
const shiftBoard = ref<ShiftBoard | null>(null)

async function loadOverview() {
  try {
    const payload = await fetchJson<Overview>('/api/overview')
    cards.value = payload.cards
    moduleRows.value = payload.modules
  } catch {
    cards.value = [{"label": "业务模块", "value": 0}, {"label": "今日新增", "value": 0}]
    moduleRows.value = []
  }
}

async function loadShiftGaps() {
  // 缺口数直接来自值班看板：格子里排班变了，这里跟着变
  try {
    shiftBoard.value = await fetchJson<ShiftBoard>('/api/staffshift/board')
  } catch {
    shiftBoard.value = null
  }
}

onMounted(async () => {
  await Promise.all([loadOverview(), loadShiftGaps()])
})
// 从人员排班页切回概览时刷新，保证缺口与格子里的最新排班一致
onActivated(() => {
  void loadShiftGaps()
})
</script>
