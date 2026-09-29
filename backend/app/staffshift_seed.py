"""人员排班场景化种子：按运行当天所在自然周生成演示排班。

独立成模块是为了避免 store <-> services.staffshift 在包初始化阶段循环导入。
看板、整表、台账共用的「有效排班」口径仍在 services.staffshift 内。
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

STAFFSHIFT_MODULE = "staffshift"
ROSTER_MODULE = "staffshift_roster"

SHIFT_FIELDS = ["早班", "中班", "夜班"]
POSITIONS = ["廊桥操作", "行李装卸", "航食配送", "航油加注", "机坪牵引", "机坪巡查"]

# 班组台账花名册：岗位资格与所属班组固定，「当日在岗」从有效排班实时推导。
ROSTER_NAMES = [
    ("王磊", "甲班", ["廊桥操作"]),
    ("李娜", "甲班", ["行李装卸"]),
    ("张涛", "甲班", ["航食配送"]),
    ("赵敏", "甲班", ["航油加注"]),
    ("陈强", "甲班", ["机坪牵引"]),
    ("刘洋", "甲班", ["机坪巡查"]),
    ("孙鹏", "乙班", ["廊桥操作"]),
    ("周婷", "乙班", ["行李装卸"]),
    ("吴凯", "乙班", ["航食配送"]),
    ("郑爽", "乙班", ["航油加注"]),
    ("冯刚", "乙班", ["机坪牵引"]),
    ("何丽", "乙班", ["机坪巡查"]),
    ("高峰", "丙班", ["廊桥操作"]),
    ("林静", "丙班", ["行李装卸"]),
    ("罗斌", "丙班", ["航食配送"]),
    ("唐诗", "丙班", ["航油加注"]),
    ("邓超", "丙班", ["机坪牵引"]),
    ("许晴", "丙班", ["机坪巡查"]),
]


def seed_demo_data(store: Any) -> None:
    """构造贴近场景的演示排班：在岗、替班缺失、缺口、整天未排班、冲突作废与跨周数据。

    store 由调用方传入，避免本模块在顶层 import app.store 形成循环导入。
    """
    roster = store.rows(ROSTER_MODULE)
    roster.clear()
    for idx, (name, team, skills) in enumerate(ROSTER_NAMES, start=1):
        roster.append({
            "id": idx,
            "姓名": name,
            "所属班组": team,
            "可值岗位": "、".join(skills),
        })

    names = [name for name, _, _ in ROSTER_NAMES]
    rows = store.rows(STAFFSHIFT_MODULE)
    rows.clear()

    state = {"seq": 1}

    def add(day: date, position: str, shift: str, primary: str, substitute: str,
            status: str = "已确认", checked: bool = True, void: bool = False) -> None:
        seq = state["seq"]
        final_status = "已作废" if void else status
        rows.append({
            "id": seq,
            "排班编号": f"STAF-{seq:04d}",
            "岗位名称": position,
            "值班人员": primary,
            "值班日期": day.isoformat(),
            "班次时段": shift,
            "替班人员": substitute,
            "到岗确认": "已到岗" if checked else "未到岗",
            "排班状态": final_status,
            "status": final_status,
            "pending": (not void) and (status != "已确认" or not checked),
            "abnormal": False,
            "void": void,
        })
        state["seq"] = seq + 1

    today = date.today()
    monday = today - timedelta(days=today.weekday())

    # 岗位 -> (当班人, 替班人)；当班人为 None 表示没人顶上（缺口），替班人为 "" 表示替班缺失。
    plan: dict[int, dict[str, tuple[object, str]]] = {
        0: {  # 周一：铺满，两个岗位替班缺失
            "廊桥操作": (names[0], names[6]),
            "行李装卸": (names[1], names[7]),
            "航食配送": (names[2], ""),
            "航油加注": (names[3], names[9]),
            "机坪牵引": (names[4], names[10]),
            "机坪巡查": (names[5], ""),
        },
        2: {  # 周三：两个岗位当班人空缺
            "廊桥操作": (names[12], names[0]),
            "行李装卸": (None, ""),
            "航食配送": (names[14], names[2]),
            "航油加注": (names[15], ""),
            "机坪牵引": (None, ""),
            "机坪巡查": (names[17], names[5]),
        },
        3: {  # 周四：早班留几条未到岗，航食配送缺口
            "廊桥操作": (names[6], names[12]),
            "行李装卸": (names[7], names[13]),
            "航食配送": (None, ""),
            "航油加注": (names[9], names[3]),
            "机坪牵引": (names[10], ""),
            "机坪巡查": (names[11], names[17]),
        },
        4: {  # 周五：铺满
            "廊桥操作": (names[0], names[12]),
            "行李装卸": (names[7], names[1]),
            "航食配送": (names[8], names[2]),
            "航油加注": (names[3], names[15]),
            "机坪牵引": (names[10], names[4]),
            "机坪巡查": (names[5], names[11]),
        },
        5: {  # 周六：少量岗位
            "廊桥操作": (names[12], names[6]),
            "航油加注": (names[15], names[3]),
            "机坪巡查": (names[17], ""),
        },
        6: {  # 周日：少量岗位
            "行李装卸": (names[13], names[7]),
            "机坪牵引": (names[10], ""),
        },
    }
    shifts_for_day = {
        0: ["早班", "中班", "夜班"],
        2: ["早班", "中班"],
        3: ["早班", "中班", "夜班"],
        4: ["早班", "中班", "夜班"],
        5: ["早班", "夜班"],
        6: ["中班"],
    }

    for offset, positions in plan.items():
        day = monday + timedelta(days=offset)
        for shift in shifts_for_day[offset]:
            for position, (primary, substitute) in positions.items():
                person = str(primary) if primary else ""
                sub = substitute or ""
                # 周四早班留成「未到岗待确认」，其它默认已确认到岗。
                checked = not (offset == 3 and shift == "早班")
                status = "已确认" if checked or not person else "待确认"
                add(day, position, shift, person, sub, status=status, checked=checked)

    # 整天未排班：本周二（offset 1）不写任何排班，看板需按「未排班」呈现。

    # 冲突演示：周一廊桥操作早班先登记一条，随后再登记一条；后者有效，前者作废。
    add(monday, "廊桥操作", "早班", names[6], names[12], void=True)
    add(monday, "廊桥操作", "早班", names[0], names[6])

    # 上一周铺几条，切换周时格子里的人应当跟着变。
    last_monday = monday - timedelta(days=7)
    add(last_monday, "廊桥操作", "早班", names[6], names[0])
    add(last_monday, "行李装卸", "中班", names[13], names[1])
    add(last_monday + timedelta(days=2), "航油加注", "夜班", names[15], names[9])
