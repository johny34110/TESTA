"""Entry point for running CoastSnap from the command line.

This module allows you to launch the CoastSnap graphical user
interface simply by running ``python -m coastsnap_py`` from
the directory that contains the ``coastsnap_py`` package.

It imports the ``main`` function from ``coastsnap_py.gui.CSP`` and
executes it.  See the documentation in that module for details.
"""

from .gui.CSP import main as _main

if __name__ == "__main__":
    _main()