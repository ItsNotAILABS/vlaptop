"""Standalone host. The desktop is a fake, so no screen is touched."""

import base64

from vlaptop import to_point
from vlaptop.host import Kernel


class _Desk:
    def __init__(self) -> None:
        self.taps = []
        self.writes = []
        self.boxes = []

    def bounds(self):
        return {"x": 0, "y": 0, "w": 1920, "h": 1080}

    def capture(self, box, *, max_w):
        self.boxes.append((box, max_w))
        return b"\xff\xd8\xff\xd9"

    def tap(self, x, y):
        self.taps.append((x, y))

    def write(self, text):
        self.writes.append(text)

    def click_name(self, name):
        return {"ok": name == "Save", "detail": "invoked:Save" if name == "Save" else "miss"}


def test_kernel_is_its_own_system():
    body = Kernel(_Desk()).kernel()
    assert body["standalone"] is True
    assert body["product"] == "vLaptop"
    assert body["protocol"] == "SCREEN-KERNEL/1.2"


def test_see_region_uses_the_spec_matrix():
    desk = _Desk()
    seen = Kernel(desk).see({"region": {"nx": 0, "ny": 0, "nw": 1, "nh": 1}, "max_w": 640})
    assert seen["ok"] is True
    assert base64.b64decode(seen["jpeg_b64"])[:2] == b"\xff\xd8"
    assert to_point(seen["matrix"], 1, 1) == (1920.0, 1080.0)
    assert desk.boxes[0][0] == {"x": 0, "y": 0, "w": 1920, "h": 1080}


def test_touch_refuses_bad_coordinates_and_maps_good_ones():
    desk = _Desk()
    host = Kernel(desk)
    assert host.touch({"nx": 1.4, "ny": 0.2})["ok"] is False
    assert desk.taps == []
    hit = host.touch({"nx": 0.5, "ny": 0.5})
    assert hit["ok"] is True
    assert desk.taps == [(960, 540)]


def test_click_reports_a_miss():
    out = Kernel(_Desk()).click({"name": "Missing"})
    assert out["ok"] is False
    assert out["detail"] == "miss"
