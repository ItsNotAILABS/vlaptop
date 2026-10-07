"""One virtual machine. The same display, pointer, keyboard, and shell on every device."""

from __future__ import annotations

import os
import platform
import subprocess
import sys
from typing import Any, Dict, List, Optional

from vlaptop.jpeg import encode_jpeg

# 3x5 glyphs, row-major, 3 bits per row. Enough to read the board.
_FONT = {
    " ": 0,
    "?": 0b111101001001001,
    "0": 0b111101101101111,
    "1": 0b010010010010010,
    "2": 0b111001111100111,
    "3": 0b111001111001111,
    "4": 0b101101111001001,
    "5": 0b111100111001111,
    "6": 0b111100111101111,
    "7": 0b111001001001001,
    "8": 0b111101111101111,
    "9": 0b111101111001111,
    "A": 0b010101111101101,
    "B": 0b110101110101110,
    "C": 0b111100100100111,
    "D": 0b110101101101110,
    "E": 0b111100111100111,
    "F": 0b111100111100100,
    "G": 0b111100101101111,
    "H": 0b101101111101101,
    "I": 0b111010010010111,
    "J": 0b001001001101111,
    "K": 0b101101110101101,
    "L": 0b100100100100111,
    "M": 0b101111111101101,
    "N": 0b110101101101101,
    "O": 0b111101101101111,
    "P": 0b111101111100100,
    "Q": 0b111101101111001,
    "R": 0b111101110101101,
    "S": 0b111100111001111,
    "T": 0b111010010010010,
    "U": 0b101101101101111,
    "V": 0b101101101101010,
    "W": 0b101101111111101,
    "X": 0b101101010101101,
    "Y": 0b101101010010010,
    "Z": 0b111001010100111,
    "-": 0b000000111000000,
    ".": 0b000000000000010,
    ":": 0b000010000010000,
    "/": 0b001001010100100,
    "_": 0b000000000000111,
}


def open_machine() -> "Board":
    """Boot the virtual machine. Windows also keeps the physical desktop as a second display."""
    native = None
    if os.name == "nt":
        from vlaptop.desktop import WindowsDesktop

        native = WindowsDesktop()
    return Board(native=native)


