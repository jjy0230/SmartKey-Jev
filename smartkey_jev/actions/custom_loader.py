"""
Custom User Macros & Configuration Loader.
Loads user-defined macros from ~/.smartkey_jev/macros.json with auto-reload support.
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from ..core.models import MacroAction, MacroCategory, MacroDeliveryMode
from .registry import MacroRegistry, DEFAULT_REGISTRY


CONFIG_DIR = Path.home() / ".smartkey_jev"
MACROS_FILE = CONFIG_DIR / "macros.json"

DEFAULT_CUSTOM_MACROS_TEMPLATE: List[Dict[str, Any]] = [
    {
        "id": "git_commit_gen",
        "title": "生成 Git Commit",
        "icon": "📦",
        "category": "code",
        "description": "分析选中的 git diff 并生成结构化 Conventional Commit 消息",
        "delivery_mode": "drawer_panel",
        "default_shortcut": "2"
    },
    {
        "id": "snake_case_conv",
        "title": "转 Snake Case",
        "icon": "🐍",
        "category": "utility",
        "description": "将选中的驼峰命名或短横线命名就地替换为 snake_case",
        "delivery_mode": "in_place_replace",
        "default_shortcut": "3"
    }
]


def ensure_config_dir():
    """Ensures ~/.smartkey_jev directory exists and seeds sample macros.json if absent."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not MACROS_FILE.exists():
        with open(MACROS_FILE, "w", encoding="utf-8") as f:
            json.dump({"custom_macros": DEFAULT_CUSTOM_MACROS_TEMPLATE}, f, indent=2, ensure_ascii=False)


def load_custom_macros(registry: Optional[MacroRegistry] = None) -> List[MacroAction]:
    """
    Parses ~/.smartkey_jev/macros.json and registers custom actions into the target registry.
    Returns list of loaded custom MacroActions.
    """
    ensure_config_dir()
    target_registry = registry or DEFAULT_REGISTRY
    loaded: List[MacroAction] = []

    try:
        with open(MACROS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        raw_macros = data.get("custom_macros", [])
        for item in raw_macros:
            try:
                cat_val = item.get("category", "utility").lower()
                cat = MacroCategory(cat_val) if cat_val in [c.value for c in MacroCategory] else MacroCategory.UTILITY

                deliv_val = item.get("delivery_mode", "external_dispatch").lower()
                deliv = MacroDeliveryMode(deliv_val) if deliv_val in [d.value for d in MacroDeliveryMode] else MacroDeliveryMode.EXTERNAL_DISPATCH

                macro = MacroAction(
                    id=item["id"],
                    title=item["title"],
                    icon=item.get("icon", "⚡"),
                    category=cat,
                    description=item.get("description", ""),
                    delivery_mode=deliv,
                    default_shortcut=item.get("default_shortcut", "3"),
                    metadata=item.get("metadata", {}),
                )
                target_registry.register(macro)
                loaded.append(macro)
            except Exception as e:
                print(f"[SmartKey-Jev] Failed to parse custom macro item {item}: {e}")

    except Exception as e:
        print(f"[SmartKey-Jev] Error reading custom macros: {e}")

    return loaded
