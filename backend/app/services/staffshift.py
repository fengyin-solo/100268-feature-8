"""人员排班业务规则：登记、替班、冲突去重，以及值班看板/班组台账/班次缺口的统一口径。

看板格子、班组台账、运营概览的缺口数都从 ``canonical_assignments`` 这一份"有效排班"推导，
任何页面都不允许各算各的。同一岗位同一时段被重复排班时，只认最后一次，旧记录置为作废。
"""
from __future__ import annotations

import datetime as _dt
from typing import Any

from app.store import store

MODULE = "staffshift"
REQUIRED_FIELDS = ["岗位名称", "值班日期", "班次时段", "值班人员"]
STATUS_ORDER = ["待确认", "已确认", "已替班", "已调班"]
ACTION_RULES = {"确认排班": "已确认", "安排替班": "已替班", "申请调班": "已调班"}
NEGATIVE_ACTIONS: list[str] = []

# 班组台账与值班看板共用的班次、岗位顺序
SHIFT_SLOTS = ["早班", "中班", "夜班"]
POSTS = ["机坪调度", "航班协调", "廊桥监管", "装卸队长"]
# 看板默认锚定到内置示例数据所在周（真实环境会换成"今天"）
DEFAULT_WEEK_ANCHOR = "2026-09-30"

SLOT_FIELDS = ["排班编号", "岗位名称", "值班人员", "值班日期", "班次时段",
               "替班人员", "到岗确认", "排班状态"]


