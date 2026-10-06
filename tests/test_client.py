"""Client routes stay on the host contract. No live Pocket required."""

import base64
import io
import urllib.error
import urllib.request

import pytest

from vlaptop import (
    PROTOCOL,
    HostError,
    Laptop,
    NetworkError,
    Screen,
    ScreenError,
    __version__,
    to_point,
)


class _Fake(Laptop):
    def __init__(self) -> None:
        super().__init__("http://127.0.0.1:9")
        self.calls = []

    def _req(self, method, path, body=None):
        self.calls.append((method, path, body))
        return {"ok": True}


def test_protocol_is_pro_generation():
    assert PROTOCOL == "SCREEN-KERNEL/1.2"
    assert __version__ == "1.2.0"


def test_memory_and_sense_routes():
    pc = _Fake()
    pc.remember("ship button", kind="note", tags=["deploy"])
    pc.recall("ship", limit=5)
    pc.sense()
    pc.scroll("down")
    methods = [(c[0], c[1].split("?", 1)[0]) for c in pc.calls]
    assert ("POST", "/v1/vcomp/memory") in methods
    assert ("GET", "/v1/vcomp/memory") in methods
    assert ("POST", "/v1/vcomp/sense") in methods
    body = pc.calls[0][2]
    assert body["text"] == "ship button"
    assert "q=ship" in pc.calls[1][1]


def test_spec_matrix_is_not_flat():
    matrix = [[1920, 0, 0], [0, 1080, 0], [0, 0, 1]]
    assert to_point(matrix, 1, 1) == (1920.0, 1080.0)
    assert to_point(matrix, 0.5, 0) == (960.0, 0.0)
    assert to_point([1920, 0, 0, 0, 1080, 0, 0, 0, 1], 1, 0) == (1920.0, 0.0)


def test_bad_matrix_is_a_screen_error():
    with pytest.raises(ScreenError):
        to_point([["no", 0, 0], [0, 1, 0], [0, 0, 1]], 0, 0)


def test_touch_refuses_coordinates_outside_the_frame():
    screen = Screen("http://127.0.0.1:9")
    with pytest.raises(ScreenError):
        screen.touch(nx=1.4, ny=-0.2)


def test_see_decodes_jpeg_and_sends_region():
    jpeg = b"\xff\xd8\xff\xd9"
    seen = {}

    class _See(Screen):
        def _req(self, method, path, body=None):
            seen["body"] = body
            return {"ok": True, "jpeg_b64": base64.b64encode(jpeg).decode("ascii"), "matrix": [[1, 0, 0], [0, 1, 0], [0, 0, 1]]}

    out = _See("http://127.0.0.1:9").see("desktop", nx=0.25, ny=0.25, nw=0.5, nh=0.5, max_w=320)
    assert out["jpeg"] == jpeg
    assert seen["body"]["region"] == {"nx": 0.25, "ny": 0.25, "nw": 0.5, "nh": 0.5}
    assert seen["body"]["max_w"] == 320


def test_host_refusal_is_not_a_network_error(monkeypatch):
    def refuse(*_args, **_kwargs):
        raise urllib.error.HTTPError(
            "http://127.0.0.1/v1/screen/kernel",
            403,
            "no",
            hdrs=None,
            fp=io.BytesIO(b'{"ok": false, "error": "gate"}'),
        )

    monkeypatch.setattr(urllib.request, "urlopen", refuse)
    with pytest.raises(HostError) as caught:
        Screen("http://127.0.0.1:9").kernel()
    assert caught.value.status == 403
    assert caught.value.body["error"] == "gate"


def test_urlerror_is_a_network_error(monkeypatch):
    def down(*_args, **_kwargs):
        raise urllib.error.URLError("timed out")

    monkeypatch.setattr(urllib.request, "urlopen", down)
    with pytest.raises(NetworkError):
        Screen("http://127.0.0.1:9").kernel()