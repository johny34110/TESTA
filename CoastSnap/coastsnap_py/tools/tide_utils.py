"""Tide and water level utilities for CoastSnap (stub).

In the MATLAB toolbox, ``CSPgetTideLevel`` reads tide predictions or
measured water levels from a site‑specific database and returns the
tide height corresponding to a particular epoch timestamp.  Accurate
tide data are crucial for interpreting shoreline positions in a
geophysical context.

This module defines a placeholder function :func:`get_tide_level`
which currently raises :class:`NotImplementedError`.  You can
implement this function to read from a CSV file, database, or
web service providing tidal predictions for your study site.
"""

from __future__ import annotations

from typing import Optional, Tuple, List
import os
import csv
import bisect
from pathlib import Path

try:
    import scipy.io as _sio  # type: ignore
except Exception:
    _sio = None


_tide_times: List[float] = []
_tide_levels: List[float] = []
_tide_file_loaded: Optional[str] = None


def _load_tide_file(tide_file: str) -> None:
    """Load tide data from a CSV or MAT file into memory.

    If the file extension is ``.csv`` or similar, the file is
    interpreted as two‑column CSV with columns ``epoch`` and ``tide``.
    If the extension is ``.mat`` and the optional dependency
    ``scipy`` is available, the file is assumed to contain one or
    more variables holding times (epoch seconds) and tide levels; a
    heuristic is used to select appropriate arrays.  In both cases
    the resulting data must be sorted by time.
    """
    global _tide_times, _tide_levels, _tide_file_loaded
    _tide_times = []
    _tide_levels = []
    ext = Path(tide_file).suffix.lower()
    if ext in {".mat"}:
        # MATLAB tide file handling.  Some CoastSnap tide files store data in
        # structures (e.g. 'tide') with fields 'time' and 'level'.  Others
        # provide separate variables for time and tide.  We attempt to detect
        # structured data first, and fall back to a heuristic search.
        if _sio is None:
            raise ImportError(
                "scipy is required to read MATLAB tide files; please install scipy or provide a CSV file"
            )
        import numpy as _np  # import here to avoid dependency for CSV usage
        mat = _sio.loadmat(tide_file)
        # ----------------------------------------------------------------------
        # Structured tide: look for an array with named fields 'time' and 'level'
        for name, arr in mat.items():
            if name.startswith("__"):
                continue
            # Structured arrays have dtype.names
            try:
                if isinstance(arr, _np.ndarray) and arr.dtype.names and 'time' in arr.dtype.names and 'level' in arr.dtype.names:
                    for rec in arr.flat:
                        try:
                            time_data = _np.asarray(rec['time']).astype(float).squeeze()
                            level_data = _np.asarray(rec['level']).astype(float).squeeze()
                        except Exception:
                            continue
                        # Flatten to 1‑D
                        time_flat = time_data.reshape(-1)
                        level_flat = level_data.reshape(-1)
                        n = min(len(time_flat), len(level_flat))
                        if n == 0:
                            continue
                        time_flat = time_flat[:n]
                        level_flat = level_flat[:n]
                        # MATLAB datenum (days since 0000‑12‑31) to Unix epoch (seconds since 1970‑01‑01)
                        t_epoch = (time_flat - 719529.0) * 86400.0
                        order = _np.argsort(t_epoch)
                        # Assign to module‑level variables (declared as globals at top)
                        _tide_times = t_epoch[order].tolist()
                        _tide_levels = level_flat[order].tolist()
                        _tide_file_loaded = tide_file
                        return
            except Exception:
                continue
        # ----------------------------------------------------------------------
        # Fallback: heuristic search for 1‑D arrays representing time and level
        time_candidates = {}
        level_candidates = {}
        for name, arr in mat.items():
            if name.startswith("__"):
                continue
            try:
                data = arr.squeeze()
            except Exception:
                continue
            try:
                if isinstance(data, _np.ndarray) and data.ndim == 1:
                    n = name.lower()
                    if any(k in n for k in ["time", "epoch", "t"]):
                        time_candidates[name] = data
                    if any(k in n for k in ["tide", "water", "level", "wl", "h"]):
                        level_candidates[name] = data
            except Exception:
                continue
        def pick_best(cands):
            if not cands:
                return None
            return max(cands.values(), key=lambda x: x.size)
        t_arr = pick_best(time_candidates)
        h_arr = pick_best(level_candidates)
        if t_arr is None or h_arr is None:
            raise ValueError(
                f"Unable to identify time and tide variables in MATLAB file {tide_file}. Candidates: {list(time_candidates.keys())}, {list(level_candidates.keys())}"
            )
        # Truncate to common length
        n = min(len(t_arr), len(h_arr))
        t_arr = _np.asarray(t_arr[:n], dtype=float)
        h_arr = _np.asarray(h_arr[:n], dtype=float)
        # Convert datenum to epoch if values are large (heuristic threshold 1e5)
        if _np.all(t_arr > 1e5):
            t_arr = (t_arr - 719529.0) * 86400.0
        order = _np.argsort(t_arr)
        _tide_times = t_arr[order].tolist()
        _tide_levels = h_arr[order].tolist()
        _tide_file_loaded = tide_file
        return
    # Default: CSV
    with open(tide_file, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        # Read potential header
        header = next(reader)
        # Check if header contains non-numeric fields
        try:
            float(header[0])
            # No header; treat as data
            f.seek(0)
            reader = csv.reader(f)
        except ValueError:
            # header row consumed
            pass
        for row in reader:
            if not row:
                continue
            try:
                t = float(row[0])
                h = float(row[1])
            except (ValueError, IndexError):
                continue
            _tide_times.append(t)
            _tide_levels.append(h)
    # Ensure sorted
    if any(_tide_times[i] > _tide_times[i + 1] for i in range(len(_tide_times) - 1)):
        combined = sorted(zip(_tide_times, _tide_levels), key=lambda x: x[0])
        _tide_times, _tide_levels = zip(*combined)
        _tide_times = list(_tide_times)
        _tide_levels = list(_tide_levels)
    _tide_file_loaded = tide_file


def get_tide_level(epoch_time: float, tide_file: Optional[str] = None) -> Optional[float]:
    """Return the predicted or measured tide level at a given epoch time.

    This implementation reads tide data from a CSV file and performs a
    linear interpolation to estimate the tide height at the specified
    epoch timestamp.  The CSV file should have two columns:
    ``epoch`` (seconds since 1970‑01‑01 UTC) and ``tide`` (water
    level).  The data must be ordered by time.  The file is cached
    after the first read for efficiency.

    Parameters
    ----------
    epoch_time : float
        Epoch timestamp (seconds since 1970‑01‑01 UTC) for which to
        retrieve the tide level.
    tide_file : str, optional
        Path to the CSV file containing tide predictions.  If not
        provided, a default file ``./data/tides.csv`` relative to the
        current working directory is used.

    Returns
    -------
    float or None
        The interpolated tide level at the specified time, or ``None``
        if no data are available or the timestamp is outside the range
        of the dataset.
    """
    # Determine file to use
    if tide_file is None:
        # Default to the data directory relative to this module
        module_dir = os.path.dirname(__file__)
        default_path = os.path.abspath(os.path.join(module_dir, os.pardir, os.pardir, "data", "tides.csv"))
        tide_file = default_path
    # Load file if necessary
    if _tide_file_loaded != tide_file:
        if not os.path.isfile(tide_file):
            return None
        _load_tide_file(tide_file)
    if not _tide_times:
        return None
    # Use bisect for interpolation
    idx = bisect.bisect_left(_tide_times, epoch_time)
    # If the timestamp matches the first or last entry exactly, return that value
    if idx == 0:
        # epoch_time is before the first time; check exact match
        if _tide_times and epoch_time == _tide_times[0]:
            return _tide_levels[0]
        return None
    if idx == len(_tide_times):
        # epoch_time is after the last time; check exact match with last
        if _tide_times and epoch_time == _tide_times[-1]:
            return _tide_levels[-1]
        return None
    # Normal case: interpolate between bounding points
    t0, t1 = _tide_times[idx - 1], _tide_times[idx]
    h0, h1 = _tide_levels[idx - 1], _tide_levels[idx]
    # Linear interpolation
    frac = (epoch_time - t0) / (t1 - t0)
    return h0 + frac * (h1 - h0)


def get_nearest_tide_level(epoch_time: float, tide_file: Optional[str] = None) -> Optional[float]:
    """Return the tide level from the sample closest in time to ``epoch_time``.

    Unlike :func:`get_tide_level`, which performs a linear interpolation between
    the bracketing tide measurements, this function simply returns the
    recorded tide level whose timestamp is nearest to the requested
    ``epoch_time``.  If the tide file has not been loaded, it will be
    loaded using the same rules as :func:`get_tide_level`.

    Parameters
    ----------
    epoch_time : float
        Epoch timestamp (seconds since 1970‑01‑01 UTC) for which to
        retrieve the tide level.
    tide_file : str, optional
        Path to the CSV or MATLAB file containing tide predictions.  If
        not provided, the default tide file in the ``data`` directory
        will be used.

    Returns
    -------
    float or None
        The tide level of the closest sample in time, or ``None`` if
        no data are available.
    """
    # Determine which file to use
    if tide_file is None:
        module_dir = os.path.dirname(__file__)
        default_path = os.path.abspath(os.path.join(module_dir, os.pardir, os.pardir, "data", "tides.csv"))
        tide_file = default_path
    # Load file if needed
    if _tide_file_loaded != tide_file:
        if not os.path.isfile(tide_file):
            return None
        _load_tide_file(tide_file)
    if not _tide_times:
        return None
    # Find the index of the closest time
    import bisect
    idx = bisect.bisect_left(_tide_times, epoch_time)
    # Check neighbour indices
    if idx == 0:
        return _tide_levels[0]
    if idx == len(_tide_times):
        return _tide_levels[-1]
    t0, t1 = _tide_times[idx - 1], _tide_times[idx]
    h0, h1 = _tide_levels[idx - 1], _tide_levels[idx]
    # Choose closer in absolute difference
    if abs(epoch_time - t0) <= abs(epoch_time - t1):
        return h0
    return h1

# Export both tide functions from this module.  If ``get_nearest_tide_level``
# is available, include it in the public API along with ``get_tide_level``.
__all__ = ["get_tide_level", "get_nearest_tide_level"]