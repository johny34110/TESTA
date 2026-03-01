"""Create a shoreline trend animation (stub).

The script ``CSPGmakeShorelineTrendAnimation`` in the MATLAB
CoastSnap toolbox produces an animated plot showing the long‑term
trend of shoreline change, often superimposed on time series of tides
or storm events.  Such animations are useful for presentations and
public outreach.

This Python module provides a :func:`run` function which is a
placeholder.  To implement the full functionality you can use
matplotlib's animation API to draw the evolving shoreline trend on a
chart or overlay it on a sequence of rectified images.
"""

from __future__ import annotations

from typing import Iterable, Optional
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import datetime

from ..tools.shoreline_utils import compute_cumulative_change


def run(
    times: Iterable[float],
    shoreline_positions: Iterable[float],
    interval: int = 500,
    output_path: Optional[str] = None,
) -> None:
    """Animate the cumulative shoreline change and its linear trend.

    Parameters
    ----------
    times : iterable of float
        Epoch timestamps corresponding to shoreline positions.
    shoreline_positions : iterable of float
        Shoreline positions (e.g., distances along a transect).
    interval : int, optional
        Delay between frames in milliseconds.  Defaults to 500 ms.
    output_path : str, optional
        If provided, the animation will be saved as an MP4 file at this
        location; otherwise it will be displayed interactively.
    """
    ts = list(times)
    pos = list(shoreline_positions)
    if len(ts) != len(pos) or not ts:
        raise ValueError("times and shoreline_positions must have the same non‑zero length")
    changes = compute_cumulative_change(ts, pos)
    # Convert times to matplotlib dates
    dt_list = [datetime.datetime.utcfromtimestamp(t) for t in ts]
    # Fit a linear trend to the changes vs time in days
    # Convert datetime to ordinal (days) for regression
    days = np.array([d.toordinal() for d in dt_list], dtype=float)
    y = np.array(changes, dtype=float)
    # Perform linear regression (least squares)
    A = np.vstack([days, np.ones_like(days)]).T
    m, c = np.linalg.lstsq(A, y, rcond=None)[0]
    fig, ax = plt.subplots()
    ax.set_xlabel("Time (UTC)")
    ax.set_ylabel("Cumulative Shoreline Change (m)")
    ax.set_ylim(min(changes) - 1.0, max(changes) + 1.0)
    ax.set_xlim(dt_list[0], dt_list[-1])
    line_change, = ax.plot([], [], marker='o', label="Cumulative change")
    # Plot full trend line once
    x_trend = np.array([dt_list[0], dt_list[-1]])
    days_trend = np.array([d.toordinal() for d in x_trend])
    y_trend = m * days_trend + c
    ax.plot(x_trend, y_trend, color='red', linestyle='--', label="Linear trend")
    ax.legend()

    def init():
        line_change.set_data([], [])
        return line_change,

    def update(frame_idx):
        line_change.set_data(dt_list[: frame_idx + 1], changes[: frame_idx + 1])
        return line_change,

    ani = FuncAnimation(fig, update, frames=len(ts), init_func=init, interval=interval, blit=True)
    if output_path:
        ani.save(output_path, writer="ffmpeg", fps=1000 / interval)
    else:
        plt.show()


__all__ = ["run"]