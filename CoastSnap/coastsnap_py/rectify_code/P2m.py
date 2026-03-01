"""Convert pixel coordinates to metric coordinates (stub).

The original CoastSnap toolbox includes functions ``P2m`` and ``m2P`` to
convert between pixel coordinates in the rectified image and real‑world
metric coordinates on the beach.  These conversions require
information about the camera calibration, scale, rotation and
translation of the scene, which are not trivial to reproduce
without a detailed site model.

This module provides a placeholder function :func:`pixel_to_metric` that
raises :class:`NotImplementedError` when called.  It exists to allow
importing the module in a way that mirrors the structure of the MATLAB
project.  Contributions are welcome to provide a full implementation
based on known GCPs and site geometry.
"""

from __future__ import annotations

from typing import Tuple, Iterable, Optional
import numpy as np
import cv2  # type: ignore


def pixel_to_metric(x: float, y: float, H: np.ndarray) -> Tuple[float, float]:
    """Convert pixel coordinates to metric coordinates using a homography.

    Given pixel coordinates in the image plane and a 3×3 homography
    matrix ``H`` that maps pixel coordinates to metric coordinates (i.e.,
    from the oblique image to the rectified plane), this function
    computes the corresponding real‑world coordinates.  The homography
    is typically computed using :func:`coastsnap_py.rectify_code.makeHomogTrans.compute_homography`.

    Parameters
    ----------
    x, y : float
        Pixel coordinates in the image plane.
    H : numpy.ndarray
        A 3×3 homography matrix mapping image coordinates to metric
        coordinates.

    Returns
    -------
    (float, float)
        Coordinates in the metric (rectified) plane.

    Notes
    -----
    The homography matrix must have been computed from corresponding
    source and destination points such that multiplying by ``H``
    transforms image pixels into the desired metric coordinate system.
    """
    pt = np.array([[[float(x), float(y)]]], dtype=np.float32)
    metric = cv2.perspectiveTransform(pt, H)
    X, Y = metric[0, 0]
    return float(X), float(Y)


__all__ = ["pixel_to_metric"]