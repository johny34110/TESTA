"""Shoreline analysis utilities for CoastSnap (stub).

The CoastSnap toolbox provides a suite of tools for analysing
shoreline positions through time, including calculations of beach
width, shoreline change rates and visualisation of these metrics.

This module contains placeholder functions for such analyses.  Some
simple implementations are provided (e.g., computing cumulative
shoreline change), while others are left as stubs for future
development.
"""

from __future__ import annotations

from typing import Iterable, List, Tuple


def compute_cumulative_change(
    shoreline_times: Iterable[float],
    shoreline_positions: Iterable[float],
) -> List[float]:
    """Compute cumulative shoreline change over time.

    Given a sequence of shoreline positions (e.g., cross‑shore
    distances) and the corresponding times, this function returns the
    cumulative change relative to the first observation.  Positive
    values indicate accretion (shoreline moving seaward) and negative
    values indicate erosion.

    Parameters
    ----------
    shoreline_times : iterable of float
        Epoch timestamps corresponding to the shoreline positions.  The
        times must be in ascending order.
    shoreline_positions : iterable of float
        Scalar shoreline position values (e.g., distances along a
        transect) at each timestamp.

    Returns
    -------
    list of float
        Cumulative change relative to the first position.
    """
    positions = list(shoreline_positions)
    if not positions:
        return []
    baseline = positions[0]
    return [p - baseline for p in positions]


def compute_beach_width(
    shoreline_position: float,
    backshore_position: float,
) -> float:
    """Compute beach width given shoreline and backshore positions.

    In CoastSnap, beach width is often defined as the distance between
    the shoreline and a fixed backshore reference point along a
    cross‑shore transect.  This implementation returns the simple
    difference between those two positions.  Depending on your site
    and dataset, you may need to account for slope or other
    geometric factors.

    Parameters
    ----------
    shoreline_position : float
        Position of the shoreline along a transect (e.g., in metres).
    backshore_position : float
        Position of a fixed backshore reference point along the same
        transect.

    Returns
    -------
    float
        Beach width (shoreline position minus backshore position).
    """
    return shoreline_position - backshore_position


def make_shoreline_change_plot(
    times: Iterable[float],
    changes: Iterable[float],
    title: str = "Shoreline Change Over Time",
) -> None:
    """Create a simple time series plot of shoreline change.

    This function uses matplotlib to produce a line plot of shoreline
    change versus time.  It is intentionally minimal and can be
    extended to replicate the more sophisticated plotting utilities
    found in the original MATLAB code.

    Parameters
    ----------
    times : iterable of float
        Epoch timestamps corresponding to shoreline change values.
    changes : iterable of float
        Shoreline change values (e.g., cumulative change in metres).
    title : str, optional
        Title of the plot.
    """
    import datetime
    import matplotlib.pyplot as plt

    # Convert epoch times to Python datetime for x‑axis ticks.
    dt = [datetime.datetime.utcfromtimestamp(t) for t in times]
    plt.figure(figsize=(8, 4))
    plt.plot(dt, list(changes), marker='o')
    plt.xlabel("Time (UTC)")
    plt.ylabel("Shoreline Change (m)")
    plt.title(title)
    plt.grid(True)
    plt.tight_layout()
    plt.show()


__all__ = [
    "compute_cumulative_change",
    "compute_beach_width",
    "make_shoreline_change_plot",
]