"""Graphical user interface components for the CoastSnap toolbox.

This subpackage contains the Python implementation of the CoastSnap
GUI as well as stand‑alone scripts corresponding to the various
`CSPG...m` files in the MATLAB version.  Only a subset of these
modules currently provide functionality; the remainder are
present as stubs to provide a scaffold for future development.
"""

from .CSP import CoastSnapGUI, main  # noqa: F401

# Import stubbed GUI modules so they are discoverable via ``coastsnap_py.gui``.
from .CSPGmakeBeachWidthAnimation import run as run_beach_width_animation  # noqa: F401
from .CSPGmakeShorelineChangePlot import run as run_shoreline_change_plot  # noqa: F401
from .CSPGmakeShorelineTrendAnimation import run as run_shoreline_trend_animation  # noqa: F401
from .CSPGmakeVideoOfShoreline import run as run_shoreline_video  # noqa: F401
from .CSPGrectifyImage import rectify_image, run_gui as run_rectify_gui  # noqa: F401
from .CSPGselectImages import run as run_select_images  # noqa: F401
from .CSPGselectRegion import run as run_select_region  # noqa: F401
from .CSPGsetGCPs import run as run_set_gcps  # noqa: F401
from .CSPGmapShoreline import run as run_map_shoreline  # noqa: F401

__all__ = [
    "CoastSnapGUI",
    "main",
    "run_beach_width_animation",
    "run_shoreline_change_plot",
    "run_shoreline_trend_animation",
    "run_shoreline_video",
    "rectify_image",
    "run_rectify_gui",
    "run_select_images",
    "run_select_region",
    "run_set_gcps",
    "run_map_shoreline",
]