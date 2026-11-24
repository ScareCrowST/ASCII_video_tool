import ctypes
from ctypes import wintypes
import os
import sys
import shutil
from typing import Tuple


class COORD(ctypes.Structure):
    _fields_ = [("X", wintypes.SHORT), ("Y", wintypes.SHORT)]


class CONSOLE_FONT_INFOEX(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.ULONG),
        ("nFont", wintypes.DWORD),
        ("dwFontSize", COORD),
        ("FontFamily", wintypes.UINT),
        ("FontWeight", wintypes.UINT),
        ("FaceName", wintypes.WCHAR * 32),
    ]


class TerminalManager:
    """Надежный вывод кадров на весь экран для режима терминала (--terminal)."""

    HIDE_CURSOR = "\033[?25l"
    SHOW_CURSOR = "\033[?25h"
    CLEAR_SCREEN = "\033[2J"
    CURSOR_HOME = "\033[H"
    CLEAR_BELOW = "\033[J"
    RESET_COLOR = "\033[0m"

    def __init__(self, title: str = "HD ASCII Player", font_size: int = 6, maximize: bool = True) -> None:
        self.font_size = font_size
        self.maximize = maximize

        if os.name == "nt":
            os.system(f"title {title}")
            self._setup_windows_console()

    def _setup_windows_console(self) -> None:
        kernel32 = ctypes.windll.kernel32
        user32 = ctypes.windll.user32
        handle = kernel32.GetStdHandle(-11)

        mode = ctypes.c_ulong()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            kernel32.SetConsoleMode(handle, mode.value | 0x0004)

        font = CONSOLE_FONT_INFOEX()
        font.cbSize = ctypes.sizeof(CONSOLE_FONT_INFOEX)
        font.nFont = 0
        font.dwFontSize.X = max(3, int(self.font_size * 0.5))
        font.dwFontSize.Y = max(5, self.font_size)
        font.FontFamily = 54
        font.FontWeight = 400
        font.FaceName = "Consolas"
        kernel32.SetCurrentConsoleFontEx(handle, False, ctypes.byref(font))

        if self.maximize:
            hwnd = kernel32.GetConsoleWindow()
            if hwnd:
                user32.ShowWindow(hwnd, 3)

    def __enter__(self) -> "TerminalManager":
        sys.stdout.write(self.HIDE_CURSOR + self.CLEAR_SCREEN)
        sys.stdout.flush()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        sys.stdout.write(self.RESET_COLOR + self.CLEAR_SCREEN + self.CURSOR_HOME + self.SHOW_CURSOR)
        sys.stdout.flush()

    def get_size(self) -> Tuple[int, int]:
        size = shutil.get_terminal_size(fallback=(180, 60))
        return size.columns, size.lines

    def render(self, frame_str: str) -> None:
        sys.stdout.write(self.CURSOR_HOME + frame_str + self.CLEAR_BELOW)
        sys.stdout.flush()
