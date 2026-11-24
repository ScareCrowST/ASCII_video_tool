import os
from typing import Optional

if os.name == "nt":
    import msvcrt


class KeyController:
    """Неблокирующее чтение клавиш в Windows cmd.exe / Terminal для режима --terminal."""

    def poll_action(self) -> Optional[str]:
        if os.name != "nt" or not msvcrt.kbhit():
            return None

        key = msvcrt.getch()

        if key in (b"\x00", b"\xe0"):
            ext = msvcrt.getch()
            if ext == b"K":
                return "seek_back"
            if ext == b"M":
                return "seek_forward"
            return None

        if key == b" ":
            return "pause"
        if key in (b"q", b"Q", b"\x1b"):
            return "quit"
        if key in (b"f", b"F", b"\xa0", b"\x80"):
            return "next_filter"
        if key in (b"c", b"C", b"\xe1", b"\x91"):
            return "next_charset"
        if key in (b"+", b"="):
            return "sat_up"
        if key in (b"-", b"_"):
            return "sat_down"
        if key in (b"[", b"{", b"\xe5", b"\x95"):
            return "res_down"
        if key in (b"]", b"}", b"\xea", b"\x9a"):
            return "res_up"

        return None
