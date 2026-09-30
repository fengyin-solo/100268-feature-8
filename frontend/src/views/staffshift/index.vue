<template>
  <section class="page" data-module="staffshift">
    <header class="page-head">
      <div>
        <h2>人员排班管理</h2>
        <p class="page-desc">值班看板按班次铺格子直观看缺口；班组台账与看板读到的是同一份有效排班。</p>
      </div>
      <div class="page-actions">
        <button class="btn primary" type="button" @click="openCreate">登记排班记录</button>
        <button class="btn" type="button" @click="exportRows">导出人员排班清单</button>
      </div>
    </header>

    <div class="tab-bar">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        class="tab-btn"
        :class="{ active: activeTab === tab.key }"
        type="button"
        @click="switchTab(tab.key)"
      >
        {{ tab.label }}
      </button>
    </div>

    <!-- 视图一：值班看板 -->
    <div v-show="activeTab === 'board'" class="board-view">
      <div class="week-bar">
        <button class="btn" type="button" @click="shiftWeek(-1)">上一周</button>
        <strong>{{ board?.weekStart }} ~ {{ board?.weekEnd }}</strong>
        <button class="btn" type="button" @click="shiftWeek(1)">下一周</button>
        <button class="btn ghost" type="button" @click="backToCurrentWeek">回到本周</button>
        <span class="week-tip">
          本周缺口 {{ board?.缺口总数 ?? 0 }} 个 · 缺替班 {{ board?.缺替班总数 ?? 0 }} 个 ·
          未排班 {{ board?.未排班日期.length ?? 0 }} 天
        </span>
      </div>

      <div class="board-grid-wrap">
        <table class="board-grid">
          <thead>
            <tr>
              <th class="slot-col">班次时段</th>
              <th v-for="day in board?.days ?? []" :key="day.日期" class="day-col">
                <span class="day-week">{{ day.星期 }}</span>
                <span class="day-date">{{ day.日期.slice(5) }}</span>
                <span v-if="day.未排班" class="tag tag-unscheduled">未排班</span>
                <span v-else-if="day.缺口数 > 0" class="tag tag-gap">缺 {{ day.缺口数 }}</span>
                <span v-else class="tag tag-ok">满岗</span>
              </th>
            </tr>
          </thead>
          <tbody>
            <template v-for="slot in board?.slots ?? []" :key="slot">
              <tr class="slot-row" @click="toggleSlotExpand(slot)">
                <td class="slot-col">
                  <span class="caret">{{ expandedSlots.has(slot) ? '▾' : '▸' }}</span>
                  {{ slot }}
                  <span class="slot-gap">本周缺口 {{ slotGap(slot) }}</span>
                </td>
                <td v-for="day in board?.days ?? []" :key="day.日期" class="cell-td">
                  <div v-if="day.未排班" class="day-cell cell-unscheduled">
                    <span class="cell-mark">未排班</span>
                  </div>
                  <template v-else>
                    <div
                      v-for="cell in slotCells(day, slot)"
                      :key="cell.岗位名称"
                      class="post-cell"
                      :class="cellClass(cell)"
                      role="button"
                      tabindex="0"
                      @click.stop="openCell(cell, day, slot)"
                      @keydown.enter.stop="openCell(cell, day, slot)"
                    >
                      <span class="post-name">{{ cell.岗位名称 }}</span>
                      <template v-if="cell.state === 'gap'">
                        <span class="cell-mark">✕ 缺口</span>
                      </template>
                      <template v-else-if="cell.state === 'unscheduled'">
                        <span class="cell-mark">未排班</span>
                      </template>
                      <template v-else>
                        <span class="person-name">{{ cell.值班人员 }}</span>
                        <span v-if="cell.缺替班" class="sub-warn">替班缺失</span>
                        <span v-else class="sub-ok">替：{{ cell.替班人员 }}</span>
                      </template>
                    </div>
                  </template>
                </td>
              </tr>
              <tr v-if="expandedSlots.has(slot)" class="slot-detail-row">
                <td class="slot-col detail-label">替班安排明细</td>
                <td v-for="day in board?.days ?? []" :key="day.日期" class="cell-td detail-td">
                  <div v-if="day.未排班" class="mini-empty">整天未排班</div>
                  <template v-else>
                    <div
                      v-for="cell in slotCells(day, slot)"
                      :key="cell.岗位名称"
                      class="mini-line"
                      :class="cellClass(cell)"
                    >
                      <span>{{ cell.岗位名称 }}：</span>
                      <template v-if="cell.state === 'gap'"><b>无人顶上</b></template>
                      <template v-else-if="cell.state === 'unscheduled'">未排班</template>
                      <template v-else>
                        <b>{{ cell.值班人员 }}</b>
                        <span v-if="cell.替班人员"> / 替班 {{ cell.替班人员 }}</span>
                        <span v-else class="sub-warn"> / 替班未定</span>
                      </template>
                    </div>
                  </template>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
      <p class="board-legend">
        图例：<span class="tag tag-ok">满岗</span>
        <span class="tag tag-gap">岗位缺口</span>
        <span class="tag tag-sub">替班缺失</span>
        <span class="tag tag-unscheduled">未排班</span>
        点击格子可查看该岗位的替班安排；班次行可展开收起，切到整表再切回时保持展开。
      </p>
    </div>

    <!-- 视图二：班组台账 -->
    <div v-show="activeTab === 'roster'" class="roster-view">
      <div class="week-bar">
        <label class="filter-item">
          <span>台账日期</span>
          <input v-model="rosterDate" type="date" @change="loadRoster" />
        </label>
        <button class="btn" type="button" @click="loadRoster">刷新台账</button>
        <span class="week-tip">
          台账在岗人与看板格子同源，都来自同一份有效排班
        </span>
      </div>

      <div v-if="roster?.未排班" class="unscheduled-banner">
        {{ roster.日期 }} 当天未排班，按未排班呈现（在岗人数不记为 0 个缺口）。
      </div>

      <div class="stat-row">
        <article class="stat-card">
          <span class="stat-label">当天在岗总人数</span>
          <strong class="stat-value">{{ roster?.未排班 ? '未排班' : roster?.在岗总人数 ?? 0 }}</strong>
        </article>
        <article v-for="slot in roster?.班次 ?? []" :key="slot.班次时段" class="stat-card">
          <span class="stat-label">{{ slot.班次时段 }}在岗</span>
          <strong class="stat-value">{{ roster?.未排班 ? '未排班' : slot.在岗人数 }}</strong>
        </article>
      </div>

      <table class="data-table roster-table">
        <thead>
          <tr><th>班次时段</th><th>岗位名称</th><th>值班人员</th><th>替班人员</th><th>到岗确认</th><th>排班状态</th></tr>
        </thead>
        <tbody>
          <template v-for="slot in roster?.班次 ?? []" :key="slot.班次时段">
            <tr v-if="!roster?.未排班 && slot.成员.length">
              <td colspan="6" class="roster-slot-head" @click="toggleSlotExpand(slot.班次时段)">
                <span class="caret">{{ expandedSlots.has(slot.班次时段) ? '▾' : '▸' }}</span>
                {{ slot.班次时段 }}（{{ slot.成员.length }} 人在岗）
              </td>
            </tr>
            <template v-if="!roster?.未排班 && expandedSlots.has(slot.班次时段)">
              <tr v-for="member in slot.成员" :key="member.entry_id">
                <td>{{ slot.班次时段 }}</td>
                <td>{{ member.岗位名称 }}</td>
                <td>{{ member.值班人员 }}</td>
                <td>
                  <span v-if="!member.替班人员" class="sub-warn">替班缺失</span>
                  <span v-else>{{ member.替班人员 }}</span>
                </td>
                <td>{{ member.到岗确认 }}</td>
                <td>
                  {{ member.排班状态 }}
                  <button class="link" type="button" @click="openEntry(member.entry_id)">安排替班</button>
                </td>
              </tr>
            </template>
          </template>
          <tr v-if="roster?.未排班">
            <td colspan="6" class="empty-state">{{ roster.日期 }} 当天未排班</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 视图三：排班整表 -->
    <div v-show="activeTab === 'table'" class="table-view">
      <div class="stat-row">
        <article v-for="item in stats" :key="item.label" class="stat-card">
          <span class="stat-label">{{ item.label }}</span>
          <strong class="stat-value">{{ item.value }}</strong>
        </article>
      </div>

      <form class="filter-bar" @submit.prevent="reloadTable">
        <label class="filter-item">
          <span>排班编号</span>
          <input v-model="filters.keyword" placeholder="按排班编号检索" />
        </label>
        <label class="filter-item">
          <span>排班状态</span>
          <select v-model="filters.status">
            <option value="">全部</option>
            <option v-for="s in allStatuses" :key="s" :value="s">{{ s }}</option>
          </select>
        </label>
        <button class="btn" type="submit">查询</button>
        <button class="btn ghost" type="button" @click="resetFilters">重置条件</button>
      </form>

      <table class="data-table">
        <thead>
          <tr>
            <th v-for="column in columns" :key="column">{{ column }}</th>
            <th>可执行动作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="String(row.id)" :class="{ 'row-voided': row.voided }">
            <td v-for="column in columns" :key="column">
              <template v-if="column === '排班状态'">
                {{ row[column] ?? '—' }}
                <span v-if="row.voided" class="void-hint">（已作废：{{ row['作废原因'] }}）</span>
              </template>
              <template v-else>{{ row[column] || '—' }}</template>
            </td>
            <td class="row-actions">
              <button class="link" type="button" @click="openEntry(Number(row.id))">替班安排</button>
              <button
                v-for="action in ['确认排班', '申请调班']"
                :key="action"
                class="link"
                type="button"
                :disabled="Boolean(row.voided)"
                @click="runAction(action, row)"
              >
                {{ action }}
              </button>
            </td>
          </tr>
          <tr v-if="!rows.length">
            <td :colspan="columns.length + 1" class="empty-state">暂无人员排班数据，可先登记排班记录</td>
          </tr>
        </tbody>
      </table>

      <footer class="page-foot">
        <span>共 {{ total }} 条人员排班记录</span>
        <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
      </footer>
    </div>

    <!-- 格子详情 / 替班安排抽屉 -->
    <div v-if="detail.open" class="drawer-mask" @click.self="closeDetail">
      <aside class="drawer">
        <header class="drawer-head">
          <h3>岗位替班安排</h3>
          <button class="btn ghost" type="button" @click="closeDetail">关闭</button>
        </header>

        <template v-if="detail.cell">
          <dl class="detail-list">
            <div><dt>值班日期</dt><dd>{{ detail.date }}（{{ detail.weekday }}）</dd></div>
            <div><dt>班次时段</dt><dd>{{ detail.slot }}</dd></div>
            <div><dt>岗位名称</dt><dd>{{ detail.cell.岗位名称 }}</dd></div>
            <template v-if="detail.cell?.state === 'gap'">
              <div class="detail-alert">该岗位此时段无人顶上，属于岗位缺口，可立即登记排班补位。</div>
            </template>
            <template v-else-if="detail.cell?.state === 'unscheduled'">
              <div class="detail-alert muted">此时段尚未排班。</div>
            </template>
            <template v-else>
              <div><dt>当班人员</dt><dd>{{ detail.cell?.值班人员 }}</dd></div>
              <div><dt>替班人员</dt>
                <dd>
                  <span v-if="detail.cell?.替班人员">{{ detail.cell?.替班人员 }}</span>
                  <span v-else class="sub-warn">替班人员缺失，需尽快安排</span>
                </dd>
              </div>
              <div><dt>到岗确认</dt><dd>{{ detail.cell?.到岗确认 || '—' }}</dd></div>
              <div><dt>排班状态</dt><dd>{{ detail.cell?.排班状态 }}</dd></div>
              <div><dt>排班编号</dt><dd>{{ detail.cell?.排班编号 }}</dd></div>
            </template>
          </dl>

          <div v-if="detail.cell?.entry_id" class="drawer-actions">
            <input v-model="substituteName" placeholder="输入替班人员姓名" />
            <button class="btn primary" type="button" @click="submitSubstitute(detail.cell!.entry_id!)">
              安排替班
            </button>
            <button class="btn" type="button" @click="runActionById('确认排班', detail.cell!.entry_id!)">
              确认排班
            </button>
          </div>
          <div v-else class="drawer-actions">
            <button class="btn primary" type="button" @click="fillCreateFromCell">为该缺口登记排班</button>
          </div>
        </template>
      </aside>
    </div>

    <!-- 登记排班抽屉 -->
    <div v-if="createOpen" class="drawer-mask" @click.self="createOpen = false">
      <aside class="drawer">
        <header class="drawer-head">
          <h3>登记排班记录</h3>
          <button class="btn ghost" type="button" @click="createOpen = false">关闭</button>
        </header>
        <form class="create-form" @submit.prevent="submitCreate">
          <label v-for="field in createFields" :key="field.key" class="filter-item">
            <span>{{ field.label }}{{ field.required ? ' *' : '' }}</span>
            <template v-if="field.options">
              <select v-model="createForm[field.key]">
                <option value="" disabled>请选择</option>
                <option v-for="opt in field.options" :key="opt" :value="opt">{{ opt }}</option>
              </select>
            </template>
            <input v-else v-model="createForm[field.key]" :type="field.type ?? 'text'" />
          </label>
          <p class="form-tip">同一岗位同一天同一班次再次登记时，前一次排班自动作废，以最后一次为准。</p>
          <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>
          <div class="drawer-actions">
            <button class="btn primary" type="submit">提交排班</button>
          </div>
        </form>
      </aside>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'

