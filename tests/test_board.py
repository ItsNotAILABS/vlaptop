"""The virtual machine is real pixels and a real shell, with no physical desktop."""

import base64
import sys

from vlaptop.board import Board
from vlaptop.host import Kernel
from vlaptop.jpeg import encode_jpeg


def test_jpeg_is_a_real_frame():
    rgb = bytes([180, 40, 40]) * 64
    blob = encode_jpeg(rgb, 8, 8)
    assert blob.startswith(b"\xff\xd8")
    assert blob.endswith(b"\xff\xd9")
    other = encode_jpeg(bytes([40, 40, 180]) * 64, 8, 8)
    assert blob != other


def test_board_see_touch_type_and_named_click():
    board = Board(96, 112)
    host = Kernel(board)
    hardware = host.kernel()["hardware"]
    assert hardware["schema"] == "vlaptop.hardware.v1"
    assert hardware["display"]["kind"] == "framebuffer"
    assert {item["kind"] for item in hardware["devices"]} == {"framebuffer", "pointer", "keyboard", "shell"}
    seen = host.see({"which": "machine", "max_w": 96})
    assert base64.b64decode(seen["jpeg_b64"]).startswith(b"\xff\xd8")
    host.type({"text": "hi", "nx": 0.2, "ny": 0.3, "click_first": True})
    assert board.field.endswith("hi")
    hit = host.click({"name": "Field"})
    assert hit["ok"] is True
    assert hit["role"] == "edit"
    assert hit["match"] == 1
    assert "nx" in hit["rect"]


def test_shell_and_memory_round_trip():
    host = Kernel(Board(96, 112))
    ran = host.handle("POST", "/v1/vcomp/shell", {"command": f"\"{sys.executable}\" -c \"print(42)\""})
    assert ran[0] == 200
    assert ran[1]["ok"] is True
    assert "42" in ran[1]["out"]
    assert "42" in host.desktop.console
    host.handle("POST", "/v1/vcomp/memory", {"text": "ship button", "kind": "note"})
    recalled = host.handle("GET", "/v1/vcomp/memory?q=ship", None)
    assert recalled[1]["notes"][0]["text"] == "ship button"
    opened = host.handle("POST", "/v1/vcomp/open", {"label": "lab"})
    assert opened[1]["hardware"]["schema"] == "vlaptop.hardware.v1"
