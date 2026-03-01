"""Convert metric coordinates to pixel coordinates (stub).

The inverse of the ``P2m`` function in the original MATLAB code is
``m2P``, which converts real‑world metric coordinates back to pixel
coordinates in a rectified image.  Performing this conversion
requires knowledge of the camera calibration and site geometry.

This module contains a placeholder :func:`metric_to_pixel` function
which currently raises :class:`NotImplementedError`.  It is provided
to maintain structural compatibility with the MATLAB project.
"""

from __future__ import annotations

from typing import Tuple
import numpy as np
import cv2  # type: ignore


def metric_to_pixel(x_m: float, y_m: float, H: np.ndarray) -> Tuple[float, float]:
    """Convert metric coordinates to pixel coordinates using a homography.

    Given a pair of coordinates in the rectified (metric) plane and
    a 3×3 homography matrix ``H`` that maps image coordinates to
    metric coordinates, this function computes the corresponding pixel
    coordinates by applying the inverse homography.

    Parameters
    ----------
    x_m, y_m : float
        Coordinates in the metric plane.
    H : numpy.ndarray
        A 3×3 homography matrix mapping image coordinates to metric
        coordinates.  Its inverse will be used to convert back.

    Returns
    -------
    (float, float)
        Pixel coordinates in the image plane.
    """
    inv_H = np.linalg.inv(H)
    pt = np.array([[[float(x_m), float(y_m)]]], dtype=np.float32)
    pixel = cv2.perspectiveTransform(pt, inv_H)
    X, Y = pixel[0, 0]
    return float(X), float(Y)


__all__ = ["metric_to_pixel"]