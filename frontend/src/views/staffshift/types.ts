/** 值班看板、排班整表、班组台账共用的接口类型。 */

export interface BoardCell {
  position: string
  /** covered 已配齐；substitute_missing 有当班人但缺替班；gap 无人顶岗；unscheduled 整天未排班 */
  state: 'covered' | 'substitute_missing' | 'gap' | 'unscheduled'
  entryId: number | null
  primary: string
  substitute: string
  checked: boolean
  status: string | null
}

export interface BoardShift {
  shift: string
  cells: BoardCell[]
  gapCount: number
  substituteMissingCount: number
  onDutyCount: number | null
}

export interface BoardDay {
  date: string
  weekday: string
  unscheduled: boolean
  shifts: BoardShift[]
  gapCount: number
  substituteMissingCount: number
}

export interface BoardSummary {
  unscheduledDays: number
  gapCount: number
  substituteMissingCount: number
  byShift: { shift: string; gapCount: number; substituteMissingCount: number }[]
}

export interface BoardData {
  weekStart: string
  weekEnd: string
  positions: string[]
  shifts: string[]
  days: BoardDay[]
  summary: BoardSummary
}

export interface RosterMember {
  id: number
  姓名: string
  所属班组: string
  可值岗位: string
  onDuty: boolean
  assignments: { 岗位名称: string; 班次时段: string; 替班人员: string; 到岗确认: string }[]
  dutyText: string
}

export interface RosterData {
  date: string
  positions: string[]
  members: RosterMember[]
  onDutyCount: number
}

export interface ShiftEntry {
  id: number
  排班编号: string
  岗位名称: string
  值班人员: string
  值班日期: string
  班次时段: string
  替班人员: string
  到岗确认: string
  排班状态: string
  status?: string
  void?: boolean
  pending?: boolean
}

export interface StaffshiftGaps {
  weekStart: string
  weekEnd: string
  unscheduledDays: number
  gapCount: number
  substituteMissingCount: number
  byShift: { shift: string; gapCount: number; substituteMissingCount: number }[]
}
