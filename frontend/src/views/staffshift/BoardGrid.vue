<template>
  <div class="board-wrap">
    <div class="board-toolbar">
      <div class="week-nav">
        <button class="btn" type="button" @click="$emit('prev-week')">← 上一周</button>
        <strong class="week-range">{{ board.weekStart }} ~ {{ board.weekEnd }}</strong>
        <button class="btn" type="button" @click="$emit('next-week')">下一周 →</button>
        <button class="btn ghost" type="button" @click="$emit('this-week')">回到本周</button>
      </div>
      <ul class="legend">
        <li><i class="dot covered"></i>已配齐当班/替班</li>
        <li><i class="dot substitute_missing"></i>替班缺失</li>
        <li><i class="dot gap"></i>无人顶岗</li>
        <li><i class="dot unscheduled"></i>整天未排班</li>
      </ul>
    </div>

    <div class="board-summary">
      <span class="chip warn">未排班 {{ board.summary.unscheduledDays }} 天</span>
      <span class="chip danger">缺口 {{ board.summary.gapCount }} 格</span>
      <span class="chip missing">替班缺失 {{ board.summary.substituteMissingCount }} 格</span>
      <span
        v-for="item in board.summary.byShift"
        :key="item.shift"
        class="chip"
      >
        {{ item.shift }}缺口 {{ item.gapCount }} · 缺替班 {{ item.substituteMissingCount }}
      </span>
    </div>

    <div class="board-scroll">
      <table class="board-table">
        <thead>
          <tr>
            <th class="shift-col">班次时段</th>
            <th v-for="day in board.days" :key="day.date" class="day-col">
              <div class="day-head">
                <span class="day-date">{{ day.date.slice(5) }}</span>
                <span class="day-weekday">{{ day.weekday }}</span>
                <span v-if="day.unscheduled" class="tag unscheduled">未排班</span>
                <span v-else class="day-gap" :class="{ danger: day.gapCount > 0 }">
                  缺口 {{ day.gapCount }}
                </span>
              </div>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(shiftRow, sIdx) in shiftRows" :key="shiftRow.shift">
            <th class="shift-col">
              <div class="shift-head">
                <span>{{ shiftRow.shift }}</span>
                <button class="link" type="button" @click="$emit('jump-table', shiftRow.shift)">
                  整表
                </button>
              </div>
            </th>
            <td
              v-for="(day, dIdx) in board.days"
              :key="day.date"
              class="day-cell"
              :class="{ 'day-unscheduled': day.unscheduled }"
            >
              <div v-if="day.unscheduled" class="unscheduled-block" @click="$emit('open-day', day.date)">
                <span class="unscheduled-mark">未排班</span>
              </div>
              <div v-else class="cell-group">
                <button
                  v-for="cell in day.shifts[sIdx].cells"
                  :key="cell.position"
                  type="button"
                  class="duty-cell"
                  :class="cell.state"
                  :title="cellTitle(cell)"
                  @click="$emit('open-cell', cell, day.date)"
                >
                  <span class="cell-position">{{ cell.position }}</span>
                  <span class="cell-primary">
                    <template v-if="cell.primary">{{ cell.primary }}</template>
                    <template v-else><i class="gap-mark">✕</i> 缺人</template>
                  </span>
                  <span class="cell-sub">
                    <i v-if="cell.state === 'substitute_missing'" class="sub-missing-mark">缺替班</i>
                    <template v-else-if="cell.substitute">替：{{ cell.substitute }}</template>
                  </span>
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

import type { BoardCell, BoardData } from './types'

const props = defineProps<{ board: BoardData }>()

defineEmits<{
  (e: 'prev-week'): void
  (e: 'next-week'): void
  (e: 'this-week'): void
  (e: 'open-cell', cell: BoardCell, date: string): void
  (e: 'open-day', date: string): void
  (e: 'jump-table', shift: string): void
}>()

// 每个班次时段铺成一行；行的顺序以后端下发的 shifts 为准。
const shiftRows = computed<{ shift: string }[]>(() => props.board.shifts.map((name) => ({ shift: name })))

