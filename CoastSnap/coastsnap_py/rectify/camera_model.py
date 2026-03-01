"""Camera model utilities (intrinsics + pose estimation).

This module implements a pragmatic CoastSnap-style camera calibration:

* Intrinsics are built from image size and a candidate horizontal FOV.
* Pose is estimated via OpenCV solvePnP using 3D GCP coordinates (local station frame)
  and 2D pixel coordinates.
* An optional scalar optimisation searches for the best FOV within the database
  min/max bounds by minimising reprojection RMS error.

The goal is to replicate the MATLAB workflow that searches over FOV/DOF and
then rectifies onto a horizontal plane.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Tuple, Optional

import numpy as np
import cv2  # type: ignore
from scipy.optimize import minimize_scalar


@dataclass
class PnPResult:
    camera_matrix: np.ndarray
    dist_coeffs: np.ndarray
    rvec: np.ndarray
    tvec: np.ndarray
    reproj_rms_px: float
    fov_deg: float


def build_camera_matrix_from_fov(width: int, height: int, fov_deg: float) -> np.ndarray:
    """Build a pinhole camera matrix from image dimensions and horizontal FOV.

    Parameters
    ----------
    width, height : int
        Image dimensions in pixels.
    fov_deg : float
        Horizontal field of view in degrees.

    Returns
    -------
    numpy.ndarray
        3x3 camera intrinsic matrix K.
    """
    fov_rad = np.deg2rad(float(fov_deg))
    cx = width / 2.0
    cy = height / 2.0
    # fx from horizontal FOV; assume square pixels => fy ~ fx
    fx = (width / 2.0) / np.tan(fov_rad / 2.0)
    fy = fx
    K = np.array([[fx, 0.0, cx], [0.0, fy, cy], [0.0, 0.0, 1.0]], dtype=np.float64)
    return K


def _reprojection_rms(
    object_points: np.ndarray,
    image_points: np.ndarray,
    K: np.ndarray,
    dist: np.ndarray,
    rvec: np.ndarray,
    tvec: np.ndarray,
) -> float:
    proj, _ = cv2.projectPoints(object_points, rvec, tvec, K, dist)
    proj = proj.reshape(-1, 2)
    err = proj - image_points
    rms = float(np.sqrt(np.mean(np.sum(err * err, axis=1))))
    return rms


def solve_pnp_pose(
    object_points_xyz: Iterable[Tuple[float, float, float]],
    image_points_uv: Iterable[Tuple[float, float]],
    K: np.ndarray,
    dist_coeffs: Optional[np.ndarray] = None,
) -> Tuple[np.ndarray, np.ndarray, float]:
    """Estimate camera pose using solvePnP.

    Returns (rvec, tvec, reprojection_rms_px).
    """
    obj = np.asarray(list(object_points_xyz), dtype=np.float64).reshape(-1, 3)
    img = np.asarray(list(image_points_uv), dtype=np.float64).reshape(-1, 2)

    if obj.shape[0] < 4:
        raise ValueError("solvePnP requires at least 4 point correspondences")
    if img.shape[0] != obj.shape[0]:
        raise ValueError("object_points and image_points must have the same length")

    if dist_coeffs is None:
        dist_coeffs = np.zeros((5, 1), dtype=np.float64)
    else:
        dist_coeffs = np.asarray(dist_coeffs, dtype=np.float64).reshape(-1, 1)

    ok, rvec, tvec = cv2.solvePnP(
        obj,
        img,
        K,
        dist_coeffs,
        flags=cv2.SOLVEPNP_ITERATIVE,
    )
    if not ok:
        raise RuntimeError("solvePnP failed to estimate pose")

    rms = _reprojection_rms(obj, img, K, dist_coeffs, rvec, tvec)
    return rvec, tvec, rms


def optimise_fov_scalar(
    width: int,
    height: int,
    object_points_xyz: Iterable[Tuple[float, float, float]],
    image_points_uv: Iterable[Tuple[float, float]],
    fov_min_deg: float,
    fov_max_deg: float,
    dist_coeffs: Optional[np.ndarray] = None,
) -> PnPResult:
    """Search for the best horizontal FOV (scalar) that minimises reprojection RMS.

    This mirrors the MATLAB workflow that searches across a plausible FOV range.
    """
    obj_list = list(object_points_xyz)
    img_list = list(image_points_uv)

    def objective(fov: float) -> float:
        K = build_camera_matrix_from_fov(width, height, float(fov))
        try:
            rvec, tvec, rms = solve_pnp_pose(obj_list, img_list, K, dist_coeffs)
            return rms
        except Exception:
            return 1e9

    res = minimize_scalar(
        objective,
        bounds=(float(fov_min_deg), float(fov_max_deg)),
        method="bounded",
        options={"xatol": 0.05},
    )
    best_fov = float(res.x)
    K_best = build_camera_matrix_from_fov(width, height, best_fov)
    if dist_coeffs is None:
        dist_coeffs = np.zeros((5, 1), dtype=np.float64)
    rvec, tvec, rms = solve_pnp_pose(obj_list, img_list, K_best, dist_coeffs)
    return PnPResult(
        camera_matrix=K_best,
        dist_coeffs=np.asarray(dist_coeffs, dtype=np.float64),
        rvec=rvec,
        tvec=tvec,
        reproj_rms_px=float(rms),
        fov_deg=best_fov,
    )


__all__ = [
    "PnPResult",
    "build_camera_matrix_from_fov",
    "solve_pnp_pose",
    "optimise_fov_scalar",
]
