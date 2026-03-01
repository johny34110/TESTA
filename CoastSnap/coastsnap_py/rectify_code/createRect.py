"""Create a rectification grid (stub).

The MATLAB script ``createRect`` generates a rectification grid based
on ground control points and camera geometry.  This grid can then be
used to remap oblique images onto a regular Cartesian coordinate
system.

Recreating this functionality in Python requires detailed knowledge
about the camera parameters and the physical layout of the site.  The
current implementation provides a placeholder function
:func:`create_rectification_grid` that raises
``NotImplementedError``.  You can implement your own version to
compute an appropriate mapping for your dataset.
"""

from __future__ import annotations

from typing import Iterable, Tuple
import numpy as np
import cv2  # type: ignore
from .makeHomogTrans import compute_homography


def create_rectification_grid(
    gcp_image: Iterable[Tuple[float, float]],
    gcp_world: Iterable[Tuple[float, float]],
    grid_shape: Tuple[int, int] = (500, 500),
) -> np.ndarray:
    """Generate a rectification grid mapping image pixels to world coordinates.

    Given a set of corresponding ground control points (GCPs) in the
    image plane and the real‑world (metric) plane, this function
    computes a homography and then creates a lookup table that maps
    each pixel in a specified rectified grid to its world
    coordinates.

    Parameters
    ----------
    gcp_image : iterable of (float, float)
        Coordinates of ground control points in the image plane.
    gcp_world : iterable of (float, float)
        Corresponding coordinates of the same control points in the
        world (metric) plane.
    grid_shape : tuple of int, optional
        Desired size of the output rectified grid given as
        ``(height, width)``.  Defaults to a 500×500 grid.  The grid
        coordinates will range from (0, 0) in the upper left to
        (width‑1, height‑1) in the lower right of the rectified
        image.

    Returns
    -------
    numpy.ndarray
        A three‑dimensional array of shape ``(height, width, 2)`` where
        each element ``grid[y, x]`` contains the world coordinate
        ``(X, Y)`` corresponding to the pixel at position ``(x, y)`` in
        the rectified image.

    Notes
    -----
    The resulting grid does not account for elevation (Z) values.
    """
    # Compute homography mapping image to world coordinates
    H = compute_homography(gcp_image, gcp_world)
    height, width = grid_shape
    # Create meshgrid of pixel coordinates in rectified image
    xs, ys = np.meshgrid(np.arange(width, dtype=np.float32), np.arange(height, dtype=np.float32))
    coords = np.stack([xs, ys], axis=-1).reshape(-1, 1, 2)
    # Apply inverse homography to map rectified pixels to image plane
    inv_H = np.linalg.inv(H)
    # Map rectified grid points back to image coordinates
    img_coords = cv2.perspectiveTransform(coords, inv_H)
    # Map image coordinates to world coordinates using forward homography
    world_coords = cv2.perspectiveTransform(img_coords, H)
    world_coords = world_coords.reshape(height, width, 2)
    return world_coords


__all__ = ["create_rectification_grid"]