<template>
  <div class="table-view">
    <div class="filter-bar">
      <label class="filter-item">
        <span>关键字</span>
        <input v-model="keyword" placeholder="编号 / 岗位 / 值班人员" @keyup.enter="emitSearch" />
      </label>
      <label class="filter-item">
        <span>班次时段</span>
        <select v-model="shiftFilter">
          <option value="">全部</option>
          <option v-for="s in shifts" :key="s" :value="s">{{ s }}</option>
        </select>
      </label>
      <label class="filter-item">
        <span>日期</span>
        <input v-model="dateFilter" type="date" />
      </label>
      <label class="filter-item checkbox">
        <input v-model="includeVoid" type="checkbox" @change="emitSearch" />
        <span>显示已作废记录</span>
      </label>
      <button class="btn" type="button" @click="emitSearch">查询</button>
      <button class="btn ghost" type="button" @click="reset">重置</button>
      <button class="btn" type="button" @click="expandAll">全部展开</button>
      <button class="btn ghost" type="button" @click="collapseAll">全部收起</button>
    </div>

    <div v-for="group in groups" :key="group.shift" class="shift-group">
      <header class="group-head" @click="toggle(group.shift)">
        <span class="caret">{{ expanded[group.shift] ? '▾' : '▸' }}</span>
        <strong>{{ group.shift }}</strong>
        <span class="group-meta">
          共 {{ group.rows.length }} 条 · 缺口 {{ group.gapCount }} · 缺替班 {{ group.substituteMissingCount }}
        </span>
      </header>
      <table v-if="expanded[group.shift]" class="data-table">
        <thead>
          <tr>
            <th v-for="col in columns" :key="col">{{ col }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in group.rows" :key="String(row.id)" :class="{ voided: row.void }">
            <td>{{ row.排班编号 }}</td>
            <td>{{ row.岗位名称 }}</td>
            <td>{{ row.值班人员 || '—' }}</td>
            <td>{{ row.值班日期 }}</td>
            <td>{{ row.班次时段 }}</td>
            <td :class="{ 'cell-missing': !row.替班人员 }">
              {{ row.替班人员 || '（缺替班）' }}
            </td>
            <td>{{ row.到岗确认 }}</td>
            <td>
              <span class="status-tag" :class="statusClass(row)">{{ row.排班状态 }}</span>
            </td>
          </tr>
          <tr v-if="!group.rows.length">
            <td :colspan="columns.length" class="empty-state">该时段暂无符合条件的排班</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'

import type { ShiftEntry } from './types'

const props = defineProps<{
  rows: ShiftEntry[]
  shifts: string[]
  expanded: Record<string, boolean>
}>()

const emit = defineEmits<{
  (e: 'toggle', shift: string): void
  (e: 'search', payload: { keyword: string; shift: string; date: string; includeVoid: boolean }): void
  (e: 'set-all', value: boolean): void
}>()

const columns = ['排班编号', '岗位名称', '值班人员', '值班日期', '班次时段', '替班人员', '到岗确认', '排班状态']

const keyword = ref('')
const shiftFilter = ref('')
const dateFilter = ref('')
const includeVoid = ref(true)

// 整表分组固定按 早/中/夜 三段，保证每段都在（哪怕为空），展开状态由父组件持有。
const groups = computed(() => props.shifts.map((shift) => {
  const groupRows = props.rows.filter((r) => r.班次时段 === shift)
  return {
    shift,
    rows: groupRows,
    gapCount: groupRows.filter((r) => !r.void && !r.值班人员).length,
    substituteMissingCount: groupRows.filter((r) => !r.void && r.值班人员 && !r.替班人员).length,
  }
}))

function toggle(shift: string) {
  emit('toggle', shift)
}

function emitSearch() {
  emit('search', {
    keyword: keyword.value.trim(),
    shift: shiftFilter.value,
    date: dateFilter.value,
    includeVoid: includeVoid.value,
  })
}

function reset() {
  keyword.value = ''
  shiftFilter.value = ''
  dateFilter.value = ''
  includeVoid.value = true
  emitSearch()
}

function expandAll() {
  emit('set-all', true)
}

function collapseAll() {
  emit('set-all', false)
}

function statusClass(row: ShiftEntry): string {
  if (row.void || row.排班状态 === '已作废') return 'st-void'
  if (row.排班状态 === '已替班') return 'st-sub'
  if (row.排班状态 === '已确认') return 'st-ok'
  return 'st-pending'
}
</script>

<style scoped>
.filter-item.checkbox { display: flex; align-items: center; gap: 6px; flex-direction: row; }
.filter-item.checkbox span { color: #1f2937; }
.shift-group { border: 1px solid var(--border); border-radius: 8px; margin-bottom: 10px; overflow: hidden; background: #fff; }
.group-head { display: flex; align-items: center; gap: 10px; padding: 9px 12px; cursor: pointer; background: #f8fafc; }
.group-meta { font-size: 12px; color: var(--muted); }
.caret { width: 12px; color: var(--muted); }
.data-table { border: none; }
.data-table th:first-child, .data-table td:first-child { border-left: none; }
.data-table th:last-child, .data-table td:last-child { border-right: none; }
tr.voided { color: #98a2b3; background: #fafafa; }
tr.voided td { text-decoration: line-through; }
.cell-missing { color: #b54708; font-weight: 600; }
.status-tag { font-size: 11px; border-radius: 4px; padding: 1px 8px; }
.st-ok { background: #e6f4ea; color: #1d6b3a; }
.st-sub { background: #e8f0fe; color: #1a56c4; }
.st-pending { background: #fffaeb; color: #b54708; }
.st-void { background: #eef0f3; color: #667085; }
</style>
