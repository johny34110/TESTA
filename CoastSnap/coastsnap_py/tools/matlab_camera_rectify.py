"""MATLAB-compatible camera-model rectification for CoastSnap.

This module ports the key logic of MATLAB's ``CSPGrectifyImage`` workflow.

Main ideas (matching MATLAB):
1) Convert GCP Easting/Northing to local x/y relative to station origin.
   Elevations remain in the absolute vertical datum (e.g., AHD), matching
   the original MATLAB script.
2) Treat camera position (x,y,z) as *known* and fixed.
3) Optimise focal length (fx=fy) by grid-search across FOV limits.
4) For each trial focal length, do a non-linear least squares fit of
   azimuth/tilt/roll to minimise reprojection error.
5) Rectify by projecting a horizontal plane ``z = tide_level + tidal_offset``
   onto a regular (x,y) grid defined by rectification limits.

This aims for behavioural similarity to the MATLAB toolbox rather than a
generic OpenCV solvePnP pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple, Dict, Any

import math
import numpy as np
import cv2  # type: ignore


@dataclass
class LCP:
    """Local Camera Parameters (intrinsics) - simplified pinhole model."""

    fx: float
    fy: float
    cx: float
    cy: float


def make_lcpp3(camera_res: Tuple[int, int], fx: float) -> LCP:
    """Create simplified intrinsics equivalent to MATLAB's makeLCPP3 (for our use)."""
    w, h = camera_res
    return LCP(fx=float(fx), fy=float(fx), cx=float(w) / 2.0, cy=float(h) / 2.0)


def _rot_z(a: float) -> np.ndarray:
    ca, sa = math.cos(a), math.sin(a)
    return np.array([[ca, -sa, 0.0], [sa, ca, 0.0], [0.0, 0.0, 1.0]], dtype=float)


def _rot_x(a: float) -> np.ndarray:
    ca, sa = math.cos(a), math.sin(a)
    return np.array([[1.0, 0.0, 0.0], [0.0, ca, -sa], [0.0, sa, ca]], dtype=float)


def _rot_y(a: float) -> np.ndarray:
    ca, sa = math.cos(a), math.sin(a)
    return np.array([[ca, 0.0, sa], [0.0, 1.0, 0.0], [-sa, 0.0, ca]], dtype=float)


def _rotation_from_az_tilt_roll(az: float, tilt: float, roll: float) -> np.ndarray:
    """World->camera rotation from CoastSnap angles.

    CoastSnap defines:
      * azimuth relative to true north (yaw about +Z)
      * tilt relative to horizon (90=horizontal, 0=nadir)
      * roll about the viewing axis

    We map tilt to a pitch angle such that:
      pitch = tilt - 90deg
    giving pitch=0 at horizontal and pitch=-90deg at nadir.

    Note: If your site uses a different sign convention, you'll see it as
    mirrored/rotated plan views. This is the *closest* mapping to MATLAB's
    description and is designed to be easily adjusted in one place.
    """
    pitch = tilt - (math.pi / 2.0)
    # Compose rotations. This convention is stable and matches common
    # CoastSnap/Argus local coordinate usage.
    return _rot_y(roll) @ _rot_x(pitch) @ _rot_z(az)


def project_xyz_to_uv(
    xyz: np.ndarray,
    cam_xyz: Tuple[float, float, float],
    az_tilt_roll: Tuple[float, float, float],
    lcp: LCP,
) -> np.ndarray:
    """Project 3D world points to image pixels using pinhole camera model."""
    xyz = np.asarray(xyz, dtype=float)
    C = np.array(cam_xyz, dtype=float).reshape(1, 3)
    az, tilt, roll = az_tilt_roll
    R = _rotation_from_az_tilt_roll(float(az), float(tilt), float(roll))

    Pw = xyz - C
    Pc = (R @ Pw.T).T

    z = Pc[:, 2]
    z_safe = np.where(np.abs(z) < 1e-9, 1e-9, z)
    u = lcp.fx * (Pc[:, 0] / z_safe) + lcp.cx
    v = lcp.fy * (Pc[:, 1] / z_safe) + lcp.cy
    return np.stack([u, v], axis=1)


def _residuals_angles(
    angles: np.ndarray,
    xyz: np.ndarray,
    uv_obs: np.ndarray,
    cam_xyz: Tuple[float, float, float],
    lcp: LCP,
) -> np.ndarray:
    uv_pred = project_xyz_to_uv(xyz, cam_xyz, (angles[0], angles[1], angles[2]), lcp)
    return (uv_pred - uv_obs).reshape(-1)


