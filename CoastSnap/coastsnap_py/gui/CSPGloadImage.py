"""Load image wrapper for the GUI (stub).

In MATLAB, ``CSPGloadImage.m`` is called by the main GUI when the
user clicks the "load image" button.  In this Python package, the
image loading logic has been integrated directly into the
``CoastSnapGUI`` class (see :mod:`coastsnap_py.gui.CSP`).  This
module exists solely for compatibility and currently forwards to
the GUI's ``load_image`` method when invoked explicitly.
"""

from __future__ import annotations

from .CSP import CoastSnapGUI  # avoid circular import issues


def load_image(gui: CoastSnapGUI) -> None:
    """Call the GUI's image loader.

    Parameters
    ----------
    gui : CoastSnapGUI
        Instance of the CoastSnapGUI.
    """
    gui.load_image()


__all__ = ["load_image"]