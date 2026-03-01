"""Rectification code for the CoastSnap Python toolbox.

This subpackage contains modules that replicate the functionality of the
MATLAB scripts in the original CoastSnap Toolbox's ``rectifyCode``
directory.  These functions are used to convert between time
representations, compute homography transformations, and provide helper
utilities for creating rectified images from oblique beach
photographs.

Many of the MATLAB functions are not yet implemented in Python.  For
those functions we provide stub modules that raise ``NotImplementedError``
so that the overall package structure matches the original project.

Implemented functions
=====================

The following modules provide working implementations or thin
wrappers around existing Python libraries:

* :mod:`epoch2Matlab` – convert UNIX epoch timestamps to MATLAB datenum
  values.
* :mod:`makeHomogTrans` – compute a homography matrix given source
  and destination control points using OpenCV.

Other modules currently expose placeholder functions.  See the
documentation of each module for details and contribute additional
implementations as needed.
"""

from .epoch2Matlab import epoch_to_matlab_datenum  # noqa:F401
from .makeHomogTrans import compute_homography      # noqa:F401