"""vLaptop — public screen-kernel client."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

__version__ = "1.0.0"
PROTOCOL = "SCREEN-KERNEL/1.0"


class Screen:
    """Talk to a Pocket host that implements SCREEN-KERNEL/1.0."""

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
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            try:
                return json.loads(e.read().decode("utf-8"))
            except Exception:
                return {"ok": False, "error": str(e)}

    def kernel(self) -> Dict[str, Any]:
        return self._req("GET", "/v1/screen/kernel")

    def see(self, which: str = "desktop") -> Dict[str, Any]:
        return self._req("POST", "/v1/screen/see", {"which": which})

    def touch(self, kind: str = "tap", *, nx: float = 0.5, ny: float = 0.5, **extra: Any) -> Dict[str, Any]:
        extra.update({"kind": kind, "nx": nx, "ny": ny})
        return self._req("POST", "/v1/screen/touch", extra)

    def type(self, text: str, *, nx: float = 0.5, ny: float = 0.5, submit: bool = False) -> Dict[str, Any]:
        return self._req("POST", "/v1/screen/type", {"text": text, "nx": nx, "ny": ny, "submit": submit})

    def click(self, name: str) -> Dict[str, Any]:
        return self._req("POST", "/v1/screen/click", {"name": name})

    def open_vlaptop(self, label: str = "main") -> Dict[str, Any]:
        return self._req("POST", "/v1/vcomp/open", {"label": label})