class StaffshiftService:
    # ---------- 基础查询 ----------
    def list_entries(
        self,
        *,
        keyword: str | None = None,
        status: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        rows = store.rows(MODULE)
        if keyword:
            rows = [row for row in rows if keyword in str(row.get("排班编号", ""))]
        if status:
            rows = [row for row in rows if row.get("status") == status]
        total = len(rows)
        start = max(page - 1, 0) * size
        return rows[start:start + size], total

    def get_entry(self, entry_id: int) -> dict[str, Any] | None:
        return store.find(MODULE, entry_id)

    # ---------- 统一口径：有效排班 ----------
    def canonical_assignments(self, *, include_voided: bool = False) -> list[dict[str, Any]]:
        """按 (值班日期, 班次时段, 岗位名称) 去重，同键只保留最后一次排班。

        返回结果按日期、班次、岗位排好序，看板、台账、缺口统计都基于它，保证"同一份在岗人"。
        """
        latest: dict[tuple[str, str, str], dict[str, Any]] = {}
        for row in store.rows(MODULE):
            if row.get("voided") and not include_voided:
                continue
            key = (str(row.get("值班日期", "")), str(row.get("班次时段", "")),
                   str(row.get("岗位名称", "")))
            latest[key] = row  # 列表即登记先后，后出现的就是"最后一次排班"
        return [latest[key] for key in sorted(latest, key=lambda k: (k[0], k[1], k[2]))]

    # ---------- 登记与动作 ----------
    def create_entry(self, values: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
        missing = [field for field in REQUIRED_FIELDS if not str(values.get(field) or "").strip()]
        if missing:
            return None, missing

        slot = str(values["班次时段"]).strip()
        if slot not in SHIFT_SLOTS:
            return None, [f"班次时段仅支持：{'、'.join(SHIFT_SLOTS)}"]

        rows = store.rows(MODULE)
        date = str(values["值班日期"]).strip()
        post = str(values["岗位名称"]).strip()

        # 同一岗位同一时段再次排班：前一次作废，以最后一次为准
        superseded_ids: list[int] = []
        for row in rows:
            if (not row.get("voided")
                    and str(row.get("值班日期", "")) == date
                    and str(row.get("班次时段", "")) == slot
                    and str(row.get("岗位名称", "")) == post):
                self._mark_voided(row, f"同一岗位同一时段被新排班 STAF 替换，原排班作废")
                superseded_ids.append(int(row.get("id", 0)))

        entry = {"id": max((int(row.get("id", 0)) for row in rows), default=0) + 1}
        entry["排班编号"] = f"STAF-{entry['id']:04d}"
        entry["岗位名称"] = post
        entry["值班人员"] = str(values["值班人员"]).strip()
        entry["值班日期"] = date
        entry["班次时段"] = slot
        entry["替班人员"] = str(values.get("替班人员") or "").strip()
        entry["到岗确认"] = str(values.get("到岗确认") or "未到岗").strip() or "未到岗"
        entry["status"] = "待确认"
        entry["排班状态"] = "待确认"
        entry["pending"] = True
        entry["abnormal"] = False
        if superseded_ids:
            entry["替换记录"] = superseded_ids
        rows.append(entry)
        return entry, []

    def assign_substitute(self, entry_id: int, substitute: str) -> tuple[dict[str, Any] | None, str]:
        """给某条排班补上替班人员；补上空名字视为缺失，不改状态。"""
        entry = store.find(MODULE, entry_id)
        if entry is None or entry.get("voided"):
            return None, f"排班记录 {entry_id} 不存在或已作废"
        substitute = substitute.strip()
        if not substitute:
            return None, "替班人员姓名不能为空"
        entry["替班人员"] = substitute
        if entry.get("status") == "待确认":
            entry["status"] = "已确认"
            entry["排班状态"] = "已确认"
            entry["pending"] = False
        elif entry.get("status") in ("已确认",):
            entry["status"] = "已替班"
            entry["排班状态"] = "已替班"
            entry["pending"] = False
        return entry, f"已为 {entry.get('岗位名称')} 安排替班：{substitute}"

    def run_action(self, entry_id: int, action: str,
                   values: dict[str, Any] | None = None) -> tuple[dict[str, Any] | None, str]:
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None, f"排班记录 {entry_id} 不存在或已归档"
        if entry.get("voided"):
            return None, f"排班记录 {entry_id} 已作废，不能再执行动作"
        if action not in ACTION_RULES:
            return None, f"动作「{action}」不属于人员排班可执行范围"
        if action == "安排替班":
            return self.assign_substitute(entry_id, str((values or {}).get("替班人员", "")))
        target = ACTION_RULES[action]
        entry["status"] = target
        entry["排班状态"] = target
        entry["pending"] = target == "待确认"
        entry["abnormal"] = action in NEGATIVE_ACTIONS
        return entry, f"排班记录已{action}"

    # ---------- 值班看板：班次 × 日期 的格子 ----------
    def week_board(self, week_start: str | None = None) -> dict[str, Any]:
        """构造一周值班看板：每个班次一行、每天一列，列内按岗位铺格子。"""
        monday = self._resolve_monday(week_start)
        dates = [(monday + _dt.timedelta(days=i)).isoformat() for i in range(7)]

        active = [row for row in self.canonical_assignments()
                  if dates[0] <= str(row.get("值班日期", "")) <= dates[-1]]
        index: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for row in active:
            index.setdefault((str(row["值班日期"]), str(row["班次时段"])), []).append(row)

        days: list[dict[str, Any]] = []
        gap_summary = {slot: 0 for slot in SHIFT_SLOTS}
        missing_substitute_total = 0
        unscheduled_dates: list[str] = []
        for i, date in enumerate(dates):
            slots_payload: list[dict[str, Any]] = []
            day_rows = [row for slot in SHIFT_SLOTS for row in index.get((date, slot), [])]
            day_unscheduled = not day_rows
            day_gap = 0
            for slot in SHIFT_SLOTS:
                rows = index.get((date, slot), [])
                by_post = {str(row["岗位名称"]): row for row in rows}
                cells = []
                if day_unscheduled:
                    # 整天未排班：格子按"未排班"呈现，不计缺口、不写零人
                    for post in POSTS:
                        cells.append({
                            "岗位名称": post, "state": "unscheduled",
                            "值班人员": "", "替班人员": "",
                            "缺口": False, "缺替班": False, "已排班": False,
                            "entry_id": None, "排班编号": "",
                        })
                elif not rows:
                    # 当天有排班但该班次未排：整格按未排呈现，不拆成四个缺口
                    for post in POSTS:
                        cells.append({
                            "岗位名称": post, "state": "unscheduled",
                            "值班人员": "", "替班人员": "",
                            "缺口": False, "缺替班": False, "已排班": False,
                            "entry_id": None, "排班编号": "",
                        })
                else:
                    for post in POSTS:
                        row = by_post.get(post)
                        if row is None:
                            cells.append({
                                "岗位名称": post, "state": "gap",
                                "值班人员": "", "替班人员": "",
                                "缺口": True, "缺替班": False, "已排班": False,
                                "entry_id": None, "排班编号": "",
                            })
                            day_gap += 1
                            gap_summary[slot] += 1
                        else:
                            sub = str(row.get("替班人员") or "").strip()
                            missing_sub = not sub
                            if missing_sub:
                                missing_substitute_total += 1
                            cells.append({
                                "岗位名称": post,
                                "state": "missing-substitute" if missing_sub else "covered",
                                "值班人员": str(row.get("值班人员", "")),
                                "替班人员": sub,
                                "缺口": False, "缺替班": missing_sub, "已排班": True,
                                "entry_id": int(row.get("id", 0)),
                                "排班编号": str(row.get("排班编号", "")),
                                "排班状态": str(row.get("排班状态", row.get("status", ""))),
                                "到岗确认": str(row.get("到岗确认", "")),
                            })
                slots_payload.append({
                    "班次时段": slot,
                    "已排班": bool(rows),
                    "格子": cells,
                })
            if day_unscheduled:
                unscheduled_dates.append(date)
            days.append({
                "日期": date,
                "星期": ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][i],
                "未排班": day_unscheduled,
                "缺口数": day_gap,
                "班次": slots_payload,
            })

        return {
            "weekStart": monday.isoformat(),
            "weekEnd": (monday + _dt.timedelta(days=6)).isoformat(),
            "slots": SHIFT_SLOTS,
            "posts": POSTS,
            "days": days,
            "缺口": [{"班次时段": slot, "缺口数": gap_summary[slot]} for slot in SHIFT_SLOTS],
            "缺口总数": sum(gap_summary.values()),
            "缺替班总数": missing_substitute_total,
            "未排班日期": unscheduled_dates,
        }

    # ---------- 班组台账：人从哪来 ----------
    def roster(self, date: str) -> dict[str, Any]:
        """某天班组台账：在岗人与看板格子同一份有效排班；整天无记录按未排班呈现。"""
        active = [row for row in self.canonical_assignments()
                  if str(row.get("值班日期", "")) == date]
        slots_payload = []
        for slot in SHIFT_SLOTS:
            members = []
            for row in active:
                if str(row.get("班次时段", "")) != slot:
                    continue
                sub = str(row.get("替班人员") or "").strip()
                members.append({
                    "排班编号": row.get("排班编号", ""),
                    "岗位名称": row.get("岗位名称", ""),
                    "值班人员": row.get("值班人员", ""),
                    "替班人员": sub,
                    "到岗确认": row.get("到岗确认", ""),
                    "排班状态": row.get("排班状态", row.get("status", "")),
                    "缺替班": not sub,
                    "entry_id": int(row.get("id", 0)),
                })
            slots_payload.append({"班次时段": slot, "在岗人数": len(members), "成员": members})
        return {
            "日期": date,
            "未排班": not active,
            "在岗总人数": len(active),
            "班次": slots_payload,
        }

    # ---------- 内部工具 ----------
    def _resolve_monday(self, week_start: str | None) -> _dt.date:
        raw = (week_start or "").strip() or DEFAULT_WEEK_ANCHOR
        try:
            anchor = _dt.date.fromisoformat(raw)
        except ValueError:
            anchor = _dt.date.fromisoformat(DEFAULT_WEEK_ANCHOR)
        return anchor - _dt.timedelta(days=anchor.weekday())

    def _mark_voided(self, row: dict[str, Any], reason: str) -> None:
        row["voided"] = True
        row["status"] = "已作废"
        row["排班状态"] = "已作废"
        row["pending"] = False
        row["abnormal"] = False
        row["作废原因"] = reason