import { request } from '@/api/client'

type Cell = {
  岗位名称: string
  state: 'covered' | 'missing-substitute' | 'gap' | 'unscheduled'
  值班人员: string
  替班人员: string
  缺口: boolean
  缺替班: boolean
  已排班: boolean
  entry_id: number | null
  排班编号: string
  排班状态?: string
  到岗确认?: string
}

type Board = {
  weekStart: string
  weekEnd: string
  slots: string[]
  posts: string[]
  days: {
    日期: string
    星期: string
    未排班: boolean
    缺口数: number
    班次: { 班次时段: string; 已排班: boolean; 格子: Cell[] }[]
  }[]
  缺口: { 班次时段: string; 缺口数: number }[]
  缺口总数: number
  缺替班总数: number
  未排班日期: string[]
}

type Roster = {
  日期: string
  未排班: boolean
  在岗总人数: number
  班次: {
    班次时段: string
    在岗人数: number
    成员: {
      排班编号: string
      岗位名称: string
      值班人员: string
      替班人员: string
      到岗确认: string
      排班状态: string
      缺替班: boolean
      entry_id: number
    }[]
  }[]
}

type Row = Record<string, string | number | boolean | null>

const ENDPOINT = '/api/staffshift'
const columns = ['排班编号', '岗位名称', '值班人员', '值班日期', '班次时段', '替班人员', '到岗确认', '排班状态']
const allStatuses = ['待确认', '已确认', '已替班', '已调班', '已作废']

