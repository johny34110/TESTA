"""Select ground control points in an image (stub).

Ground control points (GCPs) are pairs of corresponding points in
the oblique and rectified planes that determine the homography for
rectification.  The MATLAB GUI provides a user interface for
selecting these points, typically four or more per image.

This module defines a :func:`run` function that raises
``NotImplementedError``.  The :mod:`coastsnap_py.gui.CSPGrectifyImage`
module contains a simple demonstration of selecting GCPs via mouse
clicks on a Tkinter canvas.  That implementation may serve as a
starting point for a more full‑featured GCP selection tool.
"""

from __future__ import annotations


def run(*args, **kwargs) -> None:
    """Run the GCP selection GUI.

    Raises
    ------
    NotImplementedError
        Always raised because this function is a placeholder.
    """
    raise NotImplementedError(
        "GCP selection functionality has not been implemented in Python. "
        "Use coastsnap_py.gui.CSPGrectifyImage.run_gui for a simple demonstration."
    )


__all__ = ["run"]