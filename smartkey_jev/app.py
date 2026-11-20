"""
SmartKey-Jev Core Application Controller.
Coordinates global hotkey, dual-channel context capture, intent convergence,
pre-warmed overlay card display, and macro execution.
"""

import time
import threading
from typing import Optional
from .core.models import SelectionContext, IntentPrediction
from .core.config import AppConfig, DEFAULT_CONFIG
from .capture.win32_context import get_cursor_position, get_foreground_process_info
from .capture.text_extractor import TextExtractor
from .capture.hotkey_listener import GlobalHotkeyListener
from .actions.registry import DEFAULT_REGISTRY, MacroRegistry
from .actions.executor import ActionExecutor
from .intent.hybrid_engine import HybridIntentEngine
from .ui.overlay import FloatingOverlay


class SmartKeyApp:
    """Main desktop daemon application for SmartKey-Jev."""

    def __init__(self, config: Optional[AppConfig] = None):
        self.config = config or DEFAULT_CONFIG
        self.registry = DEFAULT_REGISTRY
        self.executor = ActionExecutor()
        self.text_extractor = TextExtractor(self.config.capture)
        self.intent_engine = HybridIntentEngine(self.config.model)
        
        self.overlay = FloatingOverlay(
            config=self.config.ui,
            on_action_selected=self._on_action_selected,
        )

        self.hotkey_listener = GlobalHotkeyListener(
            callback=self._on_hotkey_triggered,
            config=self.config.hotkey,
        )

        self._running = False

    def _on_hotkey_triggered(self):
        """Fired in low-level hook thread when double-tap hotkey (e.g. Double Alt) is detected."""
        t_start = time.time()

        # 1. Capture cursor position
        cursor_pos = get_cursor_position()

        # 2. Capture foreground process metadata
        proc_name, proc_path, win_title = get_foreground_process_info()

        # 3. Capture selected text snippet (dual-channel)
        t_before_extract = time.time()
        truncated_text, raw_text = self.text_extractor.extract()
        extract_latency = (time.time() - t_before_extract) * 1000.0

        if not truncated_text:
            # If no text selected, fallback to empty prompt or skip
            return

        ctx = SelectionContext(
            text=truncated_text,
            raw_text=raw_text,
            process_name=proc_name,
            process_path=proc_path,
            window_title=win_title,
            cursor_position=cursor_pos,
            capture_latency_ms=round(extract_latency, 2),
        )

        # 4. Intent convergence
        t_before_intent = time.time()
        candidates = self.registry.list_all()
        predictions = self.intent_engine.predict(ctx, candidates, top_k=3)
        intent_latency = (time.time() - t_before_intent) * 1000.0

        if not predictions:
            return

        # 5. Display overlay card
        self.overlay.show(predictions, ctx, cursor_pos)

        total_latency = (time.time() - t_start) * 1000.0
        print(
            f"[SmartKey-Jev] Context: '{proc_name}' | Extracted: {len(truncated_text)} chars | "
            f"Intent: {[p.macro.id for p in predictions]} | E2E Latency: {total_latency:.1f}ms "
            f"(Extract: {extract_latency:.1f}ms, Intent: {intent_latency:.1f}ms)"
        )

    def _on_action_selected(self, prediction: IntentPrediction, context: SelectionContext):
        """Called when user picks an action via numbers 1/2/3 or mouse click."""
        print(f"[SmartKey-Jev] Executing: {prediction.macro.id} ({prediction.macro.title})")
        res = self.executor.execute(prediction.macro, context)
        print(f"[SmartKey-Jev] Result: {res}")

    def run(self):
        """Run application loop."""
        self._running = True
        self.hotkey_listener.start()
        print("[SmartKey-Jev] Service started. Listening for Double-Tap Alt...")
        print("[SmartKey-Jev] Select text anywhere on Windows and double-tap Alt to trigger.")

        try:
            while self._running:
                # Pump both Win32 messages and UI loop
                self.hotkey_listener.pump_messages_once()
                self.overlay.pump()
                time.sleep(0.01)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        self._running = False
        self.hotkey_listener.stop()
        try:
            self.overlay.root.destroy()
        except Exception:
            pass
        print("[SmartKey-Jev] Service stopped cleanly.")
