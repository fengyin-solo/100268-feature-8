<template>
  <div v-if="open" class="modal-mask" @click.self="$emit('close')">
    <div class="modal">
      <header class="modal-head">
        <h3>登记排班</h3>
        <button class="link" type="button" @click="$emit('close')">关闭</button>
      </header>
      <form class="modal-body" @submit.prevent="submit">
        <label class="form-item">
          <span>岗位名称 *</span>
          <select v-model="form.岗位名称">
            <option value="" disabled>请选择岗位</option>
            <option v-for="p in positions" :key="p" :value="p">{{ p }}</option>
          </select>
        </label>
        <label class="form-item">
          <span>值班日期 *</span>
          <input v-model="form.值班日期" type="date" />
        </label>
        <label class="form-item">
          <span>班次时段 *</span>
          <select v-model="form.班次时段">
            <option value="" disabled>请选择班次</option>
            <option v-for="s in shifts" :key="s" :value="s">{{ s }}</option>
          </select>
        </label>
        <label class="form-item">
          <span>当班人 *</span>
          <input v-model="form.值班人员" placeholder="当班人姓名" list="roster-names" />
          <datalist id="roster-names">
            <option v-for="m in rosterNames" :key="m" :value="m" />
          </datalist>
        </label>
        <label class="form-item">
          <span>替班人员</span>
          <input v-model="form.替班人员" placeholder="可先不填，稍后在格子里补" list="roster-names" />
        </label>
        <p class="hint">同岗位、同日期、同班次重复登记时，以本次为准，前一次自动作废。</p>
        <p v-if="error" class="error-text">{{ error }}</p>
        <div class="form-actions">
          <button class="btn" type="button" @click="$emit('close')">取消</button>
          <button class="btn primary" type="submit" :disabled="busy">保存排班</button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, watch } from 'vue'

export interface CreatePayload {
  岗位名称: string
  值班日期: string
  班次时段: string
  值班人员: string
  替班人员: string
  [key: string]: string
}

const props = defineProps<{
  open: boolean
  positions: string[]
  shifts: string[]
  rosterNames: string[]
  defaultDate: string
  busy: boolean
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'submit', payload: CreatePayload): void
}>()

const form = reactive<CreatePayload>({
  岗位名称: '',
  值班日期: '',
  班次时段: '',
  值班人员: '',
  替班人员: '',
})
const error = ref('')

watch(() => props.open, (open) => {
  if (open) {
    form.值班日期 = props.defaultDate
    form.岗位名称 = props.positions[0] ?? ''
    form.班次时段 = props.shifts[0] ?? ''
    form.值班人员 = ''
    form.替班人员 = ''
  }
})

function submit() {
  if (!form.岗位名称 || !form.值班日期 || !form.班次时段 || !form.值班人员.trim()) {
    return
  }
  emit('submit', { ...form, 值班人员: form.值班人员.trim(), 替班人员: form.替班人员.trim() })
}
</script>

<style scoped>
.modal-mask { position: fixed; inset: 0; background: rgba(16,24,40,.45); display: flex; align-items: center; justify-content: center; z-index: 50; }
.modal { width: 460px; max-width: calc(100vw - 32px); background: #fff; border-radius: 10px; overflow: hidden; }
.modal-head { display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; border-bottom: 1px solid var(--border); }
.modal-head h3 { margin: 0; font-size: 15px; }
.modal-body { padding: 14px 16px; display: flex; flex-direction: column; gap: 10px; }
.form-item span { display: block; font-size: 12px; color: var(--muted); margin-bottom: 3px; }
.form-item input, .form-item select { width: 100%; border: 1px solid var(--border); border-radius: 6px; padding: 7px 9px; font-size: 13px; }
.hint { font-size: 12px; color: var(--muted); margin: 0; }
.form-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 4px; }
</style>