class Board:
    """Framebuffer computer. Phone, TV, Windows, and Linux all see these pixels."""

    def __init__(self, width: int = 320, height: int = 184, *, native: Any = None) -> None:
        self.w = width
        self.h = height
        self.native = native
        self.pixels = bytearray(width * height * 3)
        self.pointer = (width // 2, height // 2)
        self.field = ""
        self.console = "vLaptop hardware ready"
        self.focus = "Field"
        self.notes: List[Dict[str, Any]] = []
        self.label = ""
        self.agent = ""
        self._layout()
        self.paint()

    def bounds(self) -> Dict[str, int]:
        return {"x": 0, "y": 0, "w": self.w, "h": self.h}

    def hardware(self) -> Dict[str, Any]:
        return {
            "schema": "vlaptop.hardware.v1",
            "platform": platform.system() or sys.platform,
            "machine": platform.machine(),
            "python": platform.python_version(),
            "display": {"w": self.w, "h": self.h, "kind": "framebuffer"},
            "native_desktop": self.native is not None,
            "devices": [
                {"name": "display", "kind": "framebuffer"},
                {"name": "pointer", "kind": "pointer", "x": self.pointer[0], "y": self.pointer[1]},
                {"name": "keyboard", "kind": "keyboard", "focus": self.focus},
                {"name": "console", "kind": "shell"},
            ],
        }

    def capture(self, box: Dict[str, int], *, max_w: int) -> bytes:
        self.paint()
        cropped = self._crop(box)
        scaled = _fit(cropped, box["w"], box["h"], max(1, int(max_w)))
        return encode_jpeg(scaled[0], scaled[1], scaled[2])

    def tap(self, x: int, y: int) -> None:
        self.pointer = (max(0, min(self.w - 1, int(x))), max(0, min(self.h - 1, int(y))))
        hit = self._hit(self.pointer[0], self.pointer[1])
        if hit:
            self.focus = hit["name"]
            if hit["name"] == "Run":
                self.run(self.field)
        self.paint()

    def write(self, text: str) -> None:
        if self.focus == "Console":
            self.console = (self.console + text)[-800:]
        else:
            self.focus = "Field"
            self.field = (self.field + text)[-180:]
        self.paint()

    def click_name(self, name: str) -> Dict[str, Any]:
        hits = [item for item in self.controls if item["name"].lower() == (name or "").lower()]
        if not hits:
            return {"ok": False, "detail": "miss", "match": 0}
        item = hits[0]
        self.focus = item["name"]
        self.pointer = (item["x"] + item["w"] // 2, item["y"] + max(1, item["h"] // 2))
        if item["name"] == "Run":
            self.run(self.field)
        self.paint()
        return {
            "ok": True,
            "detail": "invoked:" + item["name"],
            "match": len(hits),
            "role": item["role"],
            "rect": self._rect(item),
        }

    def scroll(self, direction: str) -> None:
        if direction == "up":
            self.pointer = (self.pointer[0], max(0, self.pointer[1] - 12))
        else:
            self.pointer = (self.pointer[0], min(self.h - 1, self.pointer[1] + 12))
        self.paint()

    def run(self, command: str, *, timeout: int = 15) -> Dict[str, Any]:
        text = (command or "").strip()
        if not text:
            return {"ok": False, "error": "command required"}
        limit = max(1, min(30, int(timeout)))
        flags = int(getattr(subprocess, "CREATE_NO_WINDOW", 0)) if os.name == "nt" else 0
        info = None
        if os.name == "nt":
            info = subprocess.STARTUPINFO()
            info.dwFlags |= int(getattr(subprocess, "STARTF_USESHOWWINDOW", 1))
            info.wShowWindow = 0
        try:
            done = subprocess.run(
                text,
                shell=True,
                capture_output=True,
                timeout=limit,
                creationflags=flags,
                startupinfo=info,
            )
        except subprocess.TimeoutExpired:
            self.console = "timed out"
            self.paint()
            return {"ok": False, "error": "timed out", "code": 124}
        out = (done.stdout or b"").decode("utf-8", errors="replace")
        err = (done.stderr or b"").decode("utf-8", errors="replace")
        shown = (out or err or f"exit {done.returncode}").strip()[:800]
        self.console = shown or f"exit {done.returncode}"
        self.focus = "Console"
        self.paint()
        return {"ok": done.returncode == 0, "code": done.returncode, "out": shown}

    def sense(self) -> Dict[str, Any]:
        return {
            "ok": True,
            "hardware": self.hardware(),
            "controls": [
                {"name": item["name"], "role": item["role"], "rect": self._rect(item)}
                for item in self.controls
            ],
            "field": self.field,
            "console": self.console[:400],
        }

    def remember(self, text: str, kind: str = "note", tags: Optional[list] = None) -> Dict[str, Any]:
        self.notes.append({"text": (text or "")[:2000], "kind": kind or "note", "tags": list(tags or [])})
        self.notes = self.notes[-80:]
        return {"ok": True, "stored": len(self.notes)}

    def recall(self, query: str = "", limit: int = 20) -> Dict[str, Any]:
        needle = (query or "").lower()
        rows = [note for note in self.notes if not needle or needle in note["text"].lower()]
        return {"ok": True, "notes": rows[-max(1, limit):]}

    def paint(self) -> None:
        self._fill((8, 10, 16))
        self._fill_rect(0, 0, self.w, 14, (16, 163, 127))
        self._text(4, 4, "VLAPTOP", (6, 8, 12))
        for item in self.controls:
            on = item["name"] == self.focus
            self._fill_rect(item["x"], item["y"], item["w"], item["h"], (24, 32, 28) if on else (18, 20, 28))
            self._text(item["x"] + 4, item["y"] + 4, item["name"], (180, 220, 190))
            if item["name"] == "Field":
                self._text(item["x"] + 4, item["y"] + 16, self.field[-36:], (230, 236, 232))
            if item["name"] == "Console":
                self._text(item["x"] + 4, item["y"] + 16, self.console.replace("\n", " ")[-48:], (180, 190, 200))
        px, py = self.pointer
        self._fill_rect(px, py, 6, 6, (16, 220, 140))

    def _layout(self) -> None:
        self.controls = [
            {"name": "Field", "role": "edit", "x": 8, "y": 22, "w": self.w - 16, "h": 36},
            {"name": "Run", "role": "button", "x": 8, "y": 64, "w": 52, "h": 18},
            {"name": "Console", "role": "log", "x": 8, "y": 88, "w": self.w - 16, "h": self.h - 96},
        ]

    def _rect(self, item: Dict[str, int]) -> Dict[str, float]:
        return {
            "nx": round(item["x"] / self.w, 4),
            "ny": round(item["y"] / self.h, 4),
            "nw": round(item["w"] / self.w, 4),
            "nh": round(item["h"] / self.h, 4),
        }

    def _hit(self, x: int, y: int) -> Optional[Dict[str, Any]]:
        for item in reversed(self.controls):
            if item["x"] <= x < item["x"] + item["w"] and item["y"] <= y < item["y"] + item["h"]:
                return item
        return None

    def _fill(self, color: tuple) -> None:
        row = bytes(color) * self.w
        self.pixels[:] = row * self.h

    def _fill_rect(self, x: int, y: int, w: int, h: int, color: tuple) -> None:
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.w, x + w)
        y1 = min(self.h, y + h)
        ink = bytes(color)
        for yy in range(y0, y1):
            start = (yy * self.w + x0) * 3
            self.pixels[start:start + (x1 - x0) * 3] = ink * (x1 - x0)

    def _pix(self, x: int, y: int, color: tuple) -> None:
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.pixels[i:i + 3] = bytes(color)

    def _text(self, x: int, y: int, text: str, color: tuple) -> None:
        cursor = x
        for char in (text or "").upper():
            glyph = _FONT.get(char, _FONT["?"])
            for row in range(5):
                bits = (glyph >> (3 * (4 - row))) & 7
                for col in range(3):
                    if bits & (1 << (2 - col)):
                        self._pix(cursor + col, y + row, color)
            cursor += 4
            if cursor > self.w - 4:
                break

    def _crop(self, box: Dict[str, int]) -> bytes:
        x0 = max(0, int(box["x"]))
        y0 = max(0, int(box["y"]))
        w = max(1, int(box["w"]))
        h = max(1, int(box["h"]))
        out = bytearray(w * h * 3)
        for yy in range(h):
            sy = min(self.h - 1, y0 + yy)
            for xx in range(w):
                sx = min(self.w - 1, x0 + xx)
                src = (sy * self.w + sx) * 3
                dst = (yy * w + xx) * 3
                out[dst:dst + 3] = self.pixels[src:src + 3]
        return bytes(out)


def _fit(rgb: bytes, width: int, height: int, max_w: int) -> tuple:
    if width <= max_w:
        return rgb, width, height
    new_w = max_w
    new_h = max(1, int(height * (max_w / width)))
    out = bytearray(new_w * new_h * 3)
    for yy in range(new_h):
        sy = min(height - 1, int(yy * height / new_h))
        for xx in range(new_w):
            sx = min(width - 1, int(xx * width / new_w))
            src = (sy * width + sx) * 3
            dst = (yy * new_w + xx) * 3
            out[dst:dst + 3] = rgb[src:src + 3]
    return bytes(out), new_w, new_h
