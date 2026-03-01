"""
Camera calibration utilities for CoastSnap.

This module provides functions to estimate camera intrinsics (focal length)
and extrinsics (orientation and position) from Ground Control Points (GCPs).
The algorithm loosely follows the method used in the CoastSnap MATLAB
function `CSPGrectifyImage.m`, in which a range of field‑of‑view (FOV)
values is searched to minimise reprojection error. The functions here use
OpenCV's `solvePnP` to estimate the rotation and translation of the camera
given known world coordinates and their corresponding image points.

Note that this implementation is a simplification of the MATLAB version.
It assumes the camera has zero lens distortion, uses the same focal length
in both x and y directions, and ignores skew. The calibration search is
performed over a linear range of FOV values. If more accurate calibration
is required (e.g., optimisation over azimuth, tilt, roll and FOV), this
module can be extended accordingly.

Functions
---------
calibrate_camera_with_fov(gcp_image, gcp_world, image_shape, fov_range)
    Try multiple FOVs and return the camera matrix and extrinsics with the
    smallest reprojection error.

compute_rectification_homography(camera_matrix, rvec, tvec, world_limits, res)
    Given camera parameters and world limits, compute a homography that
    maps the oblique image to a rectified orthonormal grid.

"""

from __future__ import annotations

import math
from typing import Iterable, Tuple, Optional, List

import numpy as np
import cv2


def calibrate_camera_with_fov(
    gcp_image: np.ndarray,
    gcp_world: np.ndarray,
    image_shape: Tuple[int, int],
    fov_range: Tuple[float, float],
    n_trials: int = 7,
) -> Optional[Tuple[np.ndarray, np.ndarray, np.ndarray, float, float]]:
    """Estimate camera intrinsics and extrinsics by searching over a FOV range.

    Parameters
    ----------
    gcp_image : ndarray of shape (N, 2)
        Pixel coordinates of the ground control points in the image.
    gcp_world : ndarray of shape (N, 3)
        World coordinates (Easting, Northing, Elevation) of the ground
        control points in the same order as ``gcp_image``.
    image_shape : (height, width)
        Dimensions of the input image in pixels (rows, columns).
    fov_range : (fov_min, fov_max)
        Minimum and maximum horizontal field of view (in degrees) to search.
    n_trials : int, optional
        Number of FOV samples to evaluate between ``fov_min`` and ``fov_max``.

    Returns
    -------
    (camera_matrix, rvec, tvec, fov_deg, error) or None
        Returns the camera intrinsic matrix, rotation vector, translation
        vector, the chosen FOV (degrees) and the mean reprojection error
        in pixels. Returns ``None`` if calibration fails for all FOVs.

    Notes
    -----
    This function assumes zero lens distortion and identical focal lengths in
    x and y (square pixels). The principal point is assumed to be at the
    centre of the image. ``cv2.solvePnP`` is used with the EPnP algorithm.
    """
    if gcp_image.shape[0] < 4 or gcp_world.shape[0] < 4:
        raise ValueError("At least four GCPs are required for calibration.")

    height, width = image_shape
    fov_min, fov_max = fov_range
    # ensure fov_min < fov_max
    if fov_min >= fov_max:
        fov_min, fov_max = fov_max, fov_min
    # sample FOVs linearly between min and max
    candidates = np.linspace(fov_min, fov_max, num=n_trials)
    best_error = np.inf
    best_params = None

    # ensure arrays are float32 for cv2 functions
    gcp_image = np.asarray(gcp_image, dtype=np.float32)
    gcp_world = np.asarray(gcp_world, dtype=np.float32)

    for fov_deg in candidates:
        fov_rad = math.radians(fov_deg)
        # compute focal length in pixels from horizontal FOV
        # f = (width/2) / tan(FOV/2)
        f_pixels = (width / 2.0) / math.tan(fov_rad / 2.0)
        camera_matrix = np.array([
            [f_pixels, 0.0, width / 2.0],
            [0.0, f_pixels, height / 2.0],
            [0.0, 0.0, 1.0],
        ], dtype=np.float32)
        dist_coeffs = np.zeros((4, 1), dtype=np.float32)

        # Solve PnP to estimate rotation and translation
        retval, rvec, tvec = cv2.solvePnP(
            gcp_world,
            gcp_image,
            camera_matrix,
            dist_coeffs,
            flags=cv2.SOLVEPNP_EPNP,
        )
        if not retval:
            # try another method if EPnP fails
            retval, rvec, tvec = cv2.solvePnP(
                gcp_world,
                gcp_image,
                camera_matrix,
                dist_coeffs,
                flags=cv2.SOLVEPNP_ITERATIVE,
            )
        if not retval:
            continue

        # compute reprojection error
        projected, _ = cv2.projectPoints(
            gcp_world, rvec, tvec, camera_matrix, dist_coeffs
        )
        projected = projected.reshape(-1, 2)
        diffs = gcp_image - projected
        errors = np.linalg.norm(diffs, axis=1)
        mean_err = float(np.mean(errors))
        if mean_err < best_error:
            best_error = mean_err
            best_params = (camera_matrix, rvec, tvec, fov_deg, mean_err)

    return best_params


