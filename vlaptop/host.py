"""Standalone SCREEN-KERNEL host. No Pocket process required."""

from __future__ import annotations

import base64
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse

from vlaptop import PROTOCOL, __version__
from vlaptop.board import open_machine
from vlaptop.geom import frame_matrix, parse_region, pixel_box, unit

SCHEMA = "pocket.screen.kernel.v1"


class Kernel:
    def __init__(self, desktop: Any = None) -> None:
        self.desktop = desktop if desktop is not None else open_machine()
        self.booted = ""

    def kernel(self) -> Dict[str, Any]:
        body: Dict[str, Any] = {
            "ok": True,
            "schema": SCHEMA,
            "protocol": PROTOCOL,
            "product": "vLaptop",
            "version": __version__,
            "standalone": True,
            "verbs": ["see", "touch", "type", "click", "shell"],
            "note": "The framebuffer is the same machine on every device. which=desktop is the physical Windows screen when this host has one.",
        }
        hardware = getattr(self.desktop, "hardware", None)
        if callable(hardware):
            body["hardware"] = hardware()
        return body

    def _surface(self, which: Any) -> Any:
        native = getattr(self.desktop, "native", None)
        if str(which or "machine") == "desktop" and native is not None:
            return native
        return self.desktop

    def see(self, body: Dict[str, Any]) -> Dict[str, Any]:
        region = parse_region(body.get("region") if isinstance(body.get("region"), dict) else None)
        if body.get("region") and region is None:
            return {"ok": False, "error": "region must stay inside 0..1"}
        try:
            max_w = int(body.get("max_w") or 960)
        except (TypeError, ValueError):
            max_w = 960
        surface = self._surface(body.get("which"))
        geom = surface.bounds()
        box = pixel_box(geom, region)
        data = surface.capture(box, max_w=max(1, max_w))
        encoded = base64.b64encode(data).decode("ascii")
        return {
            "ok": True,
            "which": str(body.get("which") or "desktop"),
            "mime": "image/jpeg",
            "bytes": len(data),
            "base64": encoded,
            "jpeg_b64": encoded,
            "geom": geom,
            "frame": {"w": box["w"], "h": box["h"]},
            "matrix": frame_matrix(geom, region),
            "region": region or {"nx": 0.0, "ny": 0.0, "nw": 1.0, "nh": 1.0},
        }

    def touch(self, body: Dict[str, Any]) -> Dict[str, Any]:
        nx = unit(body.get("nx"))
        ny = unit(body.get("ny"))
        if nx is None or ny is None:
            return {"ok": False, "error": "nx and ny must be within 0..1"}
        surface = self._surface(body.get("which"))
        geom = surface.bounds()
        x = int(geom["x"] + nx * geom["w"])
        y = int(geom["y"] + ny * geom["h"])
        if str(body.get("kind") or "tap") == "scroll" and hasattr(surface, "scroll"):
            surface.scroll(str(body.get("direction") or "down"))
        else:
            surface.tap(x, y)
        return {"ok": True, "kind": str(body.get("kind") or "tap"), "nx": nx, "ny": ny, "x": x, "y": y}

    def type(self, body: Dict[str, Any]) -> Dict[str, Any]:
        text = str(body.get("text") or "")
        if body.get("click_first", True):
            tapped = self.touch(body)
            if not tapped.get("ok"):
                return tapped
        self._surface(body.get("which")).write(text)
        if body.get("submit") and hasattr(self.desktop, "run"):
            ran = self.desktop.run(text)
            return {"ok": bool(ran.get("ok")), "chars": len(text), "shell": ran}
        return {"ok": True, "chars": len(text)}

    def click(self, body: Dict[str, Any]) -> Dict[str, Any]:
        name = str(body.get("name") or "").strip()
        if not name:
            return {"ok": False, "error": "name required"}
        found = self._surface(body.get("which")).click_name(name)
        out: Dict[str, Any] = {"ok": bool(found.get("ok")), "name": name, "detail": found.get("detail") or ""}
        for key in ("match", "role", "rect"):
            if key in found:
                out[key] = found[key]
        return out

    def shell(self, body: Dict[str, Any]) -> Dict[str, Any]:
        if not hasattr(self.desktop, "run"):
            return {"ok": False, "error": "this device has no shell"}
        return self.desktop.run(str(body.get("command") or ""), timeout=int(body.get("timeout") or 15))

    def sense(self, body: Dict[str, Any]) -> Dict[str, Any]:
        del body
        if hasattr(self.desktop, "sense"):
            return self.desktop.sense()
        return {"ok": True, "hardware": self.kernel().get("hardware")}

    def act(self, body: Dict[str, Any]) -> Dict[str, Any]:
        action = str(body.get("action") or "")
        if action == "see":
            return self.see(body)
        if action in {"tap", "touch"}:
            return self.touch(body)
        if action in {"type_into", "type"}:
            return self.type(body)
        if action == "click_name":
            return self.click({"name": body.get("name") or body.get("text") or ""})
        if action == "scroll":
            return self.touch({**body, "kind": "scroll", "nx": body.get("nx", 0.5), "ny": body.get("ny", 0.5)})
        return {"ok": False, "error": "unknown action"}

    def handle(self, method: str, path: str, body: Optional[Dict[str, Any]]) -> tuple[int, Dict[str, Any]]:
        parsed = urlparse(path)
        path = parsed.path
        query = parse_qs(parsed.query)
        payload = body or {}
        if method == "GET" and path in ("/v1/screen/kernel", "/health"):
            return 200, self.kernel()
        if method == "GET" and path == "/v1/screen/hardware":
            board = getattr(self.desktop, "hardware", None)
            return 200, {"ok": True, "hardware": board() if callable(board) else {}}
        if method == "GET" and path == "/v1/vcomp":
            hardware = getattr(self.desktop, "hardware", None)
            return 200, {
                "ok": True,
                "tier": "pro",
                "label": self.booted,
                "hardware": hardware() if callable(hardware) else {},
            }
        if method == "GET" and path == "/v1/vcomp/memory":
            if not hasattr(self.desktop, "recall"):
                return 200, {"ok": False, "error": "this device has no memory"}
            limit = int((query.get("limit") or ["20"])[0] or 20)
            return 200, self.desktop.recall((query.get("q") or [""])[0], limit)
        if method == "POST" and path == "/v1/vcomp/open":
            self.booted = str(payload.get("label") or "main")
            if hasattr(self.desktop, "label"):
                self.desktop.label = self.booted
            return 200, {"ok": True, "label": self.booted, "hardware": self.kernel().get("hardware")}
        if method == "POST" and path == "/v1/vcomp/close":
            self.booted = ""
            return 200, {"ok": True}
        if method == "POST" and path == "/v1/vcomp/memory":
            if not hasattr(self.desktop, "remember"):
                return 200, {"ok": False, "error": "this device has no memory"}
            return 200, self.desktop.remember(str(payload.get("text") or ""), str(payload.get("kind") or "note"), payload.get("tags") or [])
        if method == "POST" and path == "/v1/screen/embody":
            if hasattr(self.desktop, "agent"):
                self.desktop.agent = str(payload.get("agent") or "coder")
            return 200, {"ok": True, "agent": str(payload.get("agent") or "coder"), "which": str(payload.get("which") or "machine")}
        routes = {
            ("POST", "/v1/screen/see"): self.see,
            ("POST", "/v1/screen/touch"): self.touch,
            ("POST", "/v1/screen/type"): self.type,
            ("POST", "/v1/screen/click"): self.click,
            ("POST", "/v1/vcomp/shell"): self.shell,
            ("POST", "/v1/vcomp/term"): self.shell,
            ("POST", "/v1/vcomp/sense"): self.sense,
            ("POST", "/v1/vcomp/act"): self.act,
            ("POST", "/v1/screen/body"): self._body,
        }
        call = routes.get((method, path))
        if not call:
            return 404, {"ok": False, "error": "unknown verb"}
        return 200, call(payload)

    def _body(self, body: Dict[str, Any]) -> Dict[str, Any]:
        verb = str(body.get("verb") or "see")
        if verb == "see":
            return self.see(body)
        if verb == "touch":
            return self.touch(body)
        if verb == "type":
            return self.type(body)
        if verb == "click":
            return self.click(body)
        if verb == "cursor":
            hardware = getattr(self.desktop, "hardware", None)
            devices = (hardware() if callable(hardware) else {}).get("devices") or []
            pointer = next((item for item in devices if item.get("kind") == "pointer"), {})
            return {"ok": True, "x": pointer.get("x"), "y": pointer.get("y")}
        return {"ok": False, "error": "unknown body verb"}


def serve(host: str = "127.0.0.1", port: int = 8788, desktop: Any = None) -> None:
    kernel = Kernel(desktop)

    class Handler(BaseHTTPRequestHandler):
        def _send(self, status: int, payload: Dict[str, Any]) -> None:
            raw = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self) -> None:  # noqa: N802
            status, payload = kernel.handle("GET", self.path, None)
            self._send(status, payload)

        def do_POST(self) -> None:  # noqa: N802
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b""
            try:
                body = json.loads(raw.decode("utf-8")) if raw else {}
            except json.JSONDecodeError:
                self._send(400, {"ok": False, "error": "body must be JSON"})
                return
            if not isinstance(body, dict):
                self._send(400, {"ok": False, "error": "body must be a JSON object"})
                return
            status, payload = kernel.handle("POST", self.path, body)
            self._send(status, payload)

        def log_message(self, fmt: str, *args: Any) -> None:
            return

    ThreadingHTTPServer((host, port), Handler).serve_forever()


def main() -> None:
    serve()


if __name__ == "__main__":
    main()
