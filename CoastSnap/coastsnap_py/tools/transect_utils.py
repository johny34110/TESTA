"""Transect utilities for CoastSnap (stub).

Transects are cross‑shore lines along which shoreline positions and
beach widths are measured.  In the CoastSnap toolbox, transects may
be defined in geographic coordinates and projected onto rectified
images to extract elevation or shoreline change time series.

This module provides a set of placeholder functions that define and
work with transects.  Implementations of these functions will vary
depending on your project requirements and data sources.
"""

from __future__ import annotations

from typing import Iterable, Tuple, List, Optional


def define_transect(
    start: Tuple[float, float],
    end: Tuple[float, float],
    num_points: int = 100,
) -> List[Tuple[float, float]]:
    """Define a linear transect between two points (placeholder).

    This function returns a list of equally spaced points along a line
    segment connecting ``start`` and ``end``.  You may modify this
    behaviour to accommodate curved transects or other sampling
    strategies.

    Parameters
    ----------
    start, end : tuple of float
        Coordinates of the start and end points of the transect in
        metric space.
    num_points : int, optional
        Number of sample points along the transect.  Default is 100.

    Returns
    -------
    list of (float, float)
        List of points along the transect.
    """
    x0, y0 = start
    x1, y1 = end
    xs = [x0 + (x1 - x0) * i / (num_points - 1) for i in range(num_points)]
    ys = [y0 + (y1 - y0) * i / (num_points - 1) for i in range(num_points)]
    return list(zip(xs, ys))


def sample_shoreline_along_transect(
    transect: Iterable[Tuple[float, float]],
    shoreline_points: Iterable[Tuple[float, float]],
    buffer: float = 5.0,
) -> Optional[Tuple[float, float]]:
    """Sample the shoreline position along a transect (placeholder).

    Given a list of transect points and a set of shoreline points
    (e.g., digitised from a rectified image), this function returns
    the shoreline point that is closest to the transect within a
    specified buffer distance.  If no shoreline points are found within
    the buffer, ``None`` is returned.  This behaviour is merely a
    template; you should adjust it according to your analysis needs.

    Parameters
    ----------
    transect : iterable of (float, float)
        Points defining the transect in metric space.
    shoreline_points : iterable of (float, float)
        Digitised shoreline points in metric space.
    buffer : float, optional
        Maximum distance from the transect within which to search for
        shoreline points.  Default is 5.0 units (same units as
        coordinates).

    Returns
    -------
    (float, float) or None
        The shoreline point closest to the transect (within the buffer),
        or ``None`` if no such point exists.
    """
    import math

    min_dist = float("inf")
    closest_point: Optional[Tuple[float, float]] = None
    for spt in shoreline_points:
        sx, sy = spt
        for tpt in transect:
            tx, ty = tpt
            d = math.hypot(sx - tx, sy - ty)
            if d < min_dist and d <= buffer:
                min_dist = d
                closest_point = (sx, sy)
    return closest_point


__all__ = ["define_transect", "sample_shoreline_along_transect"]