def compute_rectification_homography(
    camera_matrix: np.ndarray,
    rvec: np.ndarray,
    tvec: np.ndarray,
    world_limits: Tuple[float, float, float, float],
    resolution: float,
    image_shape: Tuple[int, int],
    ) -> Tuple[np.ndarray, Tuple[int, int]]:
    """Compute a homography to rectify the oblique image onto a world grid.

    Parameters
    ----------
    camera_matrix : ndarray of shape (3, 3)
        Intrinsic matrix of the camera (computed by calibration).
    rvec : ndarray of shape (3, 1)
        Rotation vector from `solvePnP`.
    tvec : ndarray of shape (3, 1)
        Translation vector from `solvePnP`.
    world_limits : (x_min, x_max, y_min, y_max)
        Limits of the world plane in metres (eastings and northings).
    resolution : float
        Desired ground sample distance (metres per pixel) for the rectified
        image.
    image_shape : (height, width)
        Dimensions of the input image in pixels.

    Returns
    -------
    H : ndarray of shape (3, 3)
        Homography matrix that maps points in the original image to the
        rectified image.
    output_size : (int, int)
        (width, height) of the rectified image in pixels.

    Notes
    -----
    The rectified image is oriented such that the x-axis corresponds to
    increasing Easting and the y-axis corresponds to increasing Northing. The
    origin (0, 0) of the rectified image corresponds to the upper-left
    corner (x_min, y_max) in world coordinates.
    """
    x_min, x_max, y_min, y_max = world_limits
    # number of pixels in rectified image
    nx = int(round((x_max - x_min) / resolution))
    ny = int(round((y_max - y_min) / resolution))
    # world corners (upper-left, upper-right, lower-right, lower-left)
    world_corners = np.array([
        [x_min, y_max, 0.0],  # world upper-left
        [x_max, y_max, 0.0],  # world upper-right
        [x_max, y_min, 0.0],  # world lower-right
        [x_min, y_min, 0.0],  # world lower-left
    ], dtype=np.float32)
    # project world corners into image coordinates
    projected, _ = cv2.projectPoints(world_corners, rvec, tvec, camera_matrix, np.zeros((4, 1), dtype=np.float32))
    projected = projected.reshape(-1, 2).astype(np.float32)
    # destination corners in rectified image
    dest_corners = np.array([
        [0.0, 0.0],        # rectified upper-left
        [nx, 0.0],         # rectified upper-right
        [nx, ny],          # rectified lower-right
        [0.0, ny],         # rectified lower-left
    ], dtype=np.float32)
    # compute homography from original image to rectified grid
    H, status = cv2.getPerspectiveTransform(projected, dest_corners)
    return H, (nx, ny)
