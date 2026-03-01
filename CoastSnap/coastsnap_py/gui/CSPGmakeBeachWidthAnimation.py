"""Create an animation of beach width change (stub).

In the MATLAB CoastSnap toolbox, ``CSPGmakeBeachWidthAnimation``
creates an animation showing how the width of the beach evolves
through time based on a time series of rectified images and shoreline
positions.  The animation can be useful for visualising seasonal
trends, storm impacts and other dynamic behaviours.

This module provides a placeholder :func:`run` function that raises
``NotImplementedError``.  You can implement the function using
matplotlib's animation tools (``matplotlib.animation.FuncAnimation``)
or other video libraries to assemble frames from your shoreline data.
"""

from __future__ import annotations

from typing import Iterable, Optional
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import datetime

from ..tools.shoreline_utils import compute_beach_width


def run(
    times: Iterable[float],
    shoreline_positions: Iterable[float],
    backshore_position: float,
    interval: int = 500,
    output_path: Optional[str] = None,
) -> None:
    """Animate beach width changes over time.

    Parameters
    ----------
    times : iterable of float
        Epoch timestamps corresponding to shoreline positions.
    shoreline_positions : iterable of float
        Shoreline positions along a transect.  These are used to
        compute beach width relative to a fixed backshore position.
    backshore_position : float
        Position of the backshore (fixed reference point) along the
        transect.  Beach width is computed as
        ``shoreline_position - backshore_position``.
    interval : int, optional
        Delay between frames in milliseconds.  Defaults to 500 ms.
    output_path : str, optional
        If provided, the animation will be saved as an MP4 video at
        this path.  Otherwise the animation will be displayed
        interactively.
    """
    ts = list(times)
    pos = list(shoreline_positions)
    if len(ts) != len(pos) or not ts:
        raise ValueError("times and shoreline_positions must have the same non‑zero length")
    widths = [compute_beach_width(p, backshore_position) for p in pos]
    dt_list = [datetime.datetime.utcfromtimestamp(t) for t in ts]
    fig, ax = plt.subplots()
    ax.set_xlabel("Time (UTC)")
    ax.set_ylabel("Beach Width (m)")
    ax.set_ylim(min(widths) - 1.0, max(widths) + 1.0)
    line, = ax.plot([], [], marker='o')

    def init():
        ax.set_xlim(dt_list[0], dt_list[-1])
        line.set_data([], [])
        return line,

    def update(frame_idx):
        line.set_data(dt_list[: frame_idx + 1], widths[: frame_idx + 1])
        return line,

    ani = FuncAnimation(fig, update, frames=len(ts), init_func=init, interval=interval, blit=True)
    if output_path:
        ani.save(output_path, writer="ffmpeg", fps=1000 / interval)
    else:
        plt.show()


__all__ = ["run"]