"""Compute a homography transformation matrix.

In the CoastSnap Toolbox, homography transformations are used to
rectify oblique images of a beach to a plan view by mapping
ground control points (GCPs) in the image to their real‑world
coordinates.  This module provides a thin wrapper around
``cv2.findHomography`` to compute the transformation matrix.

The returned matrix can be passed to ``cv2.warpPerspective`` to
perform the rectification.
"""

from __future__ import annotations

from typing import Iterable, Tuple

import numpy as np
import cv2  # type: ignore


def compute_homography(
    src_points: Iterable[Tuple[float, float]],
    dst_points: Iterable[Tuple[float, float]],
    method: int = cv2.RANSAC,
    ransac_reproj_threshold: float = 5.0,
) -> np.ndarray:
    """Compute the homography matrix mapping ``src_points`` to ``dst_points``.

    Parameters
    ----------
    src_points : iterable of (x, y)
        Coordinates of points in the source (image) plane.  A minimum of
        four non‑collinear points are required.
    dst_points : iterable of (x, y)
        Coordinates of points in the destination (reference) plane.
    method : int, optional
        Method to be passed to ``cv2.findHomography``.  Default is
        ``cv2.RANSAC`` for robust estimation.  Pass 0 to disable RANSAC.
    ransac_reproj_threshold : float, optional
        Maximum allowed reprojection error to treat a point pair as an
        inlier when using RANSAC.  Ignored if ``method`` is 0.

    Returns
    -------
    numpy.ndarray
        A 3×3 homography matrix ``H`` such that ``x' ≈ H @ x`` (in
        homogeneous coordinates).  Raises ``RuntimeError`` if the
        homography cannot be computed.
    """
    src = np.asarray(src_points, dtype=float)
    dst = np.asarray(dst_points, dtype=float)
    if src.shape[0] < 4 or dst.shape[0] < 4:
        raise ValueError("At least four point pairs are required to compute a homography")
    H, status = cv2.findHomography(src, dst, method, ransac_reproj_threshold)
    if H is None:
        raise RuntimeError("Could not compute homography")
    return H


__all__ = ["compute_homography"]