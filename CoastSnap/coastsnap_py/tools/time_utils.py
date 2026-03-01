"""Time conversion utilities for CoastSnap.

The original MATLAB toolbox uses epoch times (seconds since
01/01/1970) and converts them to MATLAB datenum or local times
for tide interpolation.  Here we provide minimal functions to
convert epoch timestamps to Python :class:`datetime.datetime`
objects in local time.  Additional time operations can be
implemented as needed.
"""

from __future__ import annotations

import datetime
from typing import List, Iterable, Optional


def epoch_to_local_time(epoch: int | float, tz_offset_hours: float = 0.0) -> datetime.datetime:
    """Convert a UNIX epoch time (in seconds) to a local datetime.

    Parameters
    ----------
    epoch : int or float
        Seconds since 01/01/1970 UTC.
    tz_offset_hours : float, optional
        Offset from UTC in hours.  For example, +10 for Australian
        Eastern Standard Time (AEST) or -5 for US Eastern Standard
        Time.  Defaults to 0 (UTC).

    Returns
    -------
    datetime.datetime
        Datetime object representing the local time.
    """
    utc = datetime.datetime.utcfromtimestamp(epoch)
    delta = datetime.timedelta(hours=tz_offset_hours)
    return utc + delta


def epoch_to_matlab_datenum(epoch: int | float) -> float:
    """Approximate conversion of epoch time to MATLAB datenum.

    MATLAB datenum counts days from 0 Jan 0000 and includes fractional
    days.  The Unix epoch (1 Jan 1970) corresponds to MATLAB
    datenum 719529.  This function adds the number of days since
    epoch to 719529 to approximate MATLAB's internal representation.

    Parameters
    ----------
    epoch : int or float
        Seconds since 01/01/1970 UTC.

    Returns
    -------
    float
        MATLAB datenum value.
    """
    days_since_epoch = epoch / (24 * 3600)
    return 719529 + days_since_epoch


__all__ = ["epoch_to_local_time", "epoch_to_matlab_datenum"]