"""Image rectification (oblique -> plan view) using a calibrated camera model."""

from __future__ import annotations

from typing import Tuple

import numpy as np
import cv2  # type: ignore


def rectify_oblique_to_plane(
    oblq_bgr: np.ndarray,
    camera_matrix: np.ndarray,
    dist_coeffs: np.ndarray,
    rvec: np.ndarray,
    tvec: np.ndarray,
    xlim: Tuple[float, float],
    ylim: Tuple[float, float],
    resolution: float,
    z_plane: float,
    interpolation: int = cv2.INTER_LINEAR,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, Tuple[float, float, float, float], float]:
    """Rectify an oblique image onto a horizontal plane.

    Parameters
    ----------
    oblq_bgr : np.ndarray
        Source image in BGR (OpenCV).
    camera_matrix, dist_coeffs, rvec, tvec
        Calibrated camera parameters.
    xlim, ylim : (float, float)
        Limits (in local station meters) for plan view grid.
    resolution : float
        Grid resolution in meters per pixel.
    z_plane : float
        Plane elevation in local station meters (Z relative to station).

    Returns
    -------
    rect_bgr : np.ndarray
        Rectified plan-view image.
    mapx, mapy : np.ndarray
        Remap arrays (float32) from rectified pixels to oblique pixels.
    world_limits : (xmin, xmax, ymin, ymax)
        Limits in local meters used for rectification.
    resolution : float
        Resolution used.
    """
    xmin, xmax = float(xlim[0]), float(xlim[1])
    ymin, ymax = float(ylim[0]), float(ylim[1])
    res = float(resolution)
    if res <= 0:
        raise ValueError("resolution must be positive")

    out_w = int(round((xmax - xmin) / res)) + 1
    out_h = int(round((ymax - ymin) / res)) + 1
    if out_w <= 1 or out_h <= 1:
        raise ValueError("Invalid output grid size computed from limits/resolution")

    # Define plan-view grid coordinates (local station frame).
    xs = xmin + np.arange(out_w, dtype=np.float32) * res
    ys = ymax - np.arange(out_h, dtype=np.float32) * res  # top row is ymax (north), increases downward
    X, Y = np.meshgrid(xs, ys)
    Z = np.full_like(X, float(z_plane), dtype=np.float32)
    pts3d = np.stack([X, Y, Z], axis=-1).reshape(-1, 3).astype(np.float64)

    # Project world points into the oblique image
    proj, _ = cv2.projectPoints(pts3d, rvec, tvec, camera_matrix, dist_coeffs)
    proj = proj.reshape(out_h, out_w, 2).astype(np.float32)
    mapx = proj[..., 0]
    mapy = proj[..., 1]

    rect = cv2.remap(
        oblq_bgr,
        mapx,
        mapy,
        interpolation,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(0, 0, 0),
    )
    return rect, mapx, mapy, (xmin, xmax, ymin, ymax), res


__all__ = ["rectify_oblique_to_plane"]
