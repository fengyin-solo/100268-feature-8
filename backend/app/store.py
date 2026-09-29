"""内存数据仓库：给每个业务模块准备一份可筛选、可流转的示例数据。

真实项目里这里会换成数据库访问层；当前实现只依赖标准库，保证克隆下来就能起。
"""
from __future__ import annotations

from typing import Any

from app.seed import SEED_ROWS


class Store:
    def __init__(self) -> None:
        self._tables: dict[str, list[dict[str, Any]]] = {
            name: [dict(row) for row in rows] for name, rows in SEED_ROWS.items()
        }
        self._seed_staffshift()

    def _seed_staffshift(self) -> None:
        """人员排班演示数据依赖运行当天日期，放独立模块避免与服务层循环导入。"""
        from app.staffshift_seed import seed_demo_data

        seed_demo_data(self)

    def module_names(self) -> list[str]:
        return sorted(self._tables)

    def rows(self, module: str) -> list[dict[str, Any]]:
        return self._tables.setdefault(module, [])

    def find(self, module: str, entry_id: int) -> dict[str, Any] | None:
        for row in self.rows(module):
            if int(row.get("id", 0)) == entry_id:
                return row
        return None

    def overview(self) -> dict[str, object]:
        modules: list[dict[str, object]] = []
        for name in self.module_names():
            rows = self.rows(name)
            modules.append({
                "name": name,
                "created": len(rows),
                "pending": sum(1 for row in rows if row.get("pending")),
                "abnormal": sum(1 for row in rows if row.get("abnormal")),
            })
        cards = [
            {"label": "业务模块", "value": len(modules)},
            {"label": "今日新增", "value": sum(int(item["created"]) for item in modules)},
            {"label": "待处理", "value": sum(int(item["pending"]) for item in modules)},
            {"label": "异常量", "value": sum(int(item["abnormal"]) for item in modules)},
        ]
        result: dict[str, object] = {"cards": cards, "modules": modules}
        # 各班次缺口与值班看板用同一份有效排班推导，格子一改这里立刻跟着变。
        try:
            from app.services.staffshift import StaffshiftService

            result["staffshiftGaps"] = StaffshiftService().shift_gap_summary()
        except Exception:  # noqa: BLE001 - 概览不应因排班模块异常而整体不可用
            result["staffshiftGaps"] = None
        return result


store = Store()
