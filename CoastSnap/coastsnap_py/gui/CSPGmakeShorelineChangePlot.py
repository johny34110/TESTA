"""Create a plot of shoreline change (stub).

The MATLAB script ``CSPGmakeShorelineChangePlot`` generates a time
series plot illustrating how the shoreline position varies over a
specified period.  It often includes error bars, tide information and
annotations for significant events.

This Python module provides a :func:`run` function that currently
raises ``NotImplementedError``.  You can implement this function
using :mod:`matplotlib` to create customised plots based on your
digitised shoreline data and optionally leverage functions from
``coastsnap_py.tools.shoreline_utils``.
"""

from __future__ import annotations

from typing import Iterable, Optional
import csv

from ..tools.shoreline_utils import compute_cumulative_change, make_shoreline_change_plot


def run(shoreline_file: str, title: Optional[str] = None) -> None:
    """Generate a shoreline change plot from a CSV file.

    This function reads shoreline positions from a CSV file, computes
    cumulative change relative to the first observation, and then
    produces a time series plot.  The CSV file must contain two
    columns: ``epoch`` and ``position``.  The epoch column should
    contain Unix timestamps (seconds since 1970‑01‑01 UTC), and the
    position column should contain a scalar measure of the shoreline
    (e.g., cross‑shore distance from a reference point).

    Parameters
    ----------
    shoreline_file : str
        Path to a CSV file containing shoreline data.  The file may
        optionally include a header row.
    title : str, optional
        Title of the plot.  Defaults to ``"Shoreline Change Over Time"``.
    """
    times: list[float] = []
    positions: list[float] = []
    with open(shoreline_file, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        # Skip header if present
        header_read = False
        for row in reader:
            if not header_read:
                try:
                    float(row[0])
                    # row is numeric; treat as data
                except ValueError:
                    # skip header
                    header_read = True
                    continue
            if not row:
                continue
            try:
                t = float(row[0])
                p = float(row[1])
            except (ValueError, IndexError):
                continue
            times.append(t)
            positions.append(p)
    if not times:
        raise ValueError(f"No valid shoreline data found in {shoreline_file}")
    changes = compute_cumulative_change(times, positions)
    make_shoreline_change_plot(times, changes, title or "Shoreline Change Over Time")


__all__ = ["run"]