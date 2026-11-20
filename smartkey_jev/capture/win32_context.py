"""
Win32 Foreground Process, Display Monitors, and Context Extractor.
Extracts active process name, window title, monitor work area, and cursor position via native Win32 APIs.
Includes Per-Monitor V2 DPI Awareness and Fullscreen Game/Video Exemption detection.
"""

import os
import ctypes
from ctypes import wintypes
from typing import Tuple, Optional


user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
psapi = ctypes.windll.psapi


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


class MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", RECT),
        ("rcWork", RECT),
        ("dwFlags", wintypes.DWORD),
    ]


# DPI Awareness Contexts
DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = ctypes.c_void_p(-4)


def init_dpi_awareness():
    """
    Initializes Windows Per-Monitor V2 DPI awareness.
    Must be called before creating any UI windows to prevent multi-monitor drift and blurriness.
    """
    try:
        if hasattr(user32, "SetProcessDpiAwarenessContext"):
            user32.SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2)
        elif hasattr(ctypes.windll.shcore, "SetProcessDpiAwareness"):
            # PROCESS_PER_MONITOR_DPI_AWARE = 2
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        else:
            user32.SetProcessDPIAware()
    except Exception as e:
        # Graceful fallback if OS version does not support Per-Monitor V2
        pass


def get_cursor_position() -> Tuple[int, int]:
    """Returns the current mouse cursor screen physical coordinates (x, y)."""
    pt = POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    return int(pt.x), int(pt.y)


def get_monitor_work_area(x: int, y: int) -> Tuple[int, int, int, int]:
    """
    Returns (left, top, right, bottom) of the display monitor work area (excluding taskbar)
    corresponding to the given coordinates (x, y).
    """
    pt = POINT(x, y)
    # MONITOR_DEFAULTTONEAREST = 2
    h_monitor = user32.MonitorFromPoint(pt, 2)
    if not h_monitor:
        screen_w = user32.GetSystemMetrics(0)
        screen_h = user32.GetSystemMetrics(1)
        return 0, 0, screen_w, screen_h

    mi = MONITORINFO()
    mi.cbSize = ctypes.sizeof(MONITORINFO)
    if user32.GetMonitorInfoW(h_monitor, ctypes.byref(mi)):
        return (
            int(mi.rcWork.left),
            int(mi.rcWork.top),
            int(mi.rcWork.right),
            int(mi.rcWork.bottom),
        )

    screen_w = user32.GetSystemMetrics(0)
    screen_h = user32.GetSystemMetrics(1)
    return 0, 0, screen_w, screen_h


class GUITHREADINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("hwndActive", wintypes.HWND),
        ("hwndFocus", wintypes.HWND),
        ("hwndCapture", wintypes.HWND),
        ("hwndMenuOwner", wintypes.HWND),
        ("hwndMoveSize", wintypes.HWND),
        ("hwndCaret", wintypes.HWND),
        ("rcCaret", RECT),
    ]


def is_foreground_fullscreen() -> bool:
    """
    Detects if the active foreground window is in exclusive fullscreen mode
    (e.g., DirectX/Vulkan games, full-screen video players).
    Used to exempt hotkey triggering to avoid dropping games out of fullscreen.
    """
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return False

    desktop_hwnd = user32.GetDesktopWindow()
    shell_hwnd = user32.GetShellWindow()
    if hwnd in (desktop_hwnd, shell_hwnd):
        return False

    rect = RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return False

    h_monitor = user32.MonitorFromWindow(hwnd, 2)
    if not h_monitor:
        return False

    mi = MONITORINFO()
    mi.cbSize = ctypes.sizeof(MONITORINFO)
    if not user32.GetMonitorInfoW(h_monitor, ctypes.byref(mi)):
        return False

    mon = mi.rcMonitor
    is_fullscreen = (
        rect.left <= mon.left and
        rect.top <= mon.top and
        rect.right >= mon.right and
        rect.bottom >= mon.bottom
    )

    if not is_fullscreen:
        return False

    style = user32.GetWindowLongW(hwnd, -16)
    WS_CAPTION = 0x00C00000
    if (style & WS_CAPTION) == WS_CAPTION:
        return False

    return True


