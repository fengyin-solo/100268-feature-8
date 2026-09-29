<template>
  <div v-if="open" class="modal-mask" @click.self="$emit('close')">
    <div class="modal">
      <header class="modal-head">
        <h3>{{ cell.position }} · {{ shift }} · {{ date }}</h3>
        <button class="link" type="button" @click="$emit('close')">关闭</button>
      </header>

      <div class="modal-body">
        <div class="state-line" :class="cell.state">
          <template v-if="cell.state === 'gap'">该岗位此时段无人顶岗，是一个缺口。</template>
          <template v-else-if="cell.state === 'substitute_missing'">当班人已排，但替班人员缺失。</template>
          <template v-else-if="cell.state === 'unscheduled'">这一天尚未排班。</template>
          <template v-else>当班人与替班都已安排到位。</template>
        </div>

        <dl class="detail-grid">
          <div><dt>当班人</dt><dd>{{ cell.primary || '—' }}</dd></div>
          <div><dt>替班人员</dt><dd :class="{ missing: !cell.substitute }">{{ cell.substitute || '（缺失）' }}</dd></div>
          <div><dt>到岗确认</dt><dd>{{ cell.checked ? '已到岗' : '未到岗' }}</dd></div>
          <div><dt>排班状态</dt><dd>{{ cell.status || '—' }}</dd></div>
        </dl>

        <section v-if="cell.entryId" class="sub-plan">
          <h4>替班安排</h4>
          <div class="inline-form">
            <input v-model="substitute" placeholder="输入替班人员姓名" @keyup.enter="submitSubstitute" />
            <button class="btn primary" type="button" :disabled="busy" @click="submitSubstitute">安排替班</button>
            <button class="btn" type="button" :disabled="busy || cell.checked" @click="confirmArrival">
              确认到岗
            </button>
          </div>
        </section>

        <section v-else class="sub-plan">
          <h4>该格尚无排班，直接补排</h4>
          <div class="inline-form wrap">
            <input v-model="formPrimary" placeholder="当班人姓名" />
            <input v-model="formSubstitute" placeholder="替班人员（可后补）" />
            <button class="btn primary" type="button" :disabled="busy" @click="submitCreate">登记此格排班</button>
          </div>
          <p class="hint">同一岗位同一时段若已有旧排班，保存后旧排班自动作废，以本次为准。</p>
        </section>

        <p v-if="error" class="error-text">{{ error }}</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'

import type { BoardCell } from './types'

const props = defineProps<{
  open: boolean
  cell: BoardCell
  date: string
  shift: string
  busy: boolean
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'arrange-substitute', entryId: number, substitute: string): void
  (e: 'confirm-arrival', entryId: number): void
  (e: 'create', payload: { 岗位名称: string; 值班日期: string; 班次时段: string; 值班人员: string; 替班人员: string }): void
}>()

const substitute = ref('')
const formPrimary = ref('')
const formSubstitute = ref('')
const error = ref('')

watch(() => props.cell, (cell) => {
  substitute.value = cell.substitute || ''
  formPrimary.value = cell.primary || ''
  formSubstitute.value = cell.substitute || ''
  error.value = ''
}, { immediate: true })

function submitSubstitute() {
  error.value = ''
  if (!substitute.value.trim()) {
    error.value = '请填写替班人员姓名'
    return
  }
  if (props.cell.entryId == null) return
  emit('arrange-substitute', props.cell.entryId, substitute.value.trim())
}

function confirmArrival() {
  error.value = ''
  if (props.cell.entryId == null) return
  emit('confirm-arrival', props.cell.entryId)
}

function submitCreate() {
  error.value = ''
  if (!formPrimary.value.trim()) {
    error.value = '请填写当班人姓名'
    return
  }
  emit('create', {
    岗位名称: props.cell.position,
    值班日期: props.date,
    班次时段: props.shift,
    值班人员: formPrimary.value.trim(),
    替班人员: formSubstitute.value.trim(),
  })
}
</script>

<style scoped>
.modal-mask { position: fixed; inset: 0; background: rgba(16, 24, 40, .45); display: flex; align-items: center; justify-content: center; z-index: 50; }
.modal { width: 520px; max-width: calc(100vw - 32px); background: #fff; border-radius: 10px; overflow: hidden; }
.modal-head { display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; border-bottom: 1px solid var(--border); }
.modal-head h3 { margin: 0; font-size: 15px; }
.modal-body { padding: 14px 16px; }
.state-line { font-size: 13px; border-radius: 6px; padding: 8px 10px; margin-bottom: 12px; }
.state-line.covered { background: #f0f9f2; color: #1d6b3a; }
.state-line.substitute_missing { background: #fffaeb; color: #b54708; }
.state-line.gap, .state-line.unscheduled { background: #fef3f2; color: #b42318; }
.detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px 16px; margin: 0 0 12px; }
.detail-grid dt { font-size: 12px; color: var(--muted); }
.detail-grid dd { margin: 2px 0 0; font-size: 13px; }
.detail-grid dd.missing { color: #b54708; font-weight: 600; }
.sub-plan h4 { margin: 0 0 8px; font-size: 13px; }
.inline-form { display: flex; gap: 8px; }
.inline-form.wrap { flex-wrap: wrap; }
.inline-form input { flex: 1; min-width: 140px; border: 1px solid var(--border); border-radius: 6px; padding: 6px 8px; font-size: 13px; }
.hint { font-size: 12px; color: var(--muted); margin: 6px 0 0; }
</style>
