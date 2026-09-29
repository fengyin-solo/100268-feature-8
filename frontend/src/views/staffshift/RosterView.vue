<template>
  <div class="roster-view">
    <div class="filter-bar">
      <label class="filter-item">
        <span>台账日期</span>
        <input v-model="date" type="date" @change="reload" />
      </label>
      <label class="filter-item checkbox">
        <input v-model="onlyOnDuty" type="checkbox" />
        <span>只看当日在岗</span>
      </label>
      <button class="btn ghost" type="button" @click="syncWithBoard">与看板同一天</button>
    </div>

    <div class="stat-row">
      <article class="stat-card">
        <span class="stat-label">花名册人数</span>
        <strong class="stat-value">{{ roster.members.length }}</strong>
      </article>
      <article class="stat-card">
        <span class="stat-label">{{ roster.date }} 在岗人数</span>
        <strong class="stat-value">{{ roster.onDutyCount }}</strong>
      </article>
      <article class="stat-card">
        <span class="stat-label">数据口径</span>
        <strong class="stat-value" style="font-size:13px;padding-top:4px;">与值班看板同源</strong>
      </article>
    </div>

    <table class="data-table">
      <thead>
        <tr>
          <th>姓名</th>
          <th>所属班组</th>
          <th>可值岗位</th>
          <th>当日是否在岗</th>
          <th>当班安排（班次·岗位 / 替班）</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="m in shownMembers" :key="String(m.id)" :class="{ off: !m.onDuty }">
          <td>{{ m.姓名 }}</td>
          <td>{{ m.所属班组 }}</td>
          <td>{{ m.可值岗位 }}</td>
          <td>
            <span class="status-tag" :class="m.onDuty ? 'st-ok' : 'st-off'">
              {{ m.onDuty ? '在岗' : '休息' }}
            </span>
          </td>
          <td>
            <template v-if="m.assignments.length">
              <div v-for="(a, i) in m.assignments" :key="i" class="assign-line">
                {{ a.班次时段 }} · {{ a.岗位名称 }}
                <span class="assign-sub">／替班：{{ a.替班人员 || '（缺替班）' }}</span>
                <span class="assign-check">／{{ a.到岗确认 }}</span>
              </div>
            </template>
            <span v-else class="muted">—</span>
          </td>
        </tr>
        <tr v-if="!shownMembers.length">
          <td colspan="5" class="empty-state">该条件下没有班组成员</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import type { RosterData } from './types'

const props = defineProps<{
  roster: RosterData
  boardDate: string
}>()

const emit = defineEmits<{ (e: 'load-date', date: string): void }>()

const date = ref(props.roster.date)
const onlyOnDuty = ref(false)

watch(() => props.roster.date, (value) => { date.value = value })

const shownMembers = computed(() =>
  onlyOnDuty.value ? props.roster.members.filter((m) => m.onDuty) : props.roster.members,
)

function reload() {
  if (date.value) emit('load-date', date.value)
}

function syncWithBoard() {
  date.value = props.boardDate
  emit('load-date', props.boardDate)
}
</script>

<style scoped>
.filter-item.checkbox { display: flex; align-items: center; gap: 6px; flex-direction: row; }
.filter-item.checkbox span { color: #1f2937; }
tr.off { color: #98a2b3; }
.status-tag { font-size: 11px; border-radius: 4px; padding: 1px 8px; }
.st-ok { background: #e6f4ea; color: #1d6b3a; }
.st-off { background: #eef0f3; color: #667085; }
.assign-line { font-size: 12px; line-height: 1.7; }
.assign-sub { color: #1a56c4; }
.assign-check { color: var(--muted); }
.muted { color: var(--muted); }
</style>