def load_transects_from_mat(filepath: str) -> List[Tuple[Tuple[float, float], Tuple[float, float]]]:
    """Load transect endpoints from a MATLAB .mat file.

    This function attempts to parse a .mat file that defines a set of
    cross‑shore transects.  Because the internal structure of these
    files can vary between CoastSnap sites, the parser uses a set of
    heuristics to extract pairs of x/y coordinates representing the
    start and end points of each transect.  The coordinates are
    returned in the coordinate system of the rectified image (often
    pixel units).  If no transects can be extracted, an empty list
    is returned.

    Parameters
    ----------
    filepath : str
        Path to the .mat file to load.

    Returns
    -------
    list of ((float, float), (float, float))
        List of transects, each represented by a pair of (x, y) points.
    """
    import numpy as np
    from scipy.io import loadmat

    try:
        data = loadmat(filepath, squeeze_me=True, struct_as_record=False)
    except Exception:
        return []
    endpoints: List[Tuple[Tuple[float, float], Tuple[float, float]]] = []
    # Exclude MATLAB meta keys
    exclude_keys = {"__header__", "__version__", "__globals__"}
    for name, var in data.items():
        if name in exclude_keys:
            continue
        v = var
        # Case 1: numeric array with shape (n, 4) or (4, n)
        if isinstance(v, np.ndarray) and issubclass(v.dtype.type, np.number):
            arr = np.asarray(v)
            # Ensure 2D
            if arr.ndim == 2:
                if arr.shape[1] == 4:
                    for row in arr:
                        try:
                            x0, y0, x1, y1 = float(row[0]), float(row[1]), float(row[2]), float(row[3])
                            endpoints.append(((x0, y0), (x1, y1)))
                        except Exception:
                            continue
                    if endpoints:
                        return endpoints
                if arr.shape[0] == 4:
                    arr2 = arr.T
                    for row in arr2:
                        try:
                            x0, y0, x1, y1 = float(row[0]), float(row[1]), float(row[2]), float(row[3])
                            endpoints.append(((x0, y0), (x1, y1)))
                        except Exception:
                            continue
                    if endpoints:
                        return endpoints
                # if array has shape (n, 2) or (2, n) and n >= 2, interpret first two pairs as endpoints
                if arr.ndim == 2 and arr.shape[1] == 2 and arr.shape[0] >= 2:
                    # treat arr as list of (x,y) points; group consecutive pairs
                    pts = [(float(row[0]), float(row[1])) for row in arr]
                    # create segments connecting pairs of points
                    for i in range(0, len(pts) - 1, 2):
                        endpoints.append((pts[i], pts[i+1]))
                    if endpoints:
                        return endpoints
                if arr.ndim == 2 and arr.shape[0] == 2 and arr.shape[1] >= 2:
                    pts = [(float(arr[0, j]), float(arr[1, j])) for j in range(arr.shape[1])]
                    for i in range(0, len(pts) - 1, 2):
                        endpoints.append((pts[i], pts[i+1]))
                    if endpoints:
                        return endpoints
        # Case 2: structured/record array or object with fields x/y
        try:
            # If v has 'x' and 'y' attributes (e.g. mat_struct)
            if hasattr(v, 'x') and hasattr(v, 'y'):
                try:
                    xs_arr = np.asarray(v.x)
                    ys_arr = np.asarray(v.y)
                except Exception:
                    xs_arr = None
                    ys_arr = None
                if xs_arr is not None and ys_arr is not None:
                    # If arrays have shape (2, N), interpret columns as endpoints
                    if xs_arr.ndim == 2 and ys_arr.ndim == 2:
                        # (2, N) orientation
                        if xs_arr.shape[0] == 2 and ys_arr.shape[0] == 2:
                            nseg = min(xs_arr.shape[1], ys_arr.shape[1])
                            for i in range(nseg):
                                try:
                                    x0, x1 = float(xs_arr[0, i]), float(xs_arr[1, i])
                                    y0, y1 = float(ys_arr[0, i]), float(ys_arr[1, i])
                                    endpoints.append(((x0, y0), (x1, y1)))
                                except Exception:
                                    continue
                            if endpoints:
                                continue
                        # (N, 2) orientation
                        if xs_arr.shape[1] == 2 and ys_arr.shape[1] == 2:
                            xs_t = xs_arr.T
                            ys_t = ys_arr.T
                            nseg = min(xs_t.shape[1], ys_t.shape[1])
                            for i in range(nseg):
                                try:
                                    x0, x1 = float(xs_t[0, i]), float(xs_t[1, i])
                                    y0, y1 = float(ys_t[0, i]), float(ys_t[1, i])
                                    endpoints.append(((x0, y0), (x1, y1)))
                                except Exception:
                                    continue
                            if endpoints:
                                continue
                    # If 1D arrays, pair first and last values
                    xs_flat = xs_arr.flatten().astype(float)
                    ys_flat = ys_arr.flatten().astype(float)
                    if xs_flat.size >= 2 and ys_flat.size >= 2:
                        try:
                            endpoints.append(((float(xs_flat[0]), float(ys_flat[0])), (float(xs_flat[-1]), float(ys_flat[-1]))))
                        except Exception:
                            pass
                        continue
        except Exception:
            pass
        # Additional case: numpy structured array with dtype names 'x' and 'y'
        # Some MATLAB files store transects in a struct array where each record has
        # fields x and y containing 2×N arrays of endpoints (as in SLtransects_manly.mat).
        if isinstance(v, np.ndarray) and hasattr(v, 'dtype') and v.dtype.names:
            names = v.dtype.names
            if 'x' in names and 'y' in names:
                # Iterate over each record in the structured array
                for rec in v.flat:
                    try:
                        xs_arr = np.asarray(rec['x'])
                        ys_arr = np.asarray(rec['y'])
                    except Exception:
                        continue
                    # If arrays have shape (2, N), interpret columns as start/end points
                    if xs_arr.ndim == 2 and ys_arr.ndim == 2:
                        if xs_arr.shape[0] == 2 and ys_arr.shape[0] == 2:
                            nseg = min(xs_arr.shape[1], ys_arr.shape[1])
                            for i in range(nseg):
                                try:
                                    x0 = float(xs_arr[0, i])
                                    x1 = float(xs_arr[1, i])
                                    y0 = float(ys_arr[0, i])
                                    y1 = float(ys_arr[1, i])
                                    endpoints.append(((x0, y0), (x1, y1)))
                                except Exception:
                                    continue
                            continue
                        # If arrays have shape (N, 2), transpose to (2, N)
                        if xs_arr.shape[1] == 2 and ys_arr.shape[1] == 2:
                            xs_t = xs_arr.T
                            ys_t = ys_arr.T
                            nseg = min(xs_t.shape[1], ys_t.shape[1])
                            for i in range(nseg):
                                try:
                                    x0 = float(xs_t[0, i])
                                    x1 = float(xs_t[1, i])
                                    y0 = float(ys_t[0, i])
                                    y1 = float(ys_t[1, i])
                                    endpoints.append(((x0, y0), (x1, y1)))
                                except Exception:
                                    continue
                            continue
                    # If arrays are 1D with length >=2, pair first and last values
                    xs_flat = xs_arr.flatten().astype(float)
                    ys_flat = ys_arr.flatten().astype(float)
                    if xs_flat.size >= 2 and ys_flat.size >= 2:
                        try:
                            endpoints.append(((float(xs_flat[0]), float(ys_flat[0])), (float(xs_flat[-1]), float(ys_flat[-1]))))
                        except Exception:
                            pass
                # After processing records, if endpoints were extracted return them
                if endpoints:
                    return endpoints
    return endpoints

__all__.extend(["load_transects_from_mat"])