def is_target_window_readonly() -> bool:
    """
    Detects if the foreground window or focused control is read-only (non-editable).
    Uses Win32 GUI Thread Info caret inspection and window class heuristics.
    Used to automatically fall back to drawer presentation instead of broken in-place pasting.
    """
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return True

    # 1. Inspect Caret visibility across thread
    gui_info = GUITHREADINFO()
    gui_info.cbSize = ctypes.sizeof(GUITHREADINFO)
    tid = user32.GetWindowThreadProcessId(hwnd, None)
    if user32.GetGUIThreadInfo(tid, ctypes.byref(gui_info)):
        # If there is an active blinking caret, it's definitely editable
        if gui_info.hwndCaret and gui_info.hwndCaret != 0:
            return False

    # 2. Check window class name heuristics
    class_buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, class_buf, 256)
    cls_name = class_buf.value.lower()

    # Known code editors that might not expose classic Win32 carets via GUIThreadInfo
    editable_classes = ["vscode", "sunawtframe", "sublime", "notepad", "scintilla"]
    if any(ec in cls_name for ec in editable_classes):
        return False

    # Standard browsers with page focus (non-input fields) are predominantly read-only
    browser_classes = ["chrome_widgetwin", "mozillawindowclass", "edge"]
    if any(bc in cls_name for bc in browser_classes):
        return True

    # 3. Check standard Win32 Edit control style: ES_READONLY = 0x0800
    style = user32.GetWindowLongW(hwnd, -16)
    ES_READONLY = 0x0800
    if (style & ES_READONLY) == ES_READONLY:
        return True

    return False


def is_foreground_elevated() -> bool:
    """
    Checks if the active foreground process has elevated Administrator privileges
    which may block UIPI simulated keystrokes from standard user processes.
    """
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return False

    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if pid.value == 0:
        return False

    h_process = kernel32.OpenProcess(0x1000, False, pid.value)
    if not h_process:
        return True  # If OpenProcess fails with access denied, it's almost certainly elevated

    h_token = wintypes.HANDLE()
    # TOKEN_QUERY = 0x0008
    TOKEN_QUERY = 0x0008
    advapi32 = ctypes.windll.advapi32
    if advapi32.OpenProcessToken(h_process, TOKEN_QUERY, ctypes.byref(h_token)):
        try:
            elevation = wintypes.DWORD()
            ret_len = wintypes.DWORD()
            # TokenElevation = 20
            if advapi32.GetTokenInformation(h_token, 20, ctypes.byref(elevation), ctypes.sizeof(elevation), ctypes.byref(ret_len)):
                return bool(elevation.value != 0)
        finally:
            kernel32.CloseHandle(h_token)
            kernel32.CloseHandle(h_process)
    else:
        kernel32.CloseHandle(h_process)

    return False


def get_foreground_process_info() -> Tuple[str, str, str]:
    """
    Returns (process_name, process_path, window_title) of the currently active window.
    Execution time is typically < 0.5ms.
    """
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return "unknown.exe", "", ""

    # 1. Window Title
    length = user32.GetWindowTextLengthW(hwnd)
    title_buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, title_buf, length + 1)
    window_title = title_buf.value

    # 2. Process ID
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if pid.value == 0:
        return "unknown.exe", "", window_title

    # 3. Process Handle and Executable Path
    # PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    h_process = kernel32.OpenProcess(0x1000, False, pid.value)
    if not h_process:
        # Fallback to PROCESS_QUERY_INFORMATION (0x0400) | PROCESS_VM_READ (0x0010)
        h_process = kernel32.OpenProcess(0x0410, False, pid.value)

    process_path = ""
    process_name = "unknown.exe"

    if h_process:
        try:
            exe_buf = ctypes.create_unicode_buffer(1024)
            size = wintypes.DWORD(1024)
            if kernel32.QueryFullProcessImageNameW(h_process, 0, exe_buf, ctypes.byref(size)):
                process_path = exe_buf.value
                process_name = os.path.basename(process_path)
            else:
                if psapi.GetModuleFileNameExW(h_process, 0, exe_buf, 1024):
                    process_path = exe_buf.value
                    process_name = os.path.basename(process_path)
        finally:
            kernel32.CloseHandle(h_process)

    return process_name.lower(), process_path, window_title
