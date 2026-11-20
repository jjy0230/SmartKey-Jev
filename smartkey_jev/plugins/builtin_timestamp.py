"""
Built-in Plugin: Unix Timestamp Converter.
Detects 10-digit (seconds) or 13-digit (milliseconds) timestamps and converts them to human-readable dates.
"""

import time
import datetime
from typing import Dict, Any
from .plugin_base import BasePlugin
from ..core.models import SelectionContext, MacroCategory, MacroDeliveryMode


class TimestampPlugin(BasePlugin):
    @property
    def id(self) -> str:
        return "convert_timestamp"

    @property
    def title(self) -> str:
        return "时间戳转换"

    @property
    def icon(self) -> str:
        return "⏰"

    @property
    def category(self) -> MacroCategory:
        return MacroCategory.UTILITY

    @property
    def delivery_mode(self) -> MacroDeliveryMode:
        return MacroDeliveryMode.IN_PLACE_REPLACE

    @property
    def description(self) -> str:
        return "将 10 位或 13 位 Unix 时间戳就地转换为标准北京时间"

    def match(self, context: SelectionContext) -> float:
        s = context.text.strip()
        if s.isdigit():
            if len(s) == 10 and (s.startswith("1") or s.startswith("2")):
                return 0.98  # Standard 10-digit timestamp (e.g. 1700000000)
            if len(s) == 13 and (s.startswith("1") or s.startswith("2")):
                return 0.99  # 13-digit ms timestamp
        return 0.0

    def execute(self, context: SelectionContext) -> Dict[str, Any]:
        s = context.raw_text.strip() or context.text.strip()
        try:
            val = int(s)
            if len(s) == 13:
                val = val / 1000.0
            dt = datetime.datetime.fromtimestamp(val)
            formatted = dt.strftime("%Y-%m-%d %H:%M:%S")
            return {
                "status": "success",
                "result": formatted,
                "preview": f"{s} ➔ {formatted}",
            }
        except Exception as e:
            return {"status": "error", "message": f"Timestamp parse error: {e}"}
