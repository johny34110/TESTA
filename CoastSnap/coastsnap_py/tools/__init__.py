"""Utility functions for the CoastSnap toolbox.

This subpackage contains Python equivalents of the general
purpose MATLAB functions located at the root of the
CoastSnap‑Toolbox and in the `tools` directory.  Only a
handful of functions are implemented at present.  Others
are provided as stubs to maintain the original package
structure and may raise :class:`NotImplementedError` when
called.
"""

from .file_utils import parse_filename, get_image_list  # noqa: F401
from .paths import load_paths  # noqa: F401
from .time_utils import epoch_to_local_time  # noqa: F401
from .tide_utils import get_tide_level  # noqa: F401
from .site_db import read_site_database  # noqa: F401
from .transect_utils import define_transect, sample_shoreline_along_transect  # noqa: F401
from .shoreline_utils import (
    compute_cumulative_change,
    compute_beach_width,
    make_shoreline_change_plot,
)  # noqa: F401

__all__ = [
    "parse_filename",
    "get_image_list",
    "load_paths",
    "epoch_to_local_time",
    "get_tide_level",
    "read_site_database",
    "define_transect",
    "sample_shoreline_along_transect",
    "compute_cumulative_change",
    "compute_beach_width",
    "make_shoreline_change_plot",
]