"""虚拟屏校准与坐标映射（Phase 4）."""

from __future__ import annotations

import json
from typing import Any

import numpy as np

from sensehub.db.database import get_connection


def _virtual_desktop_bounds() -> tuple[int, int, int, int]:
    """与 pyautogui 一致的虚拟桌面边界 (left, top, width, height)."""
    try:
        import mss

        with mss.mss() as sct:
            mon = sct.monitors[1]
            return int(mon["left"]), int(mon["top"]), int(mon["width"]), int(mon["height"])
    except Exception:
        import pyautogui

        w, h = pyautogui.size()
        return 0, 0, int(w), int(h)


_CALIB_GRID_NORM = [
    (0.1, 0.1),
    (0.5, 0.1),
    (0.9, 0.1),
    (0.1, 0.5),
    (0.5, 0.5),
    (0.9, 0.5),
    (0.1, 0.9),
    (0.5, 0.9),
    (0.9, 0.9),
]


def normalized_screen_point(nx: float, ny: float) -> tuple[float, float]:
    left, top, w, h = _virtual_desktop_bounds()
    return left + nx * w, top + ny * h


def calib_grid_screen_points() -> list[list[float]]:
    """九点标定在主显示器上的物理像素坐标（与鼠标坐标系一致）."""
    return [[x, y] for x, y in (normalized_screen_point(nx, ny) for nx, ny in _CALIB_GRID_NORM)]


def _empty_calibration() -> dict[str, Any]:
    return {
        "calibrated": False,
        "screen_points": [],
        "camera_points": [],
        "matrix": [],
        "frame_width": 0,
        "frame_height": 0,
    }


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
            "frame_width": 0,
            "frame_height": 0,
        }
    return {
        "calibrated": True,
        "screen_points": points.get("screen", []),
        "camera_points": points.get("camera", []),
        "matrix": json.loads(row["matrix_json"] or "[]"),
        "frame_width": int(points.get("frame_width") or 0),
        "frame_height": int(points.get("frame_height") or 0),
    }


def save_calibration(
    screen_points: list[list[float]],
    camera_points: list[list[float]],
    *,
    frame_width: int = 0,
    frame_height: int = 0,
) -> dict[str, Any]:
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
    payload_points = json.dumps(
        {
            "screen": screen_points,
            "camera": camera_points,
            "frame_width": int(frame_width),
            "frame_height": int(frame_height),
        },
        ensure_ascii=False,
    )
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
    return {
        "calibrated": True,
        "screen_points": screen_points,
        "camera_points": camera_points,
        "matrix": matrix_list,
        "frame_width": int(frame_width),
        "frame_height": int(frame_height),
    }


def _scale_camera_point(x: float, y: float, cal: dict[str, Any], frame_shape: tuple[int, int] | None) -> tuple[float, float]:
    fw = int(cal.get("frame_width") or 0)
    fh = int(cal.get("frame_height") or 0)
    if not frame_shape or fw <= 0 or fh <= 0:
        return x, y
    h, w = frame_shape
    if w == fw and h == fh:
        return x, y
    sx = w / fw
    sy = h / fh
    return x * sx, y * sy


def _point_in_hull(x: float, y: float, hull: np.ndarray) -> bool:
    import cv2

    if hull is None or len(hull) < 3:
        return True
    return cv2.pointPolygonTest(hull, (float(x), float(y)), False) >= 0


def get_mapping_mode() -> str:
    from sensehub.perception.config import get_perception_config

    mode = str(get_perception_config().get("virtual_screen_mapping") or "direct").lower()
    return mode if mode in ("direct", "homography") else "direct"


def virtual_screen_ready() -> bool:
    if get_mapping_mode() == "direct":
        return True
    cal = get_calibration()
    return bool(cal.get("calibrated") and cal.get("matrix"))


def _apply_camera_mirror(x: float, y: float, frame_shape: tuple[int, int] | None) -> tuple[float, float]:
    if not frame_shape:
        return x, y
    from sensehub.perception.config import get_perception_config

    if not get_perception_config().get("camera_mirror"):
        return x, y
    _h, w = frame_shape
    return float(w) - x, y


def map_camera_to_screen_direct(
    x: float,
    y: float,
    *,
    frame_shape: tuple[int, int] | None,
) -> tuple[float, float] | None:
    """视频画面比例线性映射到主屏像素（与预览画面一致，已镜像则不再翻转）."""
    if not frame_shape:
        return None
    h, w = frame_shape
    if w <= 0 or h <= 0:
        return None
    import pyautogui

    sw, sh = pyautogui.size()
    sx = max(0.0, min(float(sw - 1), (float(x) / float(w)) * float(sw)))
    sy = max(0.0, min(float(sh - 1), (float(y) / float(h)) * float(sh)))
    return sx, sy


def _map_camera_homography(
    x: float,
    y: float,
    *,
    frame_shape: tuple[int, int] | None,
) -> tuple[float, float] | None:
    cal = get_calibration()
    if not cal.get("calibrated") or not cal.get("matrix"):
        return None
    import cv2

    x, y = _scale_camera_point(x, y, cal, frame_shape)
    camera_pts = cal.get("camera_points") or []
    if len(camera_pts) >= 4:
        hull = cv2.convexHull(np.float32(camera_pts))
        if not _point_in_hull(x, y, hull):
            return None
    matrix = np.float32(cal["matrix"])
    pt = np.float32([[[x, y]]])
    mapped = cv2.perspectiveTransform(pt, matrix)
    return float(mapped[0][0][0]), float(mapped[0][0][1])


def map_camera_to_screen(
    x: float,
    y: float,
    *,
    frame_shape: tuple[int, int] | None = None,
) -> tuple[float, float] | None:
    if get_mapping_mode() == "direct":
        return map_camera_to_screen_direct(x, y, frame_shape=frame_shape)
    return _map_camera_homography(x, y, frame_shape=frame_shape)


def map_camera_to_virtual_click(x: float, y: float, *, frame_shape: tuple[int, int] | None = None) -> dict[str, Any]:
    """将摄像头坐标映射到屏幕像素并执行点击."""
    from sensehub.execution.tools import gui

    mapped = map_camera_to_screen(x, y, frame_shape=frame_shape)
    if not mapped:
        mode = get_mapping_mode()
        if mode == "homography":
            raise RuntimeError("虚拟屏未校准或映射点在校准区域外")
        raise RuntimeError("无法映射食指坐标")
    sx, sy = mapped
    sw, sh = gui._screen_size()
    nx = max(0, min(1000, sx / sw * 1000))
    ny = max(0, min(1000, sy / sh * 1000))
    return gui.click({"x": nx, "y": ny, "mapped_screen_x": sx, "mapped_screen_y": sy})