const tabs = [
  { key: 'board', label: '值班看板' },
  { key: 'roster', label: '班组台账' },
  { key: 'table', label: '排班整表' },
] as const
type TabKey = (typeof tabs)[number]['key']

const activeTab = ref<TabKey>('board')
const board = ref<Board | null>(null)
const roster = ref<Roster | null>(null)
const rosterDate = ref('2026-09-30')
const weekStart = ref('2026-09-28')
// 看板与整表共用展开状态：从格子退回整表时已展开班次不收回去
const expandedSlots = reactive(new Set<string>(['早班', '中班', '夜班']))

const rows = ref<Row[]>([])
const total = ref(0)
const errorMessage = ref('')
const filters = ref<{ keyword: string; status: string }>({ keyword: '', status: '' })
const stats = ref([
  { label: '本周岗位缺口', value: 0 },
  { label: '替班缺失格子', value: 0 },
  { label: '待确认班次', value: 0 },
  { label: '已作废记录', value: 0 },
])

const detail = reactive({
  open: false,
  cell: null as Cell | null,
  date: '',
  weekday: '',
  slot: '',
})
const substituteName = ref('')

const createOpen = ref(false)
const createFields = [
  { key: '岗位名称', label: '岗位名称', required: true, options: ['机坪调度', '航班协调', '廊桥监管', '装卸队长'] },
  { key: '值班日期', label: '值班日期', required: true, type: 'date' },
  { key: '班次时段', label: '班次时段', required: true, options: ['早班', '中班', '夜班'] },
  { key: '值班人员', label: '值班人员', required: true },
  { key: '替班人员', label: '替班人员', required: false },
  { key: '到岗确认', label: '到岗确认', required: false, options: ['未到岗', '已到岗'] },
]
const createForm = ref<Record<string, string>>({
  岗位名称: '',
  值班日期: '',
  班次时段: '',
  值班人员: '',
  替班人员: '',
  到岗确认: '未到岗',
})

// ---------- 数据加载 ----------
async function loadBoard() {
  const payload = await fetchJsonSafe<Board>(`${ENDPOINT}/board?week_start=${encodeURIComponent(weekStart.value)}`)
  if (payload) {
    board.value = payload
    weekStart.value = payload.weekStart
    stats.value[0].value = payload.缺口总数
    stats.value[1].value = payload.缺替班总数
  }
}

async function loadRoster() {
  const payload = await fetchJsonSafe<Roster>(`${ENDPOINT}/roster?date=${encodeURIComponent(rosterDate.value)}`)
  if (payload) {
    roster.value = payload
    // 台账默认展开当天有在岗人的班次
    payload.班次.forEach((slot) => {
      if (slot.成员.length) expandedSlots.add(slot.班次时段)
    })
  }
}

async function reloadTable() {
  errorMessage.value = ''
  const query = new URLSearchParams()
  if (filters.value.keyword) query.set('keyword', filters.value.keyword)
  if (filters.value.status) query.set('status', filters.value.status)
  try {
    const response = await request(`${ENDPOINT}?${query.toString()}&size=200`)
    if (!response.ok) throw new Error('排班记录列表读取失败')
    const payload = await response.json()
    rows.value = (payload.items ?? []) as Row[]
    total.value = payload.total ?? rows.value.length
    stats.value[2].value = rows.value.filter((r) => r.status === '待确认').length
    stats.value[3].value = rows.value.filter((r) => r.voided).length
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '人员排班列表读取失败'
  }
}

