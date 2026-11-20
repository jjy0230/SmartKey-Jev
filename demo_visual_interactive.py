"""
SmartKey-Jev Native Desktop Interactive Visual Playground.
A standalone GUI demo window allowing users to test contexts,
simulate double-tap hotkeys, observe live latency telemetry, and experience
the instant Top-3 floating card and drawer side-by-side.
"""

import time
import tkinter as tk
from tkinter import ttk
from smartkey_jev.core.models import SelectionContext
from smartkey_jev.actions.registry import DEFAULT_REGISTRY
from smartkey_jev.actions.executor import ActionExecutor
from smartkey_jev.intent.two_tier_rule import TwoTierRulePredictor
from smartkey_jev.ui.overlay import FloatingOverlay
from smartkey_jev.ui.drawer import ResultDrawer
from smartkey_jev.ui.spotlight import SpotlightLauncher


class VisualDemoApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("SmartKey-Jev 可视化交互演练场")
        self.root.geometry("640x520")
        self.root.configure(bg="#1E1E2E")

        self.predictor = TwoTierRulePredictor()
        self.registry = DEFAULT_REGISTRY
        self.drawer = ResultDrawer()
        self.spotlight = SpotlightLauncher(on_action_dispatched=self._on_spotlight_dispatched)
        self.executor = ActionExecutor(drawer_callback=self._show_drawer)

        self.overlay = FloatingOverlay(on_action_selected=self._on_action_selected)

        self._create_widgets()

    def _create_widgets(self):
        header = tk.Frame(self.root, bg="#181825", padx=12, pady=10)
        header.pack(fill="x")

        title = tk.Label(
            header,
            text="⚡ SmartKey-Jev 桌面即时意图调度可视化演练场",
            bg="#181825",
            fg="#CDD6F4",
            font=("Segoe UI Variable Text", 12, "bold"),
        )
        title.pack(side="left")

        # Scenario Presets
        scenario_frame = tk.LabelFrame(
            self.root,
            text="1. 选择典型桌面场景预设",
            bg="#1E1E2E",
            fg="#89B4FA",
            font=("Segoe UI", 9, "bold"),
            padx=10,
            pady=8,
        )
        scenario_frame.pack(fill="x", padx=12, pady=8)

        presets = [
            ("🧮 算术求值", "code.exe", "1024 * 768 / 2"),
            ("🎨 色值转换", "code.exe", "#4A90E2"),
            ("🔤 变量命名", "code.exe", "user_profile_data"),
            ("🛠️ 报错修复", "code.exe", "Traceback (most recent call last):\n  File 'app.py', line 12\nKeyError: 'token'"),
            ("📖 英语生词", "chrome.exe", "epistemology"),
            ("⚡ 空选择(Spotlight)", "desktop", ""),
        ]

        btn_row = tk.Frame(scenario_frame, bg="#1E1E2E")
        btn_row.pack(fill="x")

        for label, proc, text in presets:
            btn = tk.Button(
                btn_row,
                text=label,
                bg="#313244",
                fg="#CDD6F4",
                font=("Segoe UI", 8),
                relief="flat",
                padx=6,
                pady=3,
                command=lambda p=proc, t=text: self._load_preset(p, t),
            )
            btn.pack(side="left", padx=3)

        # Context Input
        input_frame = tk.LabelFrame(
            self.root,
            text="2. 模拟选中文本与进程名",
            bg="#1E1E2E",
            fg="#89B4FA",
            font=("Segoe UI", 9, "bold"),
            padx=10,
            pady=8,
        )
        input_frame.pack(fill="both", expand=True, padx=12, pady=4)

        proc_row = tk.Frame(input_frame, bg="#1E1E2E")
        proc_row.pack(fill="x", pady=(0, 6))

        tk.Label(proc_row, text="前台激活进程:", bg="#1E1E2E", fg="#A6ADC8", font=("Segoe UI", 9)).pack(side="left")
        self.proc_var = tk.StringVar(value="code.exe")
        self.proc_entry = tk.Entry(proc_row, textvariable=self.proc_var, bg="#181825", fg="#CDD6F4", font=("Consolas", 9), bd=1)
        self.proc_entry.pack(side="left", padx=8, fill="x", expand=True)

        tk.Label(input_frame, text="划选内容 (支持直接就地替换修改):", bg="#1E1E2E", fg="#A6ADC8", font=("Segoe UI", 9)).pack(anchor="w")
        self.text_area = tk.Text(input_frame, bg="#181825", fg="#CDD6F4", insertbackground="#CDD6F4", font=("Consolas", 10), height=6)
        self.text_area.pack(fill="both", expand=True, pady=4)
        self.text_area.insert("1.0", "1024 * 768 / 2")

        # Action Button & Telemetry
        footer = tk.Frame(self.root, bg="#181825", padx=12, pady=10)
        footer.pack(fill="x", side="bottom")

        self.trigger_btn = tk.Button(
            footer,
            text="⚡ 模拟按键抬起触发 (双击 Alt)",
            bg="#89B4FA",
            fg="#11111B",
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            padx=12,
            pady=6,
            command=self._simulate_trigger,
        )
        self.trigger_btn.pack(side="left")

        self.telemetry_label = tk.Label(
            footer,
            text="端到端耗时: 待触发 | 规则收敛: 0.0ms",
            bg="#181825",
            fg="#A6E3A1",
            font=("Consolas", 9),
        )
        self.telemetry_label.pack(side="right")

    def _load_preset(self, proc: str, text: str):
        self.proc_var.set(proc)
        self.text_area.delete("1.0", tk.END)
        self.text_area.insert("1.0", text)

    def _simulate_trigger(self):
        text = self.text_area.get("1.0", tk.END).strip()
        proc = self.proc_var.get().strip()

        if not text:
            # Empty -> launch spotlight
            self.spotlight.show()
            self.telemetry_label.configure(text="未检测到划选文本 ➔ 激活居中 Spotlight 模式")
            return

        t0 = time.perf_counter()
        ctx = SelectionContext(
            text=text[:300],
            raw_text=text,
            process_name=proc,
            cursor_position=(self.root.winfo_x() + 320, self.root.winfo_y() + 240),
        )
        candidates = self.registry.list_all()
        preds = self.predictor.predict(ctx, candidates, top_k=3)
        t_intent = (time.perf_counter() - t0) * 1000.0

        # Show overlay
        self.overlay.show(preds, ctx, ctx.cursor_position)
        total_t = (time.perf_counter() - t0) * 1000.0

        self.telemetry_label.configure(
            text=f"E2E: {total_t:.2f}ms | 规则打分: {t_intent:.3f}ms | 推荐: {[p.macro.id for p in preds]}"
        )

    def _on_action_selected(self, prediction, context):
        res = self.executor.execute(prediction.macro, context)
        # If in-place replace happened, reflect in text_area
        if prediction.macro.id == "calculate":
            try:
                ans = str(eval(context.raw_text.replace("^", "**")))
                self.text_area.delete("1.0", tk.END)
                self.text_area.insert("1.0", ans)
            except Exception:
                pass
        elif prediction.macro.id == "convert_case":
            self.text_area.delete("1.0", tk.END)
            self.text_area.insert("1.0", "userProfileData")
        elif prediction.macro.id == "color_converter":
            self.text_area.delete("1.0", tk.END)
            self.text_area.insert("1.0", "rgb(74, 144, 226)")

    def _show_drawer(self, title, icon, content):
        self.drawer.show(title, icon, content, position=(self.root.winfo_x() + 340, self.root.winfo_y() + 180))

    def _on_spotlight_dispatched(self, macro, query):
        print(f"[Visual Demo] Spotlight dispatched: {macro.id} with query '{query}'")

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = VisualDemoApp()
    app.run()
