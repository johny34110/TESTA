"""Select a region of interest in an image (stub).

Some CoastSnap workflows allow users to crop a particular region of
the rectified image for focused analysis (e.g., cropping to a
transect corridor).  The MATLAB script ``CSPGcropShorelinePoints``
provides this functionality, whereas this module lays out a general
placeholder for region selection.

The :func:`run` function below raises ``NotImplementedError``.  You can
implement region selection using Tkinter's canvas rectangle tools or
with interactive widgets from libraries like ``matplotlib``.
"""

from __future__ import annotations


def run(*args, **kwargs) -> None:
    """Run the region selection GUI.

    Raises
    ------
    NotImplementedError
        Always raised because this function is not yet implemented.
    """
    raise NotImplementedError(
        "Region selection functionality has not been implemented in Python."
    )


__all__ = ["run"]