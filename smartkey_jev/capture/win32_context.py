"""
Win32 Foreground Process & Context Extractor.
Extracts active process name, window title, and cursor position via native Win32 APIs.
"""

import os
import ctypes
from ctypes import wintypes
from typing import Tuple


user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
psapi = ctypes.windll.psapi


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


def get_cursor_position() -> Tuple[int, int]:
    """Returns the current mouse cursor screen coordinates (x, y)."""
    pt = POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    return int(pt.x), int(pt.y)


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
            # QueryFullProcessImageNameW
            if kernel32.QueryFullProcessImageNameW(h_process, 0, exe_buf, ctypes.byref(size)):
                process_path = exe_buf.value
                process_name = os.path.basename(process_path)
            else:
                # Fallback to psapi.GetModuleFileNameExW
                if psapi.GetModuleFileNameExW(h_process, 0, exe_buf, 1024):
                    process_path = exe_buf.value
                    process_name = os.path.basename(process_path)
        finally:
            kernel32.CloseHandle(h_process)

    return process_name.lower(), process_path, window_title
