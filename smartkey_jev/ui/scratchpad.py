"""
Sticky Scratchpad Pin View.
Creates a minimalist, draggable, semi-transparent pinned desktop sticky note.
Used by the 'pin_scratchpad' macro to temporarily preserve snippets on screen.
"""

import tkinter as tk
from typing import Optional, Tuple


class StickyPinNote:
    """A floating draggable desktop sticky pin note."""

    def __init__(self, content: str, title: str = "便签", position: Optional[Tuple[int, int]] = None):
        self.root = tk.Toplevel()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.92)
        self.root.configure(bg="#1E1E2E")

        self._drag_data = {"x": 0, "y": 0}

        # Frame Container
        self.frame = tk.Frame(
            self.root,
            bg="#1E1E2E",
            bd=1,
            relief="solid",
            highlightbackground="#F9E2AF",  # Yellow pin accent
            highlightthickness=1,
        )
        self.frame.pack(fill="both", expand=True, padx=2, pady=2)

        # Draggable Header
        self.header = tk.Frame(self.frame, bg="#181825", cursor="fleur")
        self.header.pack(fill="x", padx=4, pady=(4, 2))

        self.pin_icon = tk.Label(
            self.header,
            text="📌",
            bg="#181825",
            fg="#F9E2AF",
            font=("Segoe UI", 9),
        )
        self.pin_icon.pack(side="left", padx=(2, 4))

        self.title_lbl = tk.Label(
            self.header,
            text=title,
            bg="#181825",
            fg="#CDD6F4",
            font=("Segoe UI", 8, "bold"),
            anchor="w",
        )
        self.title_lbl.pack(side="left", fill="x", expand=True)

        self.close_lbl = tk.Label(
            self.header,
            text="✕",
            bg="#181825",
            fg="#6C7086",
            font=("Segoe UI", 8, "bold"),
            cursor="hand2",
            padx=4,
        )
        self.close_lbl.pack(side="right")
        self.close_lbl.bind("<Button-1>", lambda e: self.destroy())
        self.close_lbl.bind("<Enter>", lambda e: self.close_lbl.configure(fg="#F38BA8"))
        self.close_lbl.bind("<Leave>", lambda e: self.close_lbl.configure(fg="#6C7086"))

        # Draggable binding
        for w in (self.header, self.pin_icon, self.title_lbl):
            w.bind("<Button-1>", self._start_drag)
            w.bind("<B1-Motion>", self._on_drag)

        # Content Text Area
        self.text_widget = tk.Text(
            self.frame,
            bg="#1E1E2E",
            fg="#CDD6F4",
            insertbackground="#CDD6F4",
            font=("Segoe UI Variable Text", 9),
            wrap="word",
            bd=0,
            padx=6,
            pady=4,
            relief="flat",
            height=6,
            width=28,
        )
        self.text_widget.pack(fill="both", expand=True, padx=4, pady=(0, 4))
        self.text_widget.insert(tk.END, content.strip())
        self.text_widget.configure(state="disabled")

        # Double click to copy
        self.text_widget.bind("<Double-Button-1>", self._copy_and_flash)

        # Geometry
        w = 240
        h = 140
        if position:
            x, y = position
        else:
            screen_w = self.root.winfo_screenwidth()
            x = screen_w - w - 40
            y = 80

        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def _start_drag(self, event):
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y

    def _on_drag(self, event):
        deltax = event.x - self._drag_data["x"]
        deltay = event.y - self._drag_data["y"]
        x = self.root.winfo_x() + deltax
        y = self.root.winfo_y() + deltay
        self.root.geometry(f"+{x}+{y}")

    def _copy_and_flash(self, event):
        content = self.text_widget.get("1.0", tk.END).strip()
        self.root.clipboard_clear()
        self.root.clipboard_append(content)
        self.title_lbl.configure(text="✓ 已复制到剪贴板", fg="#A6E3A1")
        self.root.after(1200, lambda: self.title_lbl.configure(text="便签", fg="#CDD6F4"))

    def destroy(self):
        try:
            self.root.destroy()
        except Exception:
            pass


class ScratchpadManager:
    """Manages active pinned sticky notes on screen."""

    def __init__(self):
        self._notes = []

    def create_pin(self, content: str, title: str = "便签", position: Optional[Tuple[int, int]] = None):
        note = StickyPinNote(content, title=title, position=position)
        self._notes.append(note)
        return note


DEFAULT_SCRATCHPAD_MANAGER = ScratchpadManager()
