"""Interactive shoreline mapping (stub).

After rectifying an image, CoastSnap users digitise the shoreline by
clicking points along the waterline in the rectified view.  These
points are then saved for further analysis.  The MATLAB function
``CSPGmapShoreline`` provides such an interface.

This module defines a :func:`run` function that raises
``NotImplementedError``.  The :mod:`coastsnap_py.gui.CSP` class
implements shoreline mapping as part of the main GUI.  A future
stand‑alone shoreline mapping tool could reuse that code or provide
additional features such as undo/redo, snapping to tide lines or
semi‑automated edge detection.
"""

from __future__ import annotations


def run(*args, **kwargs) -> None:
    """Run the shoreline mapping GUI.

    Raises
    ------
    NotImplementedError
        Always raised because this function is a placeholder.
    """
    raise NotImplementedError(
        "Standalone shoreline mapping has not been implemented. "
        "Use the coastsnap_py.gui.CSP GUI for digitising shorelines."
    )


__all__ = ["run"]