function cellTitle(cell: BoardCell): string {
  if (cell.state === 'gap') return `${cell.position}：无人顶岗，点击安排替班`
  if (cell.state === 'substitute_missing') return `${cell.position}：当班 ${cell.primary}，替班缺失`
  return `${cell.position}：当班 ${cell.primary}，替班 ${cell.substitute}`
}
</script>

<style scoped>
.board-wrap { display: flex; flex-direction: column; gap: 10px; }
.board-toolbar { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; }
.week-nav { display: flex; align-items: center; gap: 8px; }
.week-range { font-size: 14px; }
.legend { display: flex; gap: 14px; list-style: none; margin: 0; padding: 0; font-size: 12px; color: var(--muted); }
.dot { display: inline-block; width: 10px; height: 10px; border-radius: 3px; margin-right: 4px; vertical-align: -1px; }
.dot.covered { background: #e6f4ea; border: 1px solid #34a853; }
.dot.substitute_missing { background: #fdeecd; border: 1px solid #e8a33d; }
.dot.gap { background: #fbe0e0; border: 1px solid #d92d20; }
.dot.unscheduled { background: #eef0f3; border: 1px solid #98a2b3; }

.board-summary { display: flex; flex-wrap: wrap; gap: 8px; }
.chip { font-size: 12px; border: 1px solid var(--border); background: #fff; border-radius: 999px; padding: 2px 10px; color: var(--muted); }
.chip.warn { background: #eef0f3; border-color: #98a2b3; color: #475467; }
.chip.danger { background: #fef3f2; border-color: #f0a8a0; color: #b42318; }
.chip.missing { background: #fffaeb; border-color: #e8b960; color: #b54708; }

.board-scroll { overflow-x: auto; border: 1px solid var(--border); border-radius: 8px; background: #fff; }
.board-table { border-collapse: collapse; min-width: 100%; }
.board-table th, .board-table td { border: 1px solid var(--border); padding: 0; vertical-align: top; }
.shift-col { width: 92px; min-width: 92px; background: #f8fafc; padding: 8px; }
.day-col { min-width: 158px; padding: 6px; background: #f8fafc; }
.day-head { display: flex; flex-direction: column; align-items: center; gap: 2px; }
.day-date { font-weight: 600; font-size: 13px; }
.day-weekday { font-size: 12px; color: var(--muted); }
.day-gap { font-size: 11px; color: #34a853; }
.day-gap.danger { color: #b42318; }
.tag { font-size: 11px; border-radius: 4px; padding: 1px 6px; }
.tag.unscheduled { background: #eef0f3; color: #475467; }
.shift-head { display: flex; flex-direction: column; gap: 4px; align-items: flex-start; font-size: 13px; }

.day-cell.unscheduled { background: repeating-linear-gradient(45deg, #f3f4f6, #f3f4f6 8px, #eef0f3 8px, #eef0f3 16px); }
.unscheduled-block { min-height: 118px; display: flex; align-items: center; justify-content: center; cursor: pointer; }
.unscheduled-mark { font-size: 12px; color: #667085; border: 1px dashed #98a2b3; border-radius: 6px; padding: 4px 10px; background: rgba(255,255,255,.7); }

.cell-group { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; padding: 6px; }
.duty-cell { text-align: left; border-radius: 6px; border: 1px solid var(--border); background: #fff; padding: 5px 6px; cursor: pointer; min-width: 0; }
.duty-cell:hover { outline: 2px solid rgba(31,111,235,.25); }
.cell-position { display: block; font-size: 10px; color: var(--muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.cell-primary { display: block; font-size: 12px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.cell-sub { display: block; font-size: 10px; color: var(--muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; min-height: 13px; }

.duty-cell.covered { background: #f0f9f2; border-color: #9bd8b0; }
.duty-cell.substitute_missing { background: #fffaeb; border-color: #e8b960; }
.duty-cell.gap { background: #fef3f2; border-color: #f0a8a0; }
.gap-mark { color: #d92d20; font-style: normal; font-weight: 700; }
.sub-missing-mark { color: #b54708; font-style: normal; font-weight: 600; }
</style>
