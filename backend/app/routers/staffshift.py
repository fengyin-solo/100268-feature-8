"""人员排班接口：值班看板、排班整表、班组台账与排班动作都走这一组路由。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.schemas import ActionResult, EntryPayload, PageResult
from app.services.staffshift import POSITIONS, SHIFT_FIELDS, StaffshiftService

router = APIRouter(prefix="/api/staffshift", tags=["人员排班"])

service = StaffshiftService()

LIST_FIELDS = ["排班编号", "岗位名称", "值班人员", "值班日期", "班次时段", "替班人员", "到岗确认", "排班状态"]
STATUSES = ["待确认", "已确认", "已替班", "已调班", "已作废"]


@router.get("/board", response_model=dict)
def get_board(week_start: str | None = Query(default=None, description="周内任意日期，自动对齐到周一")) -> dict:
    """值班看板：按班次时段铺格子，下发每个格子的当班人、替班人与缺口标记。"""
    return service.board(week_start)


@router.get("/roster", response_model=dict)
def get_roster(date: str | None = Query(default=None, description="台账日期，默认今天")) -> dict:
    """班组台账：花名册 + 当天在岗安排，与看板读取同一份有效排班。"""
    return service.roster(date)


@router.get("/meta", response_model=dict)
def get_meta() -> dict[str, Any]:
    """岗位与班次候选项，前端登记表单与看板共用。"""
    return {"positions": POSITIONS, "shifts": SHIFT_FIELDS, "statuses": STATUSES}


@router.get("", response_model=PageResult[dict])
def list_entries(
    keyword: str | None = Query(default=None, description="按排班编号、岗位或值班人员检索"),
    status: str | None = Query(default=None, description="待确认、已确认、已替班、已调班、已作废"),
    date: str | None = Query(default=None, description="值班日期 YYYY-MM-DD"),
    shift: str | None = Query(default=None, description="早班、中班、夜班"),
    include_void: bool = Query(default=True, description="是否包含被最新排班覆盖作废的记录"),
    page: int = 1,
    size: int = 20,
) -> PageResult[dict]:
    """按条件过滤人员排班列表；没有数据时返回空页，不报错。"""
    if size > 500:
        raise HTTPException(status_code=400, detail="每页最多 500 条，请缩小分页范围")
    items, total = service.list_entries(
        keyword=keyword,
        status=status,
        date=date,
        shift=shift,
        include_void=include_void,
        page=page,
        size=size,
    )
    return PageResult(items=items, total=total, page=page, size=size)


@router.get("/export")
def export_entries(
    date: str | None = None,
    shift: str | None = None,
) -> dict[str, Any]:
    """导出人员排班清单：返回当前过滤条件下的全量数据（含作废记录）。"""
    items, total = service.list_entries(date=date, shift=shift, page=1, size=10000)
    return {"module": "staffshift", "total": total, "items": items}


@router.get("/{entry_id}", response_model=dict)
def get_entry(entry_id: int) -> dict:
    """读取单条排班记录明细；不存在时给出可读的错误说明。"""
    entry = service.get_entry(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"排班记录 {entry_id} 不存在或已归档")
    return entry


@router.post("", response_model=ActionResult)
def create_entry(payload: EntryPayload) -> ActionResult:
    """登记一条排班；同岗位同时段重复登记时，以本次为准、前一次自动作废。"""
    entry, missing = service.create_entry(payload.values)
    if missing:
        return ActionResult(ok=False, message=f"缺少必填字段：{'、'.join(missing)}")
    return ActionResult(ok=True, message="排班记录已登记；同岗位同时段若已有旧排班，旧记录已作废", entry=entry)


@router.post("/{entry_id}/actions", response_model=ActionResult)
def run_action(entry_id: int, payload: EntryPayload) -> ActionResult:
    """确认排班、安排替班（带替班人员）、确认到岗、申请调班。"""
    action = str(payload.values.get("action") or "").strip()
    entry, message = service.run_action(entry_id, action, payload.values)
    if entry is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message=message, entry=entry)
