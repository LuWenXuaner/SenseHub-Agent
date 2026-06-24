"""虚拟屏校准与坐标映射（Phase 4）."""

from __future__ import annotations

import json
from typing import Any

import numpy as np

from sensehub.db.database import get_connection


def _empty_calibration() -> dict[str, Any]:
    return {"calibrated": False, "screen_points": [], "camera_points": [], "matrix": []}


def get_calibration() -> dict[str, Any]:
    with get_connection() as conn:
        row = conn.execute("SELECT points_json, matrix_json FROM virtual_screen_calibration WHERE id = 1").fetchone()
    if not row:
        return _empty_calibration()
    points = json.loads(row["points_json"] or "{}")
    if isinstance(points, list):
        return {
            "calibrated": True,
            "screen_points": points,
            "camera_points": [],
            "matrix": json.loads(row["matrix_json"] or "[]"),
        }
    return {
        "calibrated": True,
        "screen_points": points.get("screen", []),
        "camera_points": points.get("camera", []),
        "matrix": json.loads(row["matrix_json"] or "[]"),
    }


def save_calibration(screen_points: list[list[float]], camera_points: list[list[float]]) -> dict[str, Any]:
    import cv2

    n = min(len(screen_points), len(camera_points))
    if n < 4:
        raise ValueError("至少需要 4 对校准点")
    src = np.float32(camera_points[:n])
    dst = np.float32(screen_points[:n])
    if n == 4:
        matrix = cv2.getPerspectiveTransform(src, dst)
    else:
        matrix, _mask = cv2.findHomography(src, dst, cv2.RANSAC, 5.0)
        if matrix is None:
            raise ValueError("校准点无效，请重新采集")
    matrix_list = matrix.tolist()
    payload_points = json.dumps({"screen": screen_points, "camera": camera_points}, ensure_ascii=False)
    matrix_json = json.dumps(matrix_list)
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO virtual_screen_calibration (id, points_json, matrix_json, updated_at)
            VALUES (1, ?, ?, datetime('now'))
            ON CONFLICT(id) DO UPDATE SET points_json=excluded.points_json,
            matrix_json=excluded.matrix_json, updated_at=datetime('now')
            """,
            (payload_points, matrix_json),
        )
    return {"calibrated": True, "screen_points": screen_points, "camera_points": camera_points, "matrix": matrix_list}


def map_camera_to_screen(x: float, y: float) -> tuple[float, float] | None:
    cal = get_calibration()
    if not cal.get("calibrated") or not cal.get("matrix"):
        return None
    import cv2

    matrix = np.float32(cal["matrix"])
    pt = np.float32([[[x, y]]])
    mapped = cv2.perspectiveTransform(pt, matrix)
    return float(mapped[0][0][0]), float(mapped[0][0][1])


def map_camera_to_virtual_click(x: float, y: float) -> dict[str, Any]:
    """将摄像头坐标映射到屏幕像素并执行点击."""
    from sensehub.execution.tools import gui

    mapped = map_camera_to_screen(x, y)
    if not mapped:
        raise RuntimeError("虚拟屏未校准")
    sx, sy = mapped
    sw, sh = gui._screen_size()
    nx = max(0, min(1000, sx / sw * 1000))
    ny = max(0, min(1000, sy / sh * 1000))
    return gui.click({"x": nx, "y": ny, "mapped_screen_x": sx, "mapped_screen_y": sy})