async function fetchJsonSafe<T>(path: string): Promise<T | null> {
  errorMessage.value = ''
  try {
    const response = await request(path)
    if (!response.ok) throw new Error(`接口返回 ${response.status}`)
    return (await response.json()) as T
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '排班数据读取失败'
    return null
  }
}

async function reloadAll() {
  await Promise.all([loadBoard(), loadRoster(), reloadTable()])
}

// ---------- 看板交互 ----------
function switchTab(key: TabKey) {
  activeTab.value = key
  if (key === 'roster' && !roster.value) void loadRoster()
  if (key === 'table') void reloadTable()
}

function shiftWeek(delta: number) {
  const base = new Date(`${weekStart.value}T00:00:00`)
  base.setDate(base.getDate() + delta * 7)
  const y = base.getFullYear()
  const m = String(base.getMonth() + 1).padStart(2, '0')
  const d = String(base.getDate()).padStart(2, '0')
  weekStart.value = `${y}-${m}-${d}`
  void loadBoard()
}

function backToCurrentWeek() {
  weekStart.value = '2026-09-28'
  void loadBoard()
}

function slotCells(day: Board['days'][number], slot: string): Cell[] {
  return day.班次.find((item) => item.班次时段 === slot)?.格子 ?? []
}

function slotGap(slot: string): number {
  return board.value?.缺口.find((item) => item.班次时段 === slot)?.缺口数 ?? 0
}

function toggleSlotExpand(slot: string) {
  if (expandedSlots.has(slot)) expandedSlots.delete(slot)
  else expandedSlots.add(slot)
}

