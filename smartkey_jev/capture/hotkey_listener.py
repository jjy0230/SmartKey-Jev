"""
Global Low-Level Keyboard Hook & Double-Tap Alt/Ctrl State Machine.
Safely detects rapid double-tap Alt/Ctrl without triggering Windows modal Menu Loops.
Includes Fullscreen Game/Video Exemption check and dynamic pause/resume support.
"""

import time
import ctypes
from ctypes import wintypes
from typing import Callable, Optional
from ..core.config import HotkeyConfig
from .win32_context import is_foreground_fullscreen


user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105

VK_MENU = 0x12       # Alt key
VK_LMENU = 0xA4      # Left Alt
VK_RMENU = 0xA5      # Right Alt
VK_CONTROL = 0x11    # Ctrl key
VK_LCONTROL = 0xA2   # Left Ctrl
VK_RCONTROL = 0xA3   # Right Ctrl
VK_ESCAPE = 0x1B


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_ulonglong),
    ]


HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_longlong, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)


class GlobalHotkeyListener:
    """
    Listens for double-tap hotkeys (Double-Tap Alt or Double-Tap Ctrl) using SetWindowsHookEx.
    Manages key states and suppresses Windows system menu activation.
    Supports dynamic pausing/resuming and fullscreen game exemption.
    """

    def __init__(self, callback: Callable[[], None], config: Optional[HotkeyConfig] = None):
        self.callback = callback
        self.config = config or HotkeyConfig()
        self._hook = None
        self._hook_proc = None
        self._last_up_time = 0.0
        self._press_count = 0
        self._other_key_pressed = False
        self._running = False
        self._paused = False

    def is_paused(self) -> bool:
        return self._paused

    def pause(self):
        """Temporarily pause hotkey triggering without unhooking."""
        self._paused = True
        self._press_count = 0

    def resume(self):
        """Resume hotkey triggering."""
        self._paused = False
        self._press_count = 0

    def _is_target_key(self, vk: int) -> bool:
        if self.config.trigger_type == "double_alt":
            return vk in (VK_MENU, VK_LMENU, VK_RMENU)
        elif self.config.trigger_type == "double_ctrl":
            return vk in (VK_CONTROL, VK_LCONTROL, VK_RCONTROL)
        return False

    def _hook_callback(self, nCode: int, wParam: wintypes.WPARAM, lParam: wintypes.LPARAM) -> ctypes.c_longlong:
        if nCode >= 0 and not self._paused:
            kb = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
            vk = kb.vkCode
            is_target = self._is_target_key(vk)

            if wParam in (WM_KEYDOWN, WM_SYSKEYDOWN):
                if not is_target:
                    # Combination key pressed (e.g. Alt+Tab, Ctrl+C, Alt+F4)
                    self._other_key_pressed = True
                    self._press_count = 0

            elif wParam in (WM_KEYUP, WM_SYSKEYUP):
                if is_target:
                    now = time.time() * 1000.0  # current ms
                    interval = now - self._last_up_time

                    if not self._other_key_pressed and interval <= self.config.double_tap_interval_ms:
                        # Double tap detected!
                        self._press_count = 0
                        self._last_up_time = 0.0

                        # Check game / fullscreen exemption
                        if self.config.game_exemption_enabled and is_foreground_fullscreen():
                            # Pass-through: do not disturb full-screen game or video
                            return user32.CallNextHookEx(self._hook, nCode, wParam, lParam)

                        # Suppress Windows menu loop by injecting a dummy Escape key
                        if self.config.trigger_type == "double_alt" and self.config.suppress_system_menu:
                            user32.keybd_event(VK_ESCAPE, 0, 0, 0)
                            user32.keybd_event(VK_ESCAPE, 0, 0x0002, 0)

                        # Trigger application callback
                        try:
                            self.callback()
                        except Exception as e:
                            print(f"[SmartKey-Jev] Hotkey callback error: {e}")

                        # Consume this key event to avoid menu focus
                        return 1
                    else:
                        # First tap
                        self._press_count = 1
                        self._last_up_time = now
                        self._other_key_pressed = False

        return user32.CallNextHookEx(self._hook, nCode, wParam, lParam)

    def start(self):
        """Install global low-level keyboard hook."""
        if self._hook:
            return
        self._hook_proc = HOOKPROC(self._hook_callback)
        self._hook = user32.SetWindowsHookExW(
            WH_KEYBOARD_LL,
            self._hook_proc,
            kernel32.GetModuleHandleW(None),
            0,
        )
        self._running = True

    def stop(self):
        """Unhook keyboard hook."""
        if self._hook:
            user32.UnhookWindowsHookEx(self._hook)
            self._hook = None
            self._running = False

    def pump_messages_once(self):
        """Pumps Windows message loop non-blockingly."""
        msg = wintypes.MSG()
        # PM_REMOVE = 0x0001
        while user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1):
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
