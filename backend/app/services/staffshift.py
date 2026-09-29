"""人员排班业务规则。

值班看板、排班整表、班组台账三处的「在岗人」都从同一份有效排班推导，
任何一处登记/作废/安排替班后，另外两处读到的结果自动一致。

口径约定：
- 同一岗位、同一天、同一班次时段只允许一条「有效」排班；
  再次登记即视为最新排班，前一条自动作废（作废记录仍留在整表里可追溯）。
- 某天没有任何一条有效排班时，整天按「未排班」呈现，而不是在岗 0 人。
- 格子状态：
  * covered       当班人已配齐（有当班人且有替班人）
  * substitute_missing  有当班人但没有替班安排（替班缺失，单独标记）
  * gap           当班人空缺，没人顶上（缺口记号）
  * unscheduled   整天没有任何有效排班，整天按「未排班」呈现，格子不计缺口。
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from app.staffshift_seed import POSITIONS, ROSTER_MODULE, SHIFT_FIELDS
from app.store import store

MODULE = "staffshift"

REQUIRED_FIELDS = ["岗位名称", "值班人员", "值班日期", "班次时段"]

STATUS_CONFIRMED = "已确认"
STATUS_SUBSTITUTED = "已替班"
STATUS_VOID = "已作废"
ACTION_RULES = {"确认排班": "已确认", "安排替班": "已替班", "申请调班": "已调班", "确认到岗": "已确认"}


def _iso(day: date) -> str:
    return day.isoformat()


def week_range(week_start: str | None) -> list[date]:
    """把任意传入的日期对齐到所在自然周（周一为一周起点），返回 7 天。"""
    if week_start:
        try:
            anchor = date.fromisoformat(week_start)
        except ValueError:
            anchor = date.today()
    else:
        anchor = date.today()
    monday = anchor - timedelta(days=anchor.weekday())
    return [monday + timedelta(days=i) for i in range(7)]


class StaffshiftService:
    # ---- 列表 / 明细 -------------------------------------------------
    def list_entries(
        self,
        *,
        keyword: str | None = None,
        status: str | None = None,
        date: str | None = None,
        shift: str | None = None,
        include_void: bool = True,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        rows = store.rows(MODULE)
        if not include_void:
            rows = [row for row in rows if not row.get("void")]
        if keyword:
            rows = [row for row in rows if keyword in str(row.get("排班编号", ""))
                    or keyword in str(row.get("岗位名称", ""))
                    or keyword in str(row.get("值班人员", ""))]
        if status:
            rows = [row for row in rows if row.get("status") == status]
        if date:
            rows = [row for row in rows if row.get("值班日期") == date]
        if shift:
            rows = [row for row in rows if row.get("班次时段") == shift]
        total = len(rows)
        start = max(page - 1, 0) * size
        return rows[start:start + size], total

    def get_entry(self, entry_id: int) -> dict[str, Any] | None:
        return store.find(MODULE, entry_id)

    # ---- 登记 / 动作 -------------------------------------------------
    def create_entry(self, values: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
        missing = [field for field in REQUIRED_FIELDS if not str(values.get(field) or "").strip()]
        if missing:
            return None, missing
        rows = store.rows(MODULE)

        position = str(values["岗位名称"]).strip()
        duty_date = str(values["值班日期"]).strip()
        shift = str(values["班次时段"]).strip()

        # 冲突处理：同岗位 + 同一天 + 同一班次，最后一次为准，前一次作废。
        conflicts = [
            row for row in rows
            if not row.get("void")
            and row.get("岗位名称") == position
            and row.get("值班日期") == duty_date
            and row.get("班次时段") == shift
        ]
        for row in conflicts:
            row["void"] = True
            row["排班状态"] = STATUS_VOID
            row["status"] = STATUS_VOID
            row["pending"] = False

        entry = {"id": max((int(row.get("id", 0)) for row in rows), default=0) + 1}
        entry["排班编号"] = str(values.get("排班编号") or f"STAF-{entry['id']:04d}")
        entry["岗位名称"] = position
        entry["值班人员"] = str(values["值班人员"]).strip()
        entry["值班日期"] = duty_date
        entry["班次时段"] = shift
        entry["替班人员"] = str(values.get("替班人员") or "").strip()
        entry["到岗确认"] = "未到岗"
        entry["排班状态"] = "待确认"
        entry["status"] = "待确认"
        entry["pending"] = True
        entry["abnormal"] = False
        entry["void"] = False
        rows.append(entry)
        return entry, []

    def run_action(
        self, entry_id: int, action: str, extra: dict[str, Any] | None = None
    ) -> tuple[dict[str, Any] | None, str]:
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None, f"排班记录 {entry_id} 不存在或已归档"
        if entry.get("void"):
            return None, "该排班已被更新的排班覆盖作废，不能再执行动作"
        extra = extra or {}

        if action == "安排替班":
            substitute = str(extra.get("替班人员") or entry.get("替班人员") or "").strip()
            if not substitute:
                return None, "安排替班必须指定替班人员"
            entry["替班人员"] = substitute
            entry["排班状态"] = STATUS_SUBSTITUTED
            entry["status"] = STATUS_SUBSTITUTED
            entry["pending"] = False
            return entry, f"已安排 {substitute} 替班"

        if action == "确认到岗":
            entry["到岗确认"] = "已到岗"
            entry["pending"] = False
            if entry.get("status") == "待确认":
                entry["status"] = STATUS_CONFIRMED
                entry["排班状态"] = STATUS_CONFIRMED
            return entry, "当班人到岗已确认"

        if action not in ACTION_RULES:
            return None, f"动作「{action}」不属于人员排班可执行范围"
        target = ACTION_RULES[action]
        entry["排班状态"] = target
        entry["status"] = target
        entry["pending"] = target == "待确认"
        return entry, f"排班记录已{action}"

    # ---- 看板 / 台账 统一口径 ----------------------------------------
    def effective_schedules(self) -> list[dict[str, Any]]:
        """去重后的有效排班：同（日期、岗位、班次）只保留最后登记的一条。"""
        latest: dict[tuple[str, str, str], dict[str, Any]] = {}
        for row in sorted(store.rows(MODULE), key=lambda r: int(r.get("id", 0))):
            if row.get("void"):
                continue
            key = (str(row.get("值班日期")), str(row.get("岗位名称")), str(row.get("班次时段")))
            latest[key] = row
        return list(latest.values())

    def _cell_state(self, row: dict[str, Any] | None) -> str:
        if row is None:
            return "gap"
        if not str(row.get("值班人员") or "").strip():
            return "gap"
        if not str(row.get("替班人员") or "").strip():
            return "substitute_missing"
        return "covered"

    def board(self, week_start: str | None) -> dict[str, Any]:
        days = week_range(week_start)
        effective = self.effective_schedules()
        index: dict[tuple[str, str, str], dict[str, Any]] = {
            (str(r.get("值班日期")), str(r.get("岗位名称")), str(r.get("班次时段"))): r
            for r in effective
        }

        day_views: list[dict[str, Any]] = []
        for day in days:
            iso = _iso(day)
            day_rows = [r for r in effective if r.get("值班日期") == iso]
            unscheduled = len(day_rows) == 0
            shift_views: list[dict[str, Any]] = []
            for shift in SHIFT_FIELDS:
                cells: list[dict[str, Any]] = []
                gap_count = 0
                missing_sub_count = 0
                for position in POSITIONS:
                    row = index.get((iso, position, shift))
                    state = self._cell_state(row)
                    # 整天未排班时不把岗位格子计成缺口，只在 day 层标记。
                    if unscheduled:
                        state = "unscheduled"
                    elif state == "gap":
                        gap_count += 1
                    elif state == "substitute_missing":
                        missing_sub_count += 1
                    cells.append({
                        "position": position,
                        "state": state,
                        "entryId": row.get("id") if row else None,
                        "primary": (row.get("值班人员") or "") if row else "",
                        "substitute": (row.get("替班人员") or "") if row else "",
                        "checked": (row.get("到岗确认") == "已到岗") if row else False,
                        "status": row.get("status") if row else None,
                    })
                shift_views.append({
                    "shift": shift,
                    "cells": cells,
                    "gapCount": 0 if unscheduled else gap_count,
                    "substituteMissingCount": 0 if unscheduled else missing_sub_count,
                    "onDutyCount": sum(
                        1 for c in cells if c["state"] in ("covered", "substitute_missing")
                    ) if not unscheduled else None,
                })
            day_views.append({
                "date": iso,
                "weekday": ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][day.weekday()],
                "unscheduled": unscheduled,
                "shifts": shift_views,
                "gapCount": sum(s["gapCount"] for s in shift_views),
                "substituteMissingCount": sum(s["substituteMissingCount"] for s in shift_views),
            })

        return {
            "weekStart": _iso(days[0]),
            "weekEnd": _iso(days[-1]),
            "positions": POSITIONS,
            "shifts": SHIFT_FIELDS,
            "days": day_views,
            "summary": {
                "unscheduledDays": sum(1 for d in day_views if d["unscheduled"]),
                "gapCount": sum(d["gapCount"] for d in day_views),
                "substituteMissingCount": sum(d["substituteMissingCount"] for d in day_views),
                "byShift": [
                    {
                        "shift": shift,
                        "gapCount": sum(d["shifts"][i]["gapCount"] for d in day_views),
                        "substituteMissingCount": sum(
                            d["shifts"][i]["substituteMissingCount"] for d in day_views
                        ),
                    }
                    for i, shift in enumerate(SHIFT_FIELDS)
                ],
            },
        }

    def roster(self, duty_date: str | None) -> dict[str, Any]:
        """班组台账：花名册固定，当班安排直接取看板同源的有效排班。"""
        target = duty_date or _iso(date.today())
        effective = [
            row for row in self.effective_schedules()
            if row.get("值班日期") == target and str(row.get("值班人员") or "").strip()
        ]
        assignment_by_person: dict[str, list[dict[str, Any]]] = {}
        for row in effective:
            assignment_by_person.setdefault(str(row["值班人员"]), []).append({
                "岗位名称": row.get("岗位名称"),
                "班次时段": row.get("班次时段"),
                "替班人员": row.get("替班人员") or "",
                "到岗确认": row.get("到岗确认"),
            })

        members = []
        for person in store.rows(ROSTER_MODULE):
            duty = assignment_by_person.get(person["姓名"], [])
            members.append({
                **person,
                "onDuty": bool(duty),
                "assignments": duty,
                "dutyText": "、".join(f"{a['班次时段']}·{a['岗位名称']}" for a in duty),
            })

        return {
            "date": target,
            "positions": POSITIONS,
            "members": members,
            "onDutyCount": sum(1 for m in members if m["onDuty"]),
        }

    # 供运营概览调用：当前周各班次缺口（与看板 summary.byShift 完全同源）。
    def shift_gap_summary(self, week_start: str | None = None) -> dict[str, Any]:
        board = self.board(week_start)
        return {
            "weekStart": board["weekStart"],
            "weekEnd": board["weekEnd"],
            "unscheduledDays": board["summary"]["unscheduledDays"],
            "gapCount": board["summary"]["gapCount"],
            "substituteMissingCount": board["summary"]["substituteMissingCount"],
            "byShift": board["summary"]["byShift"],
        }
