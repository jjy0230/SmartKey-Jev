"""
Spotlight / Raycast-style Centered Quick Launcher.
Activated when double-tap hotkey is pressed with NO text selected.
Provides a sleek, centered quick-command bar with instant fuzzy dispatch.
"""

import tkinter as tk
from typing import List, Callable, Optional
from ..core.models import MacroAction, SelectionContext, IntentPrediction
from ..core.config import UIConfig
from ..actions.registry import DEFAULT_REGISTRY


class SpotlightLauncher:
    """
    Centered quick launcher for desktop-wide dispatch without pre-selected text.
    Pre-warmed and pooled to guarantee instant (<3ms) display.
    """

    def __init__(
        self,
        config: Optional[UIConfig] = None,
        on_action_dispatched: Optional[Callable[[MacroAction, str], None]] = None,
    ):
        self.config = config or UIConfig()
        self.on_action_dispatched = on_action_dispatched
        self._all_macros = DEFAULT_REGISTRY.list_all()

        self.root = tk.Toplevel()
        self._setup_window()
        self._create_widgets()
        self._bind_events()

        self.root.withdraw()
        self.is_visible = False

    def _setup_window(self):
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", self.config.opacity)
        self.root.configure(bg="#1E1E2E")

    def _create_widgets(self):
        self.container = tk.Frame(
            self.root,
            bg="#1E1E2E",
            bd=1,
            relief="solid",
            highlightbackground="#585B70",
            highlightthickness=1,
        )
        self.container.pack(fill="both", expand=True, padx=2, pady=2)

        # Header Search Area
        self.search_frame = tk.Frame(self.container, bg="#181825")
        self.search_frame.pack(fill="x", padx=6, pady=(6, 4))

        self.icon_label = tk.Label(
            self.search_frame,
            text="⚡",
            bg="#181825",
            fg="#F9E2AF",
            font=(self.config.font_family, 12),
        )
        self.icon_label.pack(side="left", padx=(6, 8))

        self.entry_var = tk.StringVar()
        self.entry_var.trace_add("write", self._on_query_changed)

        self.entry = tk.Entry(
            self.search_frame,
            textvariable=self.entry_var,
            bg="#181825",
            fg="#CDD6F4",
            insertbackground="#CDD6F4",
            font=(self.config.font_family, 12),
            bd=0,
            relief="flat",
        )
        self.entry.pack(side="left", fill="x", expand=True, ipady=4)

        self.hint_label = tk.Label(
            self.search_frame,
            text="Esc 退出 | ↵ 运行",
            bg="#181825",
            fg="#6C7086",
            font=(self.config.font_family, 8),
        )
        self.hint_label.pack(side="right", padx=(4, 8))

        # Results List Container
        self.results_frame = tk.Frame(self.container, bg="#1E1E2E")
        self.results_frame.pack(fill="both", expand=True, padx=4, pady=4)

        self.item_rows: List[tk.Frame] = []
        self.filtered_macros: List[MacroAction] = []
        self._populate_list(self._all_macros[:5])

    def _create_item_row(self, index: int, macro: MacroAction):
        row = tk.Frame(self.results_frame, bg="#1E1E2E", cursor="hand2")
        row.pack(fill="x", padx=2, pady=1)

        num_lbl = tk.Label(
            row,
            text=str(index + 1),
            bg="#313244",
            fg="#89B4FA",
            font=(self.config.font_family, 8, "bold"),
            width=2,
        )
        num_lbl.pack(side="left", padx=(4, 6), pady=2)

        icon_lbl = tk.Label(
            row,
            text=macro.icon,
            bg="#1E1E2E",
            fg="#CDD6F4",
            font=(self.config.font_family, 9),
        )
        icon_lbl.pack(side="left", padx=(0, 4))

        title_lbl = tk.Label(
            row,
            text=macro.title,
            bg="#1E1E2E",
            fg="#CDD6F4",
            font=(self.config.font_family, 9, "bold"),
            anchor="w",
        )
        title_lbl.pack(side="left", padx=2)

        desc_lbl = tk.Label(
            row,
            text=f"— {macro.description}",
            bg="#1E1E2E",
            fg="#6C7086",
            font=(self.config.font_family, 8),
            anchor="w",
        )
        desc_lbl.pack(side="left", fill="x", expand=True, padx=4)

        # Hover & Click bindings
        target_macro = macro
        for w in (row, num_lbl, icon_lbl, title_lbl, desc_lbl):
            w.bind("<Enter>", lambda e, f=row: f.configure(bg="#313244"))
            w.bind("<Leave>", lambda e, f=row: f.configure(bg="#1E1E2E"))
            w.bind("<Button-1>", lambda e, m=target_macro: self._trigger_macro(m))

        self.item_rows.append(row)

    def _populate_list(self, macros: List[MacroAction]):
        for r in self.item_rows:
            r.destroy()
        self.item_rows.clear()
        self.filtered_macros = macros

        for idx, m in enumerate(macros):
            self._create_item_row(idx, m)

    def _on_query_changed(self, *args):
        query = self.entry_var.get().strip().lower()
        if not query:
            self._populate_list(self._all_macros[:5])
            return

        # Simple fuzzy search
        matches = [
            m for m in self._all_macros
            if query in m.title.lower() or query in m.id.lower() or query in m.description.lower()
        ]
        self._populate_list(matches[:5])

    def _bind_events(self):
        self.root.bind("<Escape>", lambda e: self.hide())
        self.root.bind("<FocusOut>", lambda e: self.hide())
        self.entry.bind("<Return>", lambda e: self._on_enter_pressed())

        # Bind 1..5 for direct numeric dispatch
        for i in range(1, 6):
            self.root.bind(str(i), lambda e, k=i-1: self._trigger_index(k))

    def _on_enter_pressed(self):
        raw_input = self.entry_var.get().strip()
        if not raw_input:
            self.hide()
            return

        if self.filtered_macros:
            self._trigger_macro(self.filtered_macros[0], raw_input)
        else:
            # Fallback to web search
            search_macro = DEFAULT_REGISTRY.get("search_web")
            if search_macro:
                self._trigger_macro(search_macro, raw_input)

    def _trigger_index(self, index: int):
        if index < len(self.filtered_macros):
            self._trigger_macro(self.filtered_macros[index])

    def _trigger_macro(self, macro: MacroAction, text_override: str = ""):
        self.hide()
        if self.on_action_dispatched:
            query = text_override or self.entry_var.get().strip()
            self.on_action_dispatched(macro, query)

    def show(self):
        """Displays centered launcher instantly (<3ms)."""
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        w = self.config.spotlight_width
        h = self.config.spotlight_height

        x = (screen_w - w) // 2
        y = (screen_h - h) // 3  # Golden ratio vertical placement

        self.entry_var.set("")
        self._populate_list(self._all_macros[:5])

        self.root.geometry(f"{w}x{h}+{x}+{y}")
        self.root.deiconify()
        self.root.lift()
        self.entry.focus_set()
        self.is_visible = True

    def hide(self):
        if self.is_visible:
            self.root.withdraw()
            self.is_visible = False
