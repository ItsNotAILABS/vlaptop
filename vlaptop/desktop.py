"""Local desktop body for the standalone host. Windows uses the real screen."""

from __future__ import annotations

import base64
import os
import subprocess
from typing import Any, Dict, Optional


class Desktop:
    """What the host can see and touch. Tests pass a fake."""

    def bounds(self) -> Dict[str, int]:
        raise NotImplementedError

    def capture(self, box: Dict[str, int], *, max_w: int) -> bytes:
        raise NotImplementedError

    def tap(self, x: int, y: int) -> None:
        raise NotImplementedError

    def write(self, text: str) -> None:
        raise NotImplementedError

    def click_name(self, name: str) -> Dict[str, Any]:
        raise NotImplementedError


class WindowsDesktop(Desktop):
    def bounds(self) -> Dict[str, int]:
        raw = _ps(
            "Add-Type -AssemblyName System.Windows.Forms; "
            "$b=[System.Windows.Forms.Screen]::PrimaryScreen.Bounds; "
            "Write-Output ($b.X.ToString()+','+$b.Y.ToString()+','+$b.Width.ToString()+','+$b.Height.ToString())"
        )
        parts = [int(piece) for piece in raw.split(",")]
        return {"x": parts[0], "y": parts[1], "w": parts[2], "h": parts[3]}

    def capture(self, box: Dict[str, int], *, max_w: int) -> bytes:
        script = r"""
Add-Type -AssemblyName System.Drawing
$bmp = New-Object System.Drawing.Bitmap ([int]$env:VL_W), ([int]$env:VL_H)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen([int]$env:VL_X, [int]$env:VL_Y, 0, 0, $bmp.Size)
$max = [int]$env:VL_MAX
if ($bmp.Width -gt $max) {
  $nh = [Math]::Max(1, [int]($bmp.Height * ($max / [double]$bmp.Width)))
  $small = New-Object System.Drawing.Bitmap $bmp, $max, $nh
  $bmp.Dispose()
  $bmp = $small
}
$ms = New-Object System.IO.MemoryStream
$bmp.Save($ms, [System.Drawing.Imaging.ImageFormat]::Jpeg)
[Console]::Out.Write([Convert]::ToBase64String($ms.ToArray()))
"""
        encoded = _ps(
            script,
            env={
                "VL_X": str(box["x"]),
                "VL_Y": str(box["y"]),
                "VL_W": str(box["w"]),
                "VL_H": str(box["h"]),
                "VL_MAX": str(max(1, int(max_w))),
            },
        )
        return base64.b64decode(encoded)

    def tap(self, x: int, y: int) -> None:
        import ctypes

        user = ctypes.windll.user32
        user.SetCursorPos(int(x), int(y))
        user.mouse_event(0x02, 0, 0, 0, 0)
        user.mouse_event(0x04, 0, 0, 0, 0)

    def write(self, text: str) -> None:
        _ps(
            "Add-Type -AssemblyName System.Windows.Forms; "
            "[System.Windows.Forms.SendKeys]::SendWait($env:VL_TEXT)",
            env={"VL_TEXT": text[:400]},
        )

    def click_name(self, name: str) -> Dict[str, Any]:
        safe = (name or "").replace("'", "''")[:120]
        script = (
            "Add-Type -AssemblyName UIAutomationClient; "
            "$root=[System.Windows.Automation.AutomationElement]::RootElement; "
            f"$cond=New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::NameProperty,'{safe}'); "
            "$el=$root.FindFirst([System.Windows.Automation.TreeScope]::Descendants,$cond); "
            "if(-not $el){'miss'; exit 1}; "
            "try { $el.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke(); 'invoked:'+$el.Current.Name } "
            "catch { 'fail:'+$_.Exception.Message; exit 2 }"
        )
        try:
            detail = _ps(script)
        except RuntimeError as exc:
            return {"ok": False, "detail": str(exc)[:180]}
        return {"ok": not detail.startswith("miss") and not detail.startswith("fail"), "detail": detail[:180]}


def _ps(script: str, *, env: Optional[Dict[str, str]] = None) -> str:
    import os

    child_env = os.environ.copy()
    if env:
        child_env.update(env)
    flags = int(getattr(subprocess, "CREATE_NO_WINDOW", 0)) if os.name == "nt" else 0
    info = None
    if os.name == "nt":
        info = subprocess.STARTUPINFO()
        info.dwFlags |= int(getattr(subprocess, "STARTF_USESHOWWINDOW", 1))
        info.wShowWindow = 0
    run = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True,
        env=child_env,
        timeout=20,
        creationflags=flags,
        startupinfo=info,
    )
    text = (run.stdout or b"").decode("utf-8", errors="replace").strip()
    if run.returncode != 0:
        err = (run.stderr or b"").decode("utf-8", errors="replace").strip()
        raise RuntimeError(err or text or f"desktop command failed ({run.returncode})")
    return text
