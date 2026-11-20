"""
Selected Text Extraction Engine.
Implements dual-channel extraction:
1. Fast UI Automation (UIA TextPattern) for non-invasive extraction.
2. Synthetic Ctrl+C with Clipboard Isolation (prevents polluting Win+V history).
"""

import time
import ctypes
from ctypes import wintypes
from typing import Optional, Tuple
from ..core.config import CaptureConfig


user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# Register custom clipboard formats to exclude from Windows Clipboard History & cloud sync
CF_CAN_INCLUDE_IN_CLIPBOARD_HISTORY = user32.RegisterClipboardFormatW("CanIncludeInClipboardHistory")
CF_EXCLUDE_FROM_MONITOR_PROCESSING = user32.RegisterClipboardFormatW("ExcludeClipboardContentFromMonitorProcessing")

# Clipboard constants
CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002


def _read_clipboard_unicode() -> Optional[str]:
    """Safely reads Unicode text from the Win32 clipboard."""
    if not user32.OpenClipboard(None):
        return None
    try:
        if not user32.IsClipboardFormatAvailable(CF_UNICODETEXT):
            return None
        h_glb = user32.GetClipboardData(CF_UNICODETEXT)
        if not h_glb:
            return None
        kernel32.GlobalLock.restype = ctypes.c_void_p
        p_text = kernel32.GlobalLock(h_glb)
        if not p_text:
            return None
        try:
            return ctypes.wstring_at(p_text)
        finally:
            kernel32.GlobalUnlock(h_glb)
    finally:
        user32.CloseClipboard()


def _write_clipboard_unicode(text: str, exclude_from_history: bool = True) -> bool:
    """Safely writes text to the Win32 clipboard with optional history exclusion."""
    if not user32.OpenClipboard(None):
        return False
    try:
        user32.EmptyClipboard()
        # Encode null-terminated UTF-16
        encoded = text.encode("utf-16-le") + b"\x00\x00"
        h_glb = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(encoded))
        if not h_glb:
            return False

        kernel32.GlobalLock.restype = ctypes.c_void_p
        p_mem = kernel32.GlobalLock(h_glb)
        if not p_mem:
            kernel32.GlobalFree(h_glb)
            return False

        ctypes.memmove(p_mem, encoded, len(encoded))
        kernel32.GlobalUnlock(h_glb)
        user32.SetClipboardData(CF_UNICODETEXT, h_glb)

        # Flag to suppress Windows 10/11 Win+V history
        if exclude_from_history and CF_CAN_INCLUDE_IN_CLIPBOARD_HISTORY:
            # Set a 4-byte DWORD value 0
            h_flag = kernel32.GlobalAlloc(GMEM_MOVEABLE, 4)
            if h_flag:
                p_flag = kernel32.GlobalLock(h_flag)
                if p_flag:
                    ctypes.memset(p_flag, 0, 4)
                    kernel32.GlobalUnlock(h_flag)
                    user32.SetClipboardData(CF_CAN_INCLUDE_IN_CLIPBOARD_HISTORY, h_flag)

        return True
    finally:
        user32.CloseClipboard()


def _send_ctrl_c():
    """Synthesize Ctrl+C using Win32 SendInput (low-overhead, non-blocking)."""
    # Key codes: VK_CONTROL = 0x11, 'C' = 0x43
    # KEYEVENTF_KEYUP = 0x0002
    user32.keybd_event(0x11, 0, 0, 0)       # Ctrl Down
    user32.keybd_event(0x43, 0, 0, 0)       # C Down
    time.sleep(0.005)                       # 5ms hold
    user32.keybd_event(0x43, 0, 0x0002, 0)  # C Up
    user32.keybd_event(0x11, 0, 0x0002, 0)  # Ctrl Up


class TextExtractor:
    """Extracts selected text from active windows with clipboard backup and fallback."""

    def __init__(self, config: Optional[CaptureConfig] = None):
        self.config = config or CaptureConfig()

    def extract_uia(self) -> Optional[str]:
        """Channel 1: UI Automation extraction for standard accessibility-enabled controls."""
        try:
            import uiautomation as auto
            element = auto.GetFocusedElement()
            if not element:
                return None
            pattern = element.GetPattern(auto.PatternId.TextPattern)
            if pattern:
                selections = pattern.GetSelection()
                if selections and len(selections) > 0:
                    text = selections[0].GetText(self.config.max_context_chars)
                    if text and text.strip():
                        return text
        except Exception:
            pass
        return None

    def extract_clipboard_synthetic(self) -> Tuple[Optional[str], Optional[str]]:
        """
        Channel 2: Synthetic Ctrl+C with isolated clipboard backup and restore.
        Returns: (extracted_text, original_clipboard_backup)
        """
        # 1. Backup existing clipboard content
        old_clipboard = _read_clipboard_unicode()

        # 2. Clear clipboard to detect fresh copy
        if user32.OpenClipboard(None):
            user32.EmptyClipboard()
            user32.CloseClipboard()

        # 3. Simulate Ctrl+C
        _send_ctrl_c()

        # 4. Wait for active application event loop to process WM_COPY
        wait_interval = 0.005
        max_attempts = int(self.config.clipboard_wait_ms / 5)
        extracted = None

        for _ in range(max(1, max_attempts)):
            time.sleep(wait_interval)
            extracted = _read_clipboard_unicode()
            if extracted and extracted.strip():
                break

        # 5. Restore original clipboard content if configured
        if self.config.preserve_clipboard and old_clipboard is not None:
            _write_clipboard_unicode(old_clipboard, exclude_from_history=False)

        return extracted, old_clipboard

    def extract(self) -> Tuple[str, str]:
        """
        Executes dual-channel extraction.
        Returns: (truncated_text, raw_text)
        """
        # Fast path: try UI Automation
        text = self.extract_uia()

        # Fallback path: synthetic Ctrl+C
        if not text or not text.strip():
            extracted, _ = self.extract_clipboard_synthetic()
            text = extracted or ""

        raw_text = text.strip()
        truncated = raw_text[: self.config.max_context_chars]
        return truncated, raw_text
