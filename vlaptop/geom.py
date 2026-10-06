"""Screen geometry for the standalone vLaptop host. Stdlib only."""

from __future__ import annotations

from typing import Any, Dict, Optional


def unit(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number or number < -1e-6 or number > 1.0 + 1e-6:
        return None
    return max(0.0, min(1.0, number))


def parse_region(region: Optional[Dict[str, Any]]) -> Optional[Dict[str, float]]:
    if not region:
        return None
    parsed: Dict[str, float] = {}
    for key in ("nx", "ny", "nw", "nh"):
        number = unit(region.get(key))
        if number is None:
            return None
        parsed[key] = number
    if parsed["nw"] <= 0 or parsed["nh"] <= 0:
        return None
    if parsed["nx"] + parsed["nw"] > 1.000001 or parsed["ny"] + parsed["nh"] > 1.000001:
        return None
    return parsed


def frame_matrix(geom: Dict[str, Any], region: Optional[Dict[str, float]] = None) -> list:
    """Column [nx, ny, 1] times this matrix is a desktop pixel."""
    x = float(geom.get("x") or 0)
    y = float(geom.get("y") or 0)
    w = float(geom.get("w") or 1)
    h = float(geom.get("h") or 1)
    if region:
        x = x + region["nx"] * w
        y = y + region["ny"] * h
        w = w * region["nw"]
        h = h * region["nh"]
    return [[w, 0.0, x], [0.0, h, y], [0.0, 0.0, 1.0]]


def pixel_box(geom: Dict[str, Any], region: Optional[Dict[str, float]] = None) -> Dict[str, int]:
    matrix = frame_matrix(geom, region)
    return {
        "x": int(matrix[0][2]),
        "y": int(matrix[1][2]),
        "w": max(1, int(matrix[0][0])),
        "h": max(1, int(matrix[1][1])),
    }
