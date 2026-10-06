"""vLaptop — public screen-kernel client."""

from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
from typing import Any, Dict, Optional, Sequence, Tuple

__version__ = "1.2.0"
PROTOCOL = "SCREEN-KERNEL/1.2"
STREAM = "pocket.stream.v1"


class ScreenError(Exception):
    """Client or host contract failure. Catch this, not ValueError."""


class HostError(ScreenError):
    """The host answered and refused. status is the HTTP code."""

    def __init__(self, status: int, body: Dict[str, Any]) -> None:
        self.status = status
        self.body = body
        super().__init__(f"host said no ({status})")


class NetworkError(ScreenError):
    """No HTTP answer. The host was not reached."""


def _unit(name: str, value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ScreenError(f"{name} is not a number") from exc
    if number != number or number < 0.0 or number > 1.0:
        raise ScreenError(f"{name} must be within 0..1")
    return number


def _span(name: str, value: Any) -> float:
    number = _unit(name, value)
    if number <= 0.0:
        raise ScreenError(f"{name} must be greater than 0")
    return number


def to_point(matrix: Sequence[Any], nx: float, ny: float) -> Tuple[float, float]:
    """Map nx,ny through the spec's 3×3 matrix onto desktop pixels.

    Column [nx, ny, 1] times M. The documented example is
    [[1920, 0, 0], [0, 1080, 0], [0, 0, 1]]. A flat list of 9 numbers
    is accepted too.
    """
    rows = _matrix_rows(matrix)
    x = rows[0][0] * nx + rows[0][1] * ny + rows[0][2]
    y = rows[1][0] * nx + rows[1][1] * ny + rows[1][2]
    return (float(x), float(y))


def _matrix_rows(matrix: Sequence[Any]) -> list:
    if matrix and isinstance(matrix[0], (list, tuple)):
        rows = [list(row) for row in matrix]
    else:
        flat = list(matrix)
        if len(flat) != 9:
            raise ScreenError("matrix needs 3 rows or 9 numbers")
        rows = [flat[0:3], flat[3:6], flat[6:9]]
    if len(rows) < 2 or any(len(row) < 3 for row in rows[:2]):
        raise ScreenError("matrix needs 3 rows or 9 numbers")
    try:
        return [[float(row[0]), float(row[1]), float(row[2])] for row in rows[:2]]
    except (TypeError, ValueError) as exc:
        raise ScreenError("matrix values must be numbers") from exc


class Screen:
    """Talk to a Pocket host that implements SCREEN-KERNEL/1.2."""

    def __init__(self, base: str = "http://127.0.0.1:8787", *, token: str = "") -> None:
        self.base = (base or "").rstrip("/")
        self.token = token

    def _req(self, method: str, path: str, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        data = None
        headers = {"Accept": "application/json"}
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(self.base + path, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=20) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                payload = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                payload = {"ok": False, "error": raw or str(exc)}
            if not isinstance(payload, dict):
                payload = {"ok": False, "error": str(payload)}
            raise HostError(exc.code, payload) from exc
        except urllib.error.URLError as exc:
            raise NetworkError(str(getattr(exc, "reason", exc))) from exc
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError as exc:
            raise ScreenError("host returned non-JSON") from exc
        if not isinstance(payload, dict):
            raise ScreenError("host returned non-JSON")
        return payload

    def kernel(self) -> Dict[str, Any]:
        return self._req("GET", "/v1/screen/kernel")

    def see(
        self,
        which: str = "desktop",
        *,
        nx: Optional[float] = None,
        ny: Optional[float] = None,
        nw: Optional[float] = None,
        nh: Optional[float] = None,
        max_w: int = 960,
    ) -> Dict[str, Any]:
        """JPEG of the screen. Pass nx,ny,nw,nh to zoom a region of the frame.

        The returned dict includes jpeg bytes plus geom, matrix, and frame size
        when the host sends them. jpeg is decoded from jpeg_b64 or base64.
        """
        body: Dict[str, Any] = {"which": which, "max_w": int(max_w)}
        if any(value is not None for value in (nx, ny, nw, nh)):
            if any(value is None for value in (nx, ny, nw, nh)):
                raise ScreenError("region needs nx, ny, nw, and nh")
            region = {
                "nx": _unit("nx", nx),
                "ny": _unit("ny", ny),
                "nw": _span("nw", nw),
                "nh": _span("nh", nh),
            }
            if region["nx"] + region["nw"] > 1.000001 or region["ny"] + region["nh"] > 1.000001:
                raise ScreenError("region runs past the frame")
            body["region"] = region
        payload = self._req("POST", "/v1/screen/see", body)
        encoded = payload.get("jpeg_b64") or payload.get("base64") or ""
        if encoded:
            try:
                payload["jpeg"] = base64.b64decode(encoded)
            except Exception as exc:
                raise ScreenError("see image was not valid base64") from exc
        return payload

    def touch(self, kind: str = "tap", *, nx: float = 0.5, ny: float = 0.5, **extra: Any) -> Dict[str, Any]:
        extra.update({"kind": kind, "nx": _unit("nx", nx), "ny": _unit("ny", ny)})
        return self._req("POST", "/v1/screen/touch", extra)

    def type(self, text: str, *, nx: float = 0.5, ny: float = 0.5, submit: bool = False, click_first: bool = True) -> Dict[str, Any]:
        return self._req(
            "POST",
            "/v1/screen/type",
            {
                "text": text,
                "nx": _unit("nx", nx),
                "ny": _unit("ny", ny),
                "submit": submit,
                "click_first": click_first,
            },
        )

    def click(self, name: str) -> Dict[str, Any]:
        return self._req("POST", "/v1/screen/click", {"name": name})

    def cursor(self) -> Dict[str, Any]:
        return self.body("cursor")

    def open_vlaptop(self, label: str = "main") -> Dict[str, Any]:
        return self._req("POST", "/v1/vcomp/open", {"label": label})

    def close(self) -> Dict[str, Any]:
        return self._req("POST", "/v1/vcomp/close", {})

    def computer(self) -> Dict[str, Any]:
        return self._req("GET", "/v1/vcomp")

    def sense(self, max_ui: int = 500) -> Dict[str, Any]:
        return self._req("POST", "/v1/vcomp/sense", {"max_ui": max_ui})

    def act(self, action: str, **params: Any) -> Dict[str, Any]:
        params["action"] = action
        return self._req("POST", "/v1/vcomp/act", params)

    def shell(self, command: str, *, timeout: int = 60) -> Dict[str, Any]:
        return self._req("POST", "/v1/vcomp/shell", {"command": command, "timeout": timeout})

    def term(self, command: str = "", *, terminal_id: str = "", kind: str = "powershell") -> Dict[str, Any]:
        body: Dict[str, Any] = {"kind": kind}
        if command and terminal_id:
            body["id"] = terminal_id
            body["command"] = command
        return self._req("POST", "/v1/vcomp/term", body)

    def scroll(self, direction: str = "down", *, n: int = 3) -> Dict[str, Any]:
        return self.act("scroll", direction=direction, n=n)

    def remember(self, text: str, *, kind: str = "note", tags: Optional[list] = None) -> Dict[str, Any]:
        return self._req("POST", "/v1/vcomp/memory", {"text": text, "kind": kind, "tags": tags or []})

    def recall(self, query: str = "", *, limit: int = 20) -> Dict[str, Any]:
        path = "/v1/vcomp/memory"
        if query or limit != 20:
            from urllib.parse import urlencode

            path += "?" + urlencode({"q": query, "limit": str(limit)})
        return self._req("GET", path)

    def embody(self, agent: str = "coder", *, which: str = "desktop") -> Dict[str, Any]:
        return self._req("POST", "/v1/screen/embody", {"agent": agent, "which": which})

    def body(self, verb: str = "see", **extra: Any) -> Dict[str, Any]:
        extra.update({"verb": verb})
        return self._req("POST", "/v1/screen/body", extra)


class Laptop(Screen):
    """Pro seat: the screen kernel plus the virtual computer and its memory."""

    def boot(self, label: str = "main") -> Dict[str, Any]:
        opened = self.open_vlaptop(label)
        opened["memory"] = self.recall(limit=8)
        return opened