def _lm_solve_3params(
    x0: np.ndarray,
    fun,
    max_iter: int = 80,
    lam0: float = 1e-2,
) -> Tuple[np.ndarray, float]:
    """Tiny Levenberg-Marquardt for 3 parameters (no SciPy required)."""
    x = x0.astype(float).copy()
    lam = float(lam0)
    r = fun(x)
    prev = float(np.dot(r, r))
    for _ in range(max_iter):
        # Numerical Jacobian
        J = np.zeros((r.size, 3), dtype=float)
        eps = 1e-6
        for k in range(3):
            dx = np.zeros(3, dtype=float)
            dx[k] = eps
            rk = fun(x + dx)
            J[:, k] = (rk - r) / eps
        A = J.T @ J + lam * np.eye(3)
        g = J.T @ r
        try:
            delta = -np.linalg.solve(A, g)
        except np.linalg.LinAlgError:
            lam *= 10.0
            continue
        x_new = x + delta
        r_new = fun(x_new)
        cur = float(np.dot(r_new, r_new))
        if cur < prev:
            x = x_new
            r = r_new
            prev = cur
            lam = max(lam / 2.0, 1e-10)
            if np.linalg.norm(delta) < 1e-6:
                break
        else:
            lam *= 5.0
    rmse = math.sqrt(prev / max(1, (r.size // 2)))
    return x, rmse


def fit_geometry_for_fx(
    xyz: np.ndarray,
    uv_obs: np.ndarray,
    camera_res: Tuple[int, int],
    cam_xyz: Tuple[float, float, float],
    angles0_rad: Tuple[float, float, float],
    fx: float,
) -> Tuple[np.ndarray, float, LCP]:
    lcp = make_lcpp3(camera_res, fx)
    x0 = np.array([angles0_rad[0], angles0_rad[1], angles0_rad[2]], dtype=float)

    def fun(a: np.ndarray) -> np.ndarray:
        return _residuals_angles(a, xyz, uv_obs, cam_xyz, lcp)

    angles, rmse = _lm_solve_3params(x0, fun)
    return angles, rmse, lcp


def fx_grid_from_fov_limits(
    camera_res: Tuple[int, int],
    fov_min_deg: float,
    fov_max_deg: float,
    step_px: int = 5,
) -> np.ndarray:
    w, _ = camera_res
    fx_max = 0.5 * w / math.tan(float(fov_min_deg) * math.pi / 360.0)
    fx_min = 0.5 * w / math.tan(float(fov_max_deg) * math.pi / 360.0)
    fx_min = step_px * round(fx_min / step_px)
    fx_max = step_px * round(fx_max / step_px)
    if fx_max < fx_min:
        fx_min, fx_max = fx_max, fx_min
    return np.arange(fx_min, fx_max + step_px, step_px, dtype=float)


def fov_from_fx(camera_res: Tuple[int, int], fx: float) -> float:
    w, _ = camera_res
    return math.degrees(2.0 * math.atan(w / (2.0 * float(fx))))


def matlab_style_calibrate(
    xyz: np.ndarray,
    uv_obs: np.ndarray,
    camera_res: Tuple[int, int],
    cam_xyz: Tuple[float, float, float],
    angles0_deg: Tuple[float, float, float],
    fov_limits_deg: Tuple[float, float],
) -> Dict[str, Any]:
    """Grid-search focal length + fit angles, matching MATLAB CSPGrectifyImage."""
    az0, tilt0, roll0 = [math.radians(float(x)) for x in angles0_deg]
    fx_grid = fx_grid_from_fov_limits(camera_res, fov_limits_deg[0], fov_limits_deg[1])
    best: Dict[str, Any] | None = None
    for fx in fx_grid:
        angles, rmse, lcp = fit_geometry_for_fx(
            xyz=xyz,
            uv_obs=uv_obs,
            camera_res=camera_res,
            cam_xyz=cam_xyz,
            angles0_rad=(az0, tilt0, roll0),
            fx=float(fx),
        )
        if best is None or rmse < float(best["rmse"]):
            best = {"fx": float(fx), "lcp": lcp, "angles_rad": angles, "rmse": float(rmse)}
    assert best is not None
    best["fov_deg"] = float(fov_from_fx(camera_res, best["fx"]))
    best["angles_deg"] = [float(math.degrees(a)) for a in best["angles_rad"]]
    return best


def rectify_image_matlab_style(
    bgr_image: np.ndarray,
    calib: Dict[str, Any],
    cam_xyz: Tuple[float, float, float],
    rectxy: Tuple[float, float, float, float, float, float],
    rectz_abs: float,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Rectify by projecting z=rectz plane on (x,y) grid.

    rectxy matches MATLAB: [x_min dx x_max y_min dy y_max]
    Returns (rectified_bgr, xgrid, ygrid).
    """
    x_min, dx, x_max, y_min, dy, y_max = [float(v) for v in rectxy]
    xs = np.arange(x_min, x_max + dx, dx, dtype=float)
    ys = np.arange(y_min, y_max + dy, dy, dtype=float)
    X, Y = np.meshgrid(xs, ys)
    Z = np.full_like(X, float(rectz_abs), dtype=float)

    pts = np.stack([X.ravel(), Y.ravel(), Z.ravel()], axis=1)
    lcp: LCP = calib["lcp"]
    az, tilt, roll = calib["angles_rad"]
    uv = project_xyz_to_uv(pts, cam_xyz, (float(az), float(tilt), float(roll)), lcp)

    mapx = uv[:, 0].reshape(Y.shape).astype(np.float32)
    mapy = uv[:, 1].reshape(Y.shape).astype(np.float32)

    rect = cv2.remap(
        bgr_image,
        mapx,
        mapy,
        interpolation=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(0, 0, 0),
    )
    return rect, xs, ys


__all__ = [
    "matlab_style_calibrate",
    "rectify_image_matlab_style",
    "fx_grid_from_fov_limits",
    "fov_from_fx",
    "project_xyz_to_uv",
]