function cellClass(cell: Cell): Record<string, boolean> {
  return {
    'cell-covered': cell.state === 'covered',
    'cell-gap': cell.state === 'gap',
    'cell-sub-missing': cell.state === 'missing-substitute',
    'cell-unscheduled': cell.state === 'unscheduled',
  }
}

function openCell(cell: Cell, day: Board['days'][number], slot: string) {
  detail.open = true
  detail.cell = cell
  detail.date = day.日期
  detail.weekday = day.星期
  detail.slot = slot
  substituteName.value = cell.替班人员
}

async function openEntry(entryId: number) {
  try {
    const response = await request(`${ENDPOINT}/${entryId}`)
    if (!response.ok) throw new Error('排班明细读取失败')
    const entry = (await response.json()) as Row
    const cell: Cell = {
      岗位名称: String(entry['岗位名称'] ?? ''),
      state: entry['替班人员'] ? 'covered' : 'missing-substitute',
      值班人员: String(entry['值班人员'] ?? ''),
      替班人员: String(entry['替班人员'] ?? ''),
      缺口: false,
      缺替班: !entry['替班人员'],
      已排班: true,
      entry_id: Number(entry.id),
      排班编号: String(entry['排班编号'] ?? ''),
      排班状态: String(entry['排班状态'] ?? entry.status ?? ''),
      到岗确认: String(entry['到岗确认'] ?? ''),
    }
    detail.open = true
    detail.cell = cell
    detail.date = String(entry['值班日期'] ?? '')
    detail.weekday = ''
    detail.slot = String(entry['班次时段'] ?? '')
    substituteName.value = cell.替班人员
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '排班明细读取失败'
  }
}

function closeDetail() {
  detail.open = false
  detail.cell = null
}

function fillCreateFromCell() {
  createForm.value.值班日期 = detail.date
  createForm.value.班次时段 = detail.slot
  createForm.value.岗位名称 = detail.cell?.岗位名称 ?? ''
  closeDetail()
  createOpen.value = true
}

// ---------- 动作 ----------
async function submitSubstitute(entryId: number) {
  errorMessage.value = ''
  if (!substituteName.value.trim()) {
    errorMessage.value = '请填写替班人员姓名'
    return
  }
  try {
    const response = await request(`${ENDPOINT}/${entryId}/actions`, {
      method: 'POST',
      body: JSON.stringify({ values: { action: '安排替班', 替班人员: substituteName.value.trim() } }),
    })
    const payload = (await response.json()) as { ok: boolean; message: string }
    if (!response.ok || !payload.ok) throw new Error(payload.message || '替班安排未生效')
    closeDetail()
    await reloadAll()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '替班安排失败'
  }
}

async function runActionById(action: string, entryId: number) {
  try {
    const response = await request(`${ENDPOINT}/${entryId}/actions`, {
      method: 'POST',
      body: JSON.stringify({ values: { action } }),
    })
    const payload = (await response.json()) as { ok: boolean; message: string }
    if (!response.ok || !payload.ok) throw new Error(payload.message)
    closeDetail()
    await reloadAll()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '排班操作失败'
  }
}

async function runAction(action: string, row: Row) {
  if (action === '安排替班') {
    await openEntry(Number(row.id))
    return
  }
  await runActionById(action, Number(row.id))
}

// ---------- 登记 ----------
function openCreate() {
  createForm.value = {
    岗位名称: '',
    值班日期: rosterDate.value,
    班次时段: '早班',
    值班人员: '',
    替班人员: '',
    到岗确认: '未到岗',
  }
  createOpen.value = true
}

async function submitCreate() {
  errorMessage.value = ''
  try {
    const response = await request(ENDPOINT, {
      method: 'POST',
      body: JSON.stringify({ values: { ...createForm.value } }),
    })
    const payload = (await response.json()) as { ok: boolean; message: string }
    if (!response.ok || !payload.ok) throw new Error(payload.message)
    createOpen.value = false
    await reloadAll()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '排班登记失败'
  }
}

function resetFilters() {
  filters.value = { keyword: '', status: '' }
  void reloadTable()
}

function exportRows() {
  window.open(`${ENDPOINT}/export`, '_blank')
}

onMounted(() => {
  void reloadAll()
})
</script>
