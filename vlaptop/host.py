"""Standalone SCREEN-KERNEL host. No Pocket process required."""

from __future__ import annotations

import base64
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional

from vlaptop import PROTOCOL, __version__
from vlaptop.desktop import Desktop, WindowsDesktop
from vlaptop.geom import frame_matrix, parse_region, pixel_box, unit

SCHEMA = "pocket.screen.kernel.v1"


class Kernel:
    def __init__(self, desktop: Optional[Desktop] = None) -> None:
        self.desktop = desktop or WindowsDesktop()

    def kernel(self) -> Dict[str, Any]:
        return {
            "ok": True,
            "schema": SCHEMA,
            "protocol": PROTOCOL,
            "product": "vLaptop",
            "version": __version__,
            "standalone": True,
            "verbs": ["see", "touch", "type", "click"],
            "note": "This host owns the screen. Pocket is another host of the same contract.",
        }

    def see(self, body: Dict[str, Any]) -> Dict[str, Any]:
        region = parse_region(body.get("region") if isinstance(body.get("region"), dict) else None)
        if body.get("region") and region is None:
            return {"ok": False, "error": "region must stay inside 0..1"}
        try:
            max_w = int(body.get("max_w") or 960)
        except (TypeError, ValueError):
            max_w = 960
        geom = self.desktop.bounds()
        box = pixel_box(geom, region)
        data = self.desktop.capture(box, max_w=max(1, max_w))
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
        geom = self.desktop.bounds()
        x = int(geom["x"] + nx * geom["w"])
        y = int(geom["y"] + ny * geom["h"])
        self.desktop.tap(x, y)
        return {"ok": True, "kind": str(body.get("kind") or "tap"), "nx": nx, "ny": ny, "x": x, "y": y}

    def type(self, body: Dict[str, Any]) -> Dict[str, Any]:
        text = str(body.get("text") or "")
        if body.get("click_first", True):
            tapped = self.touch(body)
            if not tapped.get("ok"):
                return tapped
        self.desktop.write(text)
        return {"ok": True, "chars": len(text)}

    def click(self, body: Dict[str, Any]) -> Dict[str, Any]:
        name = str(body.get("name") or "").strip()
        if not name:
            return {"ok": False, "error": "name required"}
        found = self.desktop.click_name(name)
        return {"ok": bool(found.get("ok")), "name": name, "detail": found.get("detail") or ""}

    def handle(self, method: str, path: str, body: Optional[Dict[str, Any]]) -> tuple[int, Dict[str, Any]]:
        path = path.split("?", 1)[0]
        payload = body or {}
        if method == "GET" and path in ("/v1/screen/kernel", "/health"):
            return 200, self.kernel()
        routes = {
            ("POST", "/v1/screen/see"): self.see,
            ("POST", "/v1/screen/touch"): self.touch,
            ("POST", "/v1/screen/type"): self.type,
            ("POST", "/v1/screen/click"): self.click,
        }
        call = routes.get((method, path))
        if not call:
            return 404, {"ok": False, "error": "unknown verb"}
        return 200, call(payload)


def serve(host: str = "127.0.0.1", port: int = 8788, desktop: Optional[Desktop] = None) -> None:
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
