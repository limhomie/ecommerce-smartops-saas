"""ERP system integration tool — inventory, procurement, financial data."""

from __future__ import annotations

from src.tools.base import BaseTool, ToolResult


class ERPTool(BaseTool):
    name = "erp_api"
    description = "查询 ERP 系统的库存、采购、成本和财务数据"

    async def execute(
        self,
        action: str = "inventory",
        sku: str = "",
        warehouse: str = "",
    ) -> ToolResult:
        if action == "inventory":
            return self._get_inventory(warehouse)
        elif action == "cost":
            return self._get_cost(sku)
        elif action == "procurement":
            return self._get_procurement()
        else:
            return ToolResult(success=False, error=f"Unknown action: {action}")

    def _get_inventory(self, warehouse: str) -> ToolResult:
        return ToolResult(
            success=True,
            data={
                "warehouse": warehouse or "主仓",
                "items": [
                    {"sku": "SKU-001", "name": "有机棉T恤-白色-M", "qty": 230, "safety_stock": 50},
                    {"sku": "SKU-002", "name": "有机棉T恤-白色-L", "qty": 180, "safety_stock": 50},
                    {"sku": "SKU-003", "name": "环保帆布袋-标准", "qty": 25, "safety_stock": 30, "alert": "低于安全库存"},
                ],
            },
            tool_name=self.name,
        )

    def _get_cost(self, sku: str) -> ToolResult:
        return ToolResult(
            success=True,
            data={
                "sku": sku or "SKU-001",
                "unit_cost": "$8.50",
                "shipping_cost": "$2.30",
                "warehousing_cost": "$0.80",
                "total_landed_cost": "$11.60",
                "selling_price": "$45.60",
                "gross_margin": "74.6%",
            },
            tool_name=self.name,
        )

    def _get_procurement(self) -> ToolResult:
        return ToolResult(
            success=True,
            data={
                "pending_orders": [
                    {"po_id": "PO-2026-001", "supplier": "供应商A", "status": "在途", "eta": "2026-06-20"},
                    {"po_id": "PO-2026-002", "supplier": "供应商B", "status": "生产中", "eta": "2026-06-25"},
                ]
            },
            tool_name=self.name,
        )
