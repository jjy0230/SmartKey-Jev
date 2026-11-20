"""
Built-in Plugin: Base64 Codec.
Detects base64 encoded strings and decodes them into plain text.
"""

import base64
import re
from typing import Dict, Any
from .plugin_base import BasePlugin
from ..core.models import SelectionContext, MacroCategory, MacroDeliveryMode


class Base64Plugin(BasePlugin):
    # Base64 regex heuristic (alphanumeric + +/ with trailing =)
    B64_PATTERN = re.compile(r'^[A-Za-z0-9+/]{8,}={0,2}$')

    @property
    def id(self) -> str:
        return "decode_base64"

    @property
    def title(self) -> str:
        return "Base64 解码"

    @property
    def icon(self) -> str:
        return "🔓"

    @property
    def category(self) -> MacroCategory:
        return MacroCategory.UTILITY

    @property
    def delivery_mode(self) -> MacroDeliveryMode:
        return MacroDeliveryMode.DRAWER_PANEL

    @property
    def description(self) -> str:
        return "检测并解码 Base64 密文或数据片段"

    def match(self, context: SelectionContext) -> float:
        s = context.text.strip()
        if len(s) >= 8 and len(s) % 4 == 0 and self.B64_PATTERN.match(s):
            try:
                decoded = base64.b64decode(s).decode("utf-8")
                if decoded.isprintable():
                    return 0.95
            except Exception:
                pass
        return 0.0

    def execute(self, context: SelectionContext) -> Dict[str, Any]:
        s = context.raw_text.strip() or context.text.strip()
        try:
            decoded = base64.b64decode(s).decode("utf-8")
            return {
                "status": "success",
                "result": decoded,
                "preview": decoded[:60],
            }
        except Exception as e:
            return {"status": "error", "message": f"Base64 decode failed: {e}"}
