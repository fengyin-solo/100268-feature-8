<template>
  <section class="page" data-module="staffshift">
    <header class="page-head">
      <div>
        <h2>值班排班看板</h2>
        <p class="page-desc">
          按班次时段铺格子直接看缺口：缺人留缺口记号、缺替班单独标记；点开格子安排替班。
          看板、整表、班组台账读到的是同一份在岗排班。
        </p>
      </div>
      <div class="page-actions">
        <button class="btn primary" type="button" @click="createOpen = true">登记排班</button>
      </div>
    </header>

    <nav class="tabs">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        type="button"
        class="tab"
        :class="{ active: activeTab === tab.key }"
        @click="switchTab(tab.key)"
      >
        {{ tab.label }}
      </button>
    </nav>

    <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>

    <BoardGrid
      v-if="activeTab === 'board' && board"
      :board="board"
      @prev-week="changeWeek(-1)"
      @next-week="changeWeek(1)"
      @this-week="goThisWeek"
      @open-cell="openCell"
      @open-day="openUnscheduledDay"
      @jump-table="jumpToTable"
    />

    <ShiftTable
      v-else-if="activeTab === 'table'"
      :rows="tableRows"
      :shifts="shiftOrder"
      :expanded="expandedShifts"
      @toggle="toggleShift"
      @search="onTableSearch"
      @set-all="setAllExpanded"
    />

    <RosterView
      v-else-if="activeTab === 'roster' && roster"
      :roster="roster"
      :board-date="selectedDate"
      @load-date="loadRoster"
    />

    <CellModal
      v-if="activeCell"
      :open="true"
      :cell="activeCell"
      :date="activeCellDate"
      :shift="activeCellShift"
      :busy="busy"
      @close="activeCell = null"
      @arrange-substitute="onArrangeSubstitute"
      @confirm-arrival="onConfirmArrival"
      @create="onCellCreate"
    />

    <CreateModal
      :open="createOpen"
      :positions="positions"
      :shifts="shiftOrder"
      :roster-names="rosterNames"
      :default-date="selectedDate"
      :busy="busy"
      @close="createOpen = false"
      @submit="onCreate"
    />
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { request } from '@/api/client'
import BoardGrid from './BoardGrid.vue'
import CellModal from './CellModal.vue'
import CreateModal, { type CreatePayload } from './CreateModal.vue'
import RosterView from './RosterView.vue'
import ShiftTable from './ShiftTable.vue'
import type { BoardCell, BoardData, RosterData, ShiftEntry } from './types'

const ENDPOINT = '/api/staffshift'
const tabs = [
  { key: 'board', label: '值班看板' },
  { key: 'table', label: '排班整表' },
  { key: 'roster', label: '班组台账' },
] as const

type TabKey = (typeof tabs)[number]['key']

const activeTab = ref<TabKey>('board')
const board = ref<BoardData | null>(null)
const roster = ref<RosterData | null>(null)
const tableRows = ref<ShiftEntry[]>([])
const shiftOrder = ref<string[]>(['早班', '中班', '夜班'])
const positions = ref<string[]>([])
const rosterNames = ref<string[]>([])

const selectedDate = ref(isoToday())
const errorMessage = ref('')
const busy = ref(false)
const createOpen = ref(false)

// 格子详情
const activeCell = ref<BoardCell | null>(null)
const activeCellDate = ref('')
const activeCellShift = ref('')

// 整表展开状态：切换标签/刷新都不清，只有手动收起才收。
const expandedShifts = ref<Record<string, boolean>>({ 早班: true, 中班: true, 夜班: true })

function isoToday(): string {
  const now = new Date()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  return `${now.getFullYear()}-${month}-${day}`
}

async function loadBoard() {
  errorMessage.value = ''
  try {
    const response = await request(`${ENDPOINT}/board?week_start=${encodeURIComponent(selectedDate.value)}`)
    if (!response.ok) throw new Error('值班看板读取失败')
    const data: BoardData = await response.json()
    board.value = data
    shiftOrder.value = data.shifts
    positions.value = data.positions
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '值班看板读取失败'
  }
}

async function loadTable() {
  errorMessage.value = ''
  try {
    const response = await request(`${ENDPOINT}?size=500&include_void=true`)
    if (!response.ok) throw new Error('排班整表读取失败')
    const payload = await response.json()
    tableRows.value = payload.items ?? []
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '排班整表读取失败'
  }
}

async function loadRoster(date: string) {
  errorMessage.value = ''
  try {
    const response = await request(`${ENDPOINT}/roster?date=${encodeURIComponent(date)}`)
    if (!response.ok) throw new Error('班组台账读取失败')
    const data: RosterData = await response.json()
    roster.value = data
    rosterNames.value = data.members.map((m) => m.姓名)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '班组台账读取失败'
  }
}

async function loadMeta() {
  try {
    const response = await request(`${ENDPOINT}/meta`)
    if (!response.ok) return
    const payload = await response.json()
    if (!shiftOrder.value.length) shiftOrder.value = payload.shifts
    if (!positions.value.length) positions.value = payload.positions
  } catch {
    // meta 只是兜底，失败不影响主流程
  }
}

// 任何写操作后统一刷新：看板格子、整表、台账、概览缺口因此始终是同一份口径。
async function refreshAll() {
  const rosterDate = roster.value ? roster.value.date : selectedDate.value
  await Promise.all([loadBoard(), loadTable(), loadRoster(rosterDate)])
}

function changeWeek(delta: number) {
  const current = new Date(selectedDate.value)
  current.setDate(current.getDate() + delta * 7)
  selectedDate.value = current.toISOString().slice(0, 10)
  void loadBoard()
}

function goThisWeek() {
  selectedDate.value = isoToday()
  void loadBoard()
}

function openCell(cell: BoardCell, date: string) {
  const current = board.value
  if (!current) return
  // 通过格子定位它属于哪个班次：在 board 中反查。
  const shiftIndex = current.days.findIndex((d) => d.date === date)
  let shift = ''
  if (shiftIndex >= 0) {
    const idx = current.days[shiftIndex].shifts.findIndex((s) => s.cells.some((c) => c === cell))
    if (idx >= 0) shift = current.shifts[idx]
  }
  activeCell.value = cell
  activeCellDate.value = date
  activeCellShift.value = shift
}

function openUnscheduledDay(date: string) {
  // 整天未排班时点击：打开登记弹窗并锁定到该日，引导直接补排。
  selectedDate.value = date
  createOpen.value = true
}

function jumpToTable(shift: string) {
  // 从格子退回整表：保证被点击的班次处于展开状态，其它班次维持原状。
  expandedShifts.value = { ...expandedShifts.value, [shift]: true }
  activeTab.value = 'table'
}

function switchTab(key: TabKey) {
  activeTab.value = key
  if (key === 'table') void loadTable()
  if (key === 'roster' && !roster.value) void loadRoster(selectedDate.value)
}

function toggleShift(shift: string) {
  expandedShifts.value = { ...expandedShifts.value, [shift]: !expandedShifts.value[shift] }
}

function setAllExpanded(value: boolean) {
  const next: Record<string, boolean> = {}
  for (const shift of shiftOrder.value) next[shift] = value
  expandedShifts.value = next
}

async function onTableSearch(payload: { keyword: string; shift: string; date: string; includeVoid: boolean }) {
  errorMessage.value = ''
  const params = new URLSearchParams({ size: '500', include_void: String(payload.includeVoid) })
  if (payload.keyword) params.set('keyword', payload.keyword)
  if (payload.shift) params.set('shift', payload.shift)
  if (payload.date) params.set('date', payload.date)
  try {
    const response = await request(`${ENDPOINT}?${params.toString()}`)
    if (!response.ok) throw new Error('排班整表查询失败')
    tableRows.value = (await response.json()).items ?? []
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '排班整表查询失败'
  }
}

async function postAction(url: string, body: Record<string, unknown>): Promise<{ ok: boolean; message: string }> {
  const response = await request(url, { method: 'POST', body: JSON.stringify(body) })
  const payload = await response.json().catch(() => ({}))
  if (!response.ok || payload.ok === false) {
    return { ok: false, message: payload.message || '操作未生效' }
  }
  return { ok: true, message: payload.message || '操作已生效' }
}

async function onArrangeSubstitute(entryId: number, substitute: string) {
  busy.value = true
  const result = await postAction(`${ENDPOINT}/${entryId}/actions`, { action: '安排替班', 替班人员: substitute })
  busy.value = false
  if (!result.ok) {
    errorMessage.value = result.message
    return
  }
  activeCell.value = null
  await refreshAll()
}

async function onConfirmArrival(entryId: number) {
  busy.value = true
  const result = await postAction(`${ENDPOINT}/${entryId}/actions`, { action: '确认到岗' })
  busy.value = false
  if (!result.ok) {
    errorMessage.value = result.message
    return
  }
  activeCell.value = null
  await refreshAll()
}

async function onCellCreate(payload: CreatePayload) {
  busy.value = true
  const result = await postAction(ENDPOINT, payload)
  busy.value = false
  if (!result.ok) {
    errorMessage.value = result.message
    return
  }
  activeCell.value = null
  await refreshAll()
}

async function onCreate(payload: CreatePayload) {
  busy.value = true
  const result = await postAction(ENDPOINT, payload)
  busy.value = false
  if (!result.ok) {
    errorMessage.value = result.message
    return
  }
  createOpen.value = false
  selectedDate.value = payload.值班日期
  await refreshAll()
}

onMounted(async () => {
  await Promise.all([loadBoard(), loadMeta()])
  void loadRoster(selectedDate.value)
  void loadTable()
})
</script>

<style scoped>
.page-actions { display: flex; gap: 8px; }
.tabs { display: flex; gap: 4px; border-bottom: 1px solid var(--border); margin-bottom: 12px; }
.tab { border: none; background: none; padding: 8px 16px; font-size: 14px; color: var(--muted); cursor: pointer; border-bottom: 2px solid transparent; margin-bottom: -1px; }
.tab.active { color: var(--brand); border-bottom-color: var(--brand); font-weight: 600; }
</style>
