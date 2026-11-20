"""
Global Configuration for SmartKey-Jev.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class HotkeyConfig:
    trigger_type: str = "double_alt"  # "double_alt" | "double_ctrl"
    double_tap_interval_ms: int = 300  # Max millisecond interval to register double tap
    suppress_system_menu: bool = True  # Consume key up to prevent Windows menu loop focus
    game_exemption_enabled: bool = True  # Auto-disable when foreground app is exclusive fullscreen
    spotlight_on_empty: bool = True  # When no text selected, launch centered Spotlight dispatcher


@dataclass
class CaptureConfig:
    max_context_chars: int = 300
    uia_timeout_ms: int = 15
    clipboard_wait_ms: int = 25
    preserve_clipboard: bool = True
    prevent_clipboard_history: bool = True  # Mark clipboard data to exclude from Win+V history


@dataclass
class ModelConfig:
    enabled: bool = False  # Disabled by default until model is configured
    provider: str = "stub"  # "stub" | "anyjev_local" | "openai_compatible" | "http"
    endpoint_url: str = "http://127.0.0.1:8000/v1/intent"
    model_name: str = "SmolLM2-1.7B-Instruct-4bit"
    timeout_ms: int = 40
    temperature: float = 0.1
    top_k_candidates: int = 8  # Number of pre-filtered candidates passed to model
    async_rerank: bool = True  # Non-blocking async re-ranking with UI stabilization lock


@dataclass
class UIConfig:
    theme: str = "dark"
    opacity: float = 0.94
    width: int = 270
    height: int = 145
    drawer_width: int = 360
    drawer_height: int = 240
    spotlight_width: int = 480
    spotlight_height: int = 260
    font_family: str = "Segoe UI Variable Text"
    font_size: int = 11


@dataclass
class DeliveryConfig:
    in_place_replace_delay_ms: int = 12  # Wait for foreground window to regain focus before Ctrl+V
    copy_to_clipboard_on_drawer: bool = True  # Offer one-click copy in drawer view


@dataclass
class TrayConfig:
    enabled: bool = True
    start_minimized: bool = True


@dataclass
class AppConfig:
    hotkey: HotkeyConfig = field(default_factory=HotkeyConfig)
    capture: CaptureConfig = field(default_factory=CaptureConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    delivery: DeliveryConfig = field(default_factory=DeliveryConfig)
    tray: TrayConfig = field(default_factory=TrayConfig)


DEFAULT_CONFIG = AppConfig()
