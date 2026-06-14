"""Logistics tracking tool — query shipping status and generate customer replies."""

from __future__ import annotations

from src.tools.base import BaseTool, ToolResult


class LogisticsTool(BaseTool):
    name = "logistics"
    description = "查询物流单号状态，生成客户物流查询的自动回复"

    async def execute(
        self,
        action: str = "track",
        tracking_number: str = "",
        order_id: str = "",
    ) -> ToolResult:
        if action == "track":
            return self._track(tracking_number or order_id)
        elif action == "generate_reply":
            return self._generate_reply(tracking_number or order_id)
        else:
            return ToolResult(success=False, error=f"Unknown action: {action}")

    def _track(self, tracking_number: str) -> ToolResult:
        return ToolResult(
            success=True,
            data={
                "tracking_number": tracking_number or "YT202506130001",
                "carrier": "圆通速递",
                "status": "运输中",
                "current_location": "广州市分拣中心",
                "estimated_delivery": "2026-06-15",
                "history": [
                    {"date": "2026-06-13 08:00", "status": "已揽收", "location": "深圳市"},
                    {"date": "2026-06-13 14:00", "status": "运输中", "location": "广州市分拣中心"},
                ],
            },
            tool_name=self.name,
        )

    def _generate_reply(self, tracking_number: str) -> ToolResult:
        track_result = self._track(tracking_number)
        track_data = track_result.data

        reply = (
            f"尊敬的客户，您好！\n\n"
            f"您的包裹（快递单号：{track_data['tracking_number']}）\n"
            f"当前状态：{track_data['status']}\n"
            f"所在位置：{track_data['current_location']}\n"
            f"预计送达：{track_data['estimated_delivery']}\n\n"
            f"如有任何问题，请随时联系我们。祝您购物愉快！"
        )

        return ToolResult(
            success=True,
            data={
                "tracking": track_data,
                "auto_reply": reply,
            },
            tool_name=self.name,
        )
