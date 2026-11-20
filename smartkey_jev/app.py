"""
SmartKey-Jev Core Application Controller.
Coordinates global hotkey, dual-channel context capture, intent convergence,
pre-warmed overlay card, slide-out result drawer, centered Spotlight launcher,
and native system tray management.
"""

import time
import threading
from typing import Optional, List
from .core.models import SelectionContext, IntentPrediction, MacroAction
from .core.config import AppConfig, DEFAULT_CONFIG
from .capture.win32_context import (
    init_dpi_awareness,
    get_cursor_position,
    get_foreground_process_info,
    get_monitor_work_area,
)
from .capture.text_extractor import TextExtractor
from .capture.hotkey_listener import GlobalHotkeyListener
from .actions.registry import DEFAULT_REGISTRY
from .actions.executor import ActionExecutor
from .actions.custom_loader import load_custom_macros
from .intent.hybrid_engine import HybridIntentEngine
from .ui.overlay import FloatingOverlay
from .ui.drawer import ResultDrawer
from .ui.spotlight import SpotlightLauncher
from .ui.tray import SystemTrayIcon


class SmartKeyApp:
    """Main desktop daemon application for SmartKey-Jev."""

    def __init__(self, config: Optional[AppConfig] = None):
        # 1. Initialize Per-Monitor V2 DPI awareness first
        init_dpi_awareness()

        self.config = config or DEFAULT_CONFIG
        self.registry = DEFAULT_REGISTRY

        # 2. Load custom user macros from ~/.smartkey_jev/macros.json
        load_custom_macros(self.registry)

        # 3. Action executor with drawer callback
        self.executor = ActionExecutor(
            config=self.config.delivery,
            drawer_callback=self._show_drawer,
        )

        self.text_extractor = TextExtractor(self.config.capture)
        self.intent_engine = HybridIntentEngine(self.config.model)

        # 4. Pre-warmed pooled UI views
        self.overlay = FloatingOverlay(
            config=self.config.ui,
            on_action_selected=self._on_action_selected,
        )
        self.drawer = ResultDrawer(config=self.config.ui)
        self.spotlight = SpotlightLauncher(
            config=self.config.ui,
            on_action_dispatched=self._on_spotlight_dispatched,
        )

        # 5. Global hotkey listener
        self.hotkey_listener = GlobalHotkeyListener(
            callback=self._on_hotkey_triggered,
            config=self.config.hotkey,
        )

        # 6. Native system tray
        self.tray = SystemTrayIcon(
            on_toggle_pause=self._on_tray_toggle_pause,
            on_toggle_hotkey=self._on_tray_toggle_hotkey,
            on_spotlight_open=self._open_spotlight_manual,
            on_exit=self.stop,
        )

        self._running = False
        self._last_shown_time = 0.0

    def _on_hotkey_triggered(self):
        """Fired when double-tap hotkey (Alt or Ctrl) is detected."""
        t_start = time.time()

        # 1. Capture cursor position
        cursor_pos = get_cursor_position()

        # 2. Capture foreground process info
        proc_name, proc_path, win_title = get_foreground_process_info()

        # 3. Capture selected text (dual-channel)
        t_before_extract = time.time()
        truncated_text, raw_text = self.text_extractor.extract()
        extract_latency = (time.time() - t_before_extract) * 1000.0

        # Branch: If NO text selected, launch centered Spotlight
        if not truncated_text or not truncated_text.strip():
            if self.config.hotkey.spotlight_on_empty:
                self.spotlight.show()
            return

        # Prepare context
        ctx = SelectionContext(
            text=truncated_text,
            raw_text=raw_text,
            process_name=proc_name,
            process_path=proc_path,
            window_title=win_title,
            cursor_position=cursor_pos,
            capture_latency_ms=round(extract_latency, 2),
        )

        # 4. Fast Two-Tier Rule Prediction (always finishes in < 1ms)
        candidates = self.registry.list_all()
        t_before_intent = time.time()
        rule_predictions = self.intent_engine.rule_engine.predict(ctx, candidates, top_k=3)
        intent_latency = (time.time() - t_before_intent) * 1000.0

        if not rule_predictions:
            return

        # 5. Instant display of pre-warmed floating card (< 3ms)
        self.overlay.show(rule_predictions, ctx, cursor_pos)
        self._last_shown_time = time.time()

        total_latency = (time.time() - t_start) * 1000.0
        print(
            f"[SmartKey-Jev] Context: '{proc_name}' | Extracted: {len(truncated_text)} chars | "
            f"Rule Intent: {[p.macro.id for p in rule_predictions]} | E2E Latency: {total_latency:.1f}ms"
        )

        # 6. Optional Async Model Re-Ranking with Visual Stabilization Lock
        if self.config.model.enabled and self.config.model.async_rerank:
            threading.Thread(
                target=self._async_model_rerank_worker,
                args=(ctx, candidates, rule_predictions),
                daemon=True,
            ).start()

    def _async_model_rerank_worker(
        self,
        ctx: SelectionContext,
        candidates: List[MacroAction],
        initial_preds: List[IntentPrediction],
    ):
        """Asynchronously queries Jev Model and applies First-Pick visual stabilization."""
        try:
            model_preds = self.intent_engine.model_engine.predict(ctx, candidates, top_k=3)
            if not model_preds:
                return

            # Check if card is still visible and user hasn't pressed a key yet
            if not self.overlay.is_visible:
                return

            # Visual Stabilization Policy (Lock Top-2 to prevent user mis-clicks)
            # Only update the 3rd candidate or badge if significantly different
            locked_top2_ids = {initial_preds[0].macro.id, initial_preds[1].macro.id}
            new_third = None
            for mp in model_preds:
                if mp.macro.id not in locked_top2_ids:
                    new_third = mp
                    break

            if new_third and len(initial_preds) >= 3:
                updated_preds = [initial_preds[0], initial_preds[1], new_third]
                # Silently refresh UI row 3
                self.overlay.show(updated_preds, ctx, ctx.cursor_position)
        except Exception as e:
            pass

    def _on_action_selected(self, prediction: IntentPrediction, context: SelectionContext):
        """Fired when user clicks or blind-types 1/2/3."""
        print(f"[SmartKey-Jev] Executing: {prediction.macro.id} ({prediction.macro.title})")
        res = self.executor.execute(prediction.macro, context)
        print(f"[SmartKey-Jev] Execution result: {res.get('status')}")

    def _on_spotlight_dispatched(self, macro: MacroAction, query_text: str):
        """Fired when user selects an action in Spotlight mode."""
        dummy_ctx = SelectionContext(
            text=query_text,
            raw_text=query_text,
            process_name="spotlight",
            window_title="Spotlight Dispatch",
        )
        self.executor.execute(macro, dummy_ctx)

    def _show_drawer(self, title: str, icon: str, content: str):
        """Callback to display drawer view beside floating window."""
        cursor_pos = get_cursor_position()
        self.drawer.show(title, icon, content, position=(cursor_pos[0] + 16, cursor_pos[1] + 16))

    def _on_tray_toggle_pause(self, is_paused: bool):
        if is_paused:
            self.hotkey_listener.pause()
            print("[SmartKey-Jev] Hotkey listening PAUSED via tray.")
        else:
            self.hotkey_listener.resume()
            print("[SmartKey-Jev] Hotkey listening RESUMED via tray.")

    def _on_tray_toggle_hotkey(self) -> str:
        current = self.config.hotkey.trigger_type
        new_key = "double_ctrl" if current == "double_alt" else "double_alt"
        self.config.hotkey.trigger_type = new_key
        self.hotkey_listener.config.trigger_type = new_key
        print(f"[SmartKey-Jev] Trigger hotkey switched to: {new_key}")
        return new_key

    def _open_spotlight_manual(self):
        self.spotlight.show()

    def run(self):
        """Starts background daemon, hotkey hook, and UI event pump."""
        self._running = True
        self.hotkey_listener.start()
        self.tray.start()

        print("==========================================================================")
        print("   SmartKey-Jev Daemon Ready (All 4 Phases Fully Integrated)")
        print(f"   • Hotkey Trigger: {self.config.hotkey.trigger_type.upper()}")
        print("   • Empty Selection: Centered Spotlight Launcher Enabled")
        print("   • Multi-Monitor: Per-Monitor V2 DPI Awareness Active")
        print("   • Delivery Modes: In-Place Replace + Drawer + External Dispatch")
        print("   • Tray Controller: Active in Windows Notification Area")
        print("==========================================================================")

        try:
            while self._running:
                self.hotkey_listener.pump_messages_once()
                self.overlay.pump()
                time.sleep(0.01)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        if not self._running:
            return
        self._running = False
        self.hotkey_listener.stop()
        self.tray.stop()
        try:
            self.overlay.root.destroy()
        except Exception:
            pass
        print("[SmartKey-Jev] Stopped cleanly. All hooks and resources released.")
