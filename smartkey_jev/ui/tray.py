"""
Native Win32 System Tray Controller (Shell_NotifyIcon).
Provides a lightweight resident tray icon with right-click menu controls:
- Pause / Resume Hotkey Listening
- Toggle Trigger Key (Double-Alt / Double-Ctrl)
- Open User Config Directory
- Exit Application
"""

import os
import sys
import threading
import win32gui
import win32con
import win32api
from typing import Callable, Optional
from pathlib import Path


WM_TRAY_NOTIFY = win32con.WM_USER + 20
ID_TRAY_PAUSE_RESUME = 1001
ID_TRAY_TOGGLE_HOTKEY = 1002
ID_TRAY_OPEN_CONFIG = 1003
ID_TRAY_OPEN_GITHUB = 1004
ID_TRAY_EXIT = 1005


class SystemTrayIcon:
    """
    Zero-overhead native Windows Taskbar Notification Tray Icon.
    Runs on its own dedicated message pump thread.
    """

    def __init__(
        self,
        on_toggle_pause: Optional[Callable[[bool], None]] = None,
        on_toggle_hotkey: Optional[Callable[[], str]] = None,
        on_spotlight_open: Optional[Callable[[], None]] = None,
        on_exit: Optional[Callable[[], None]] = None,
    ):
        self.on_toggle_pause = on_toggle_pause
        self.on_toggle_hotkey = on_toggle_hotkey
        self.on_spotlight_open = on_spotlight_open
        self.on_exit = on_exit

        self._is_paused = False
        self._current_hotkey_label = "双击 Alt"
        self._hwnd = None
        self._thread = None
        self._running = False

    def start(self):
        """Spawns the tray message loop in a background thread."""
        self._running = True
        self._thread = threading.Thread(target=self._run_tray_thread, daemon=True)
        self._thread.start()

    def _run_tray_thread(self):
        message_map = {
            win32con.WM_DESTROY: self._on_destroy,
            win32con.WM_COMMAND: self._on_command,
            WM_TRAY_NOTIFY: self._on_tray_notify,
        }

        wc = win32gui.WNDCLASS()
        hinst = wc.hInstance = win32api.GetModuleHandle(None)
        wc.lpszClassName = "SmartKeyJevTrayWnd"
        wc.style = win32con.CS_VREDRAW | win32con.CS_HREDRAW
        wc.hCursor = win32gui.LoadCursor(0, win32con.IDC_ARROW)
        wc.hbrBackground = win32con.COLOR_WINDOW
        wc.lpfnWndProc = message_map

        try:
            class_atom = win32gui.RegisterClass(wc)
        except Exception:
            class_atom = win32gui.GetClassInfo(hinst, "SmartKeyJevTrayWnd")

        style = win32con.WS_OVERLAPPED | win32con.WS_SYSMENU
        self._hwnd = win32gui.CreateWindow(
            wc.lpszClassName,
            "SmartKeyJevTray",
            style,
            0, 0,
            win32con.CW_USEDEFAULT,
            win32con.CW_USEDEFAULT,
            0, 0, hinst, None,
        )
        win32gui.UpdateWindow(self._hwnd)

        # Standard system application icon
        hicon = win32gui.LoadIcon(0, win32con.IDI_APPLICATION)

        flags = win32gui.NIF_ICON | win32gui.NIF_MESSAGE | win32gui.NIF_TIP
        nid = (self._hwnd, 0, flags, WM_TRAY_NOTIFY, hicon, "SmartKey-Jev (全局即时意图调度器)")
        win32gui.Shell_NotifyIcon(win32gui.NIM_ADD, nid)

        # Win32 pump
        win32gui.PumpMessages()

    def _on_destroy(self, hwnd, msg, wparam, lparam):
        nid = (self._hwnd, 0)
        win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, nid)
        win32gui.PostQuitMessage(0)
        return 0

    def _on_tray_notify(self, hwnd, msg, wparam, lparam):
        if lparam == win32con.WM_RBUTTONUP:
            self._show_context_menu()
        elif lparam == win32con.WM_LBUTTONDBLCLK:
            if self.on_spotlight_open:
                self.on_spotlight_open()
        return 1

    def _show_context_menu(self):
        menu = win32gui.CreatePopupMenu()

        status_text = "▶ 恢复监听" if self._is_paused else "⏸ 暂停监听"
        win32gui.AppendMenu(menu, win32con.MF_STRING, ID_TRAY_PAUSE_RESUME, status_text)

        hotkey_menu_text = f"⚙ 快捷键: {self._current_hotkey_label} (点击切换)"
        win32gui.AppendMenu(menu, win32con.MF_STRING, ID_TRAY_TOGGLE_HOTKEY, hotkey_menu_text)

        win32gui.AppendMenu(menu, win32con.MF_SEPARATOR, 0, "")
        win32gui.AppendMenu(menu, win32con.MF_STRING, ID_TRAY_OPEN_CONFIG, "📁 打开自定义配置目录")
        win32gui.AppendMenu(menu, win32con.MF_STRING, ID_TRAY_OPEN_GITHUB, "🌐 GitHub 仓库开源页")
        win32gui.AppendMenu(menu, win32con.MF_SEPARATOR, 0, "")
        win32gui.AppendMenu(menu, win32con.MF_STRING, ID_TRAY_EXIT, "✕ 退出 SmartKey-Jev")

        pos = win32gui.GetCursorPos()
        win32gui.SetForegroundWindow(self._hwnd)
        win32gui.TrackPopupMenu(
            menu,
            win32con.TPM_LEFTALIGN | win32con.TPM_RIGHTBUTTON,
            pos[0], pos[1], 0, self._hwnd, None
        )
        win32gui.PostMessage(self._hwnd, win32con.WM_NULL, 0, 0)

    def _on_command(self, hwnd, msg, wparam, lparam):
        cmd = win32api.LOWORD(wparam)
        if cmd == ID_TRAY_PAUSE_RESUME:
            self._is_paused = not self._is_paused
            if self.on_toggle_pause:
                self.on_toggle_pause(self._is_paused)

        elif cmd == ID_TRAY_TOGGLE_HOTKEY:
            if self.on_toggle_hotkey:
                new_key = self.on_toggle_hotkey()
                self._current_hotkey_label = "双击 Ctrl" if "ctrl" in new_key else "双击 Alt"

        elif cmd == ID_TRAY_OPEN_CONFIG:
            cfg_dir = Path.home() / ".smartkey_jev"
            cfg_dir.mkdir(parents=True, exist_ok=True)
            os.startfile(str(cfg_dir))

        elif cmd == ID_TRAY_OPEN_GITHUB:
            import webbrowser
            webbrowser.open("https://github.com/jjy0230/SmartKey-Jev")

        elif cmd == ID_TRAY_EXIT:
            if self.on_exit:
                self.on_exit()
            win32gui.DestroyWindow(self._hwnd)

        return 0

    def stop(self):
        self._running = False
        if self._hwnd:
            win32gui.PostMessage(self._hwnd, win32con.WM_CLOSE, 0, 0)
