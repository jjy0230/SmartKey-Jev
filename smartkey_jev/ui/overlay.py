"""
Instant Overlay Floating Card.
Implements window pooling and zero-latency display near the mouse cursor.
Supports blind typing numbers 1 / 2 / 3, Esc to dismiss, and click-to-execute.
"""

import sys
import tkinter as tk
from typing import List, Callable, Optional, Tuple
from ..core.models import IntentPrediction, SelectionContext
from ..core.config import UIConfig


class FloatingOverlay:
    """
    Ultra-low-latency floating window positioned near mouse cursor.
    Uses pre-warmed pooled window (hidden, never re-instantiated) to guarantee < 5ms rendering.
    """

    def __init__(
        self,
        config: Optional[UIConfig] = None,
        on_action_selected: Optional[Callable[[IntentPrediction, SelectionContext], None]] = None,
    ):
        self.config = config or UIConfig()
        self.on_action_selected = on_action_selected
        self._current_context: Optional[SelectionContext] = None
        self._current_predictions: List[IntentPrediction] = []

        # Initialize Tkinter pooled root
        self.root = tk.Tk()
        self._setup_window()
        self._create_widgets()
        self._bind_events()

        # Keep hidden initially
        self.root.withdraw()
        self.is_visible = False

    def _setup_window(self):
        self.root.overrideredirect(True)                # Borderless
        self.root.attributes("-topmost", True)          # Always on top
        self.root.attributes("-alpha", self.config.opacity) # Semi-transparent
        self.root.configure(bg="#1E1E2E")               # Sleek dark palette (Catppuccin Mocha style)

    def _create_widgets(self):
        # Container frame
        self.container = tk.Frame(self.root, bg="#1E1E2E", bd=1, relief="solid", highlightbackground="#45475A", highlightthickness=1)
        self.container.pack(fill="both", expand=True, padx=2, pady=2)

        # Header: Process badge & title
        self.header_frame = tk.Frame(self.container, bg="#181825")
        self.header_frame.pack(fill="x", padx=4, pady=(4, 2))

        self.proc_badge = tk.Label(
            self.header_frame,
            text="APP",
            bg="#89B4FA",
            fg="#11111B",
            font=(self.config.font_family, 8, "bold"),
            padx=4,
            pady=1,
        )
        self.proc_badge.pack(side="left", padx=(2, 6))

        self.snippet_label = tk.Label(
            self.header_frame,
            text="",
            bg="#181825",
            fg="#A6ADC8",
            font=(self.config.font_family, 8),
            anchor="w",
        )
        self.snippet_label.pack(side="left", fill="x", expand=True)

        # 3 Prediction Rows
        self.row_frames = []
        self.badge_labels = []
        self.title_labels = []
        self.prob_labels = []

        for i in range(3):
            rf = tk.Frame(self.container, bg="#1E1E2E", cursor="hand2")
            rf.pack(fill="x", padx=4, pady=2)

            num_badge = tk.Label(
                rf,
                text=str(i + 1),
                bg="#313244",
                fg="#CDD6F4",
                font=(self.config.font_family, 9, "bold"),
                width=2,
            )
            num_badge.pack(side="left", padx=(2, 6), pady=2)

            title_lbl = tk.Label(
                rf,
                text=f"Action {i + 1}",
                bg="#1E1E2E",
                fg="#CDD6F4",
                font=(self.config.font_family, 10),
                anchor="w",
            )
            title_lbl.pack(side="left", fill="x", expand=True)

            prob_lbl = tk.Label(
                rf,
                text="0%",
                bg="#1E1E2E",
                fg="#6C7086",
                font=(self.config.font_family, 8),
            )
            prob_lbl.pack(side="right", padx=(2, 6))

            # Bind hover effect and click
            idx = i
            for w in (rf, num_badge, title_lbl, prob_lbl):
                w.bind("<Enter>", lambda e, f=rf: f.configure(bg="#313244"))
                w.bind("<Leave>", lambda e, f=rf: f.configure(bg="#1E1E2E"))
                w.bind("<Button-1>", lambda e, k=idx: self._trigger_index(k))

            self.row_frames.append(rf)
            self.badge_labels.append(num_badge)
            self.title_labels.append(title_lbl)
            self.prob_labels.append(prob_lbl)

    def _bind_events(self):
        # Keyboard blind-typing triggers
        self.root.bind("1", lambda e: self._trigger_index(0))
        self.root.bind("2", lambda e: self._trigger_index(1))
        self.root.bind("3", lambda e: self._trigger_index(2))
        self.root.bind("<Escape>", lambda e: self.hide())
        self.root.bind("<FocusOut>", lambda e: self.hide())

    def _trigger_index(self, index: int):
        if index < len(self._current_predictions) and self._current_context:
            pred = self._current_predictions[index]
            ctx = self._current_context
            self.hide()
            if self.on_action_selected:
                self.on_action_selected(pred, ctx)

    def show(
        self,
        predictions: List[IntentPrediction],
        context: SelectionContext,
        cursor_pos: Optional[Tuple[int, int]] = None,
    ):
        """Pre-warmed instant show call (< 3ms)."""
        if not predictions:
            return

        self._current_predictions = predictions
        self._current_context = context

        # Update process badge & text preview
        proc_disp = context.process_name.replace(".exe", "").upper()[:12]
        self.proc_badge.configure(text=proc_disp)
        preview_text = context.text.replace("\n", " ").strip()
        self.snippet_label.configure(text=f'"{preview_text[:28]}..."' if len(preview_text) > 28 else f'"{preview_text}"')

        # Update top-3 rows
        colors = ["#A6E3A1", "#F9E2AF", "#89B4FA"]  # Catppuccin Green, Yellow, Blue
        for i in range(3):
            if i < len(predictions):
                pred = predictions[i]
                self.title_labels[i].configure(text=f"{pred.macro.icon} {pred.macro.title}")
                self.prob_labels[i].configure(text=f"{int(pred.confidence * 100)}%")
                self.badge_labels[i].configure(fg=colors[i % len(colors)])
                self.row_frames[i].pack(fill="x", padx=4, pady=2)
            else:
                self.row_frames[i].pack_forget()

        # Compute position near cursor (offset slightly to right & down so mouse doesn't cover)
        x, y = cursor_pos or context.cursor_position
        x += 16
        y += 16

        # Screen boundary clamp
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        w = self.config.width
        h = self.config.height

        if x + w > screen_w:
            x = screen_w - w - 10
        if y + h > screen_h:
            y = screen_h - h - 10

        self.root.geometry(f"{w}x{h}+{x}+{y}")
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        self.is_visible = True

    def hide(self):
        """Withdraw window without destroying it."""
        if self.is_visible:
            self.root.withdraw()
            self.is_visible = False

    def pump(self):
        """Update idle tasks and process UI events non-blockingly."""
        self.root.update_idletasks()
        self.root.update()
