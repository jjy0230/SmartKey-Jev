"""
SmartKey-Jev Core Data Models.
Defines contexts, macros, categories, and prediction payloads.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple, Dict, Any
import time


class MacroCategory(str, Enum):
    CODE = "code"
    TRANSLATION = "translation"
    WRITING = "writing"
    PRODUCTIVITY = "productivity"
    SEARCH = "search"
    UTILITY = "utility"


@dataclass(frozen=True)
class MacroAction:
    """Represents an atomic macro action executable by SmartKey-Jev."""
    id: str
    title: str
    icon: str
    category: MacroCategory
    description: str
    default_shortcut: str = "1"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SelectionContext:
    """Context extracted from the active desktop environment upon hotkey trigger."""
    text: str                               # Selected text (truncated to max length, e.g., 300 chars)
    raw_text: str                           # Full selected text
    process_name: str                       # Name of foreground process (e.g. 'code.exe', 'chrome.exe')
    process_path: str = ""                  # Full executable path
    window_title: str = ""                  # Foreground window title
    cursor_position: Tuple[int, int] = (0, 0) # (x, y) screen coordinates
    timestamp_ms: float = field(default_factory=lambda: time.time() * 1000.0)
    capture_latency_ms: float = 0.0         # Latency spent in capturing context

    @property
    def is_empty(self) -> bool:
        return not bool(self.text and self.text.strip())

    @property
    def char_count(self) -> int:
        return len(self.text)


@dataclass
class IntentPrediction:
    """Result of intent scoring for a candidate macro."""
    macro: MacroAction
    confidence: float                       # Posterior probability / confidence score [0.0, 1.0]
    rank: int = 1                           # 1, 2, or 3
    reason: str = ""                        # Explainability tag (e.g. "Rule: Code trace in IDE")
    source: str = "rule"                    # "rule" | "model" | "hybrid"
