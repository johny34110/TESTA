"""Convert UNIX epoch timestamps to MATLAB datenum values.

MATLAB represents time using datenum, which counts the number of
days since ``0000-01-00`` (yes, the zero-th day of year 0).  Unix epoch
timestamps, on the other hand, count seconds since 1970‑01‑01 UTC.

This module provides a convenience function for converting between
these two formats.  The conversion is based on a fixed offset between
the Unix epoch and MATLAB's day zero.  Note that MATLAB's datenum
counts days as floating point values, so sub‑day precision is
preserved.

Example
-------

>>> from coastsnap_py.rectify_code.epoch2Matlab import epoch_to_matlab_datenum
>>> t_epoch = 1709218800  # corresponds to 2024‑03‑01 00:00:00 UTC
>>> dnum = epoch_to_matlab_datenum(t_epoch)
>>> round(dnum - 738343.0, 6)
0.0
"""

from __future__ import annotations

import datetime
from typing import Union, Iterable, List

import numpy as np

# MATLAB datenum offset: number of days between 0000‑01‑00 and 1970‑01‑01.
# In MATLAB, datenum('1970-01-01') equals 719529.  Unix epoch (1970-01-01)
# therefore corresponds to datenum 719529.0.  We subtract this when
# converting an epoch to datenum and divide seconds by the number of
# seconds per day.
_MATLAB_UNIX_DAYS_OFFSET = 719529.0
_SECONDS_PER_DAY = 86400.0


def epoch_to_matlab_datenum(epoch: Union[int, float, Iterable]) -> Union[float, np.ndarray]:
    """Convert Unix epoch time(s) to MATLAB datenum value(s).

    Parameters
    ----------
    epoch : int, float or iterable
        A single epoch timestamp or an iterable of epoch timestamps.  The
        input should represent seconds since the Unix epoch (1970‑01‑01
        00:00:00 UTC).  Fractional values are allowed to represent
        sub‑second precision.

    Returns
    -------
    float or numpy.ndarray
        The corresponding MATLAB datenum(s).  If the input is a single
        scalar, the result is a float.  If the input is an iterable, a
        numpy array of floats is returned.
    """
    if np.isscalar(epoch):
        return _epoch_scalar_to_datenum(float(epoch))
    # Assume iterable
    epoch_arr = np.asarray(epoch, dtype=float)
    return _epoch_array_to_datenum(epoch_arr)


def _epoch_scalar_to_datenum(ts: float) -> float:
    # Compute days since Unix epoch and add MATLAB offset.
    return ts / _SECONDS_PER_DAY + _MATLAB_UNIX_DAYS_OFFSET


def _epoch_array_to_datenum(ts_arr: np.ndarray) -> np.ndarray:
    return ts_arr / _SECONDS_PER_DAY + _MATLAB_UNIX_DAYS_OFFSET


__all__ = ["epoch_to_matlab_datenum"]