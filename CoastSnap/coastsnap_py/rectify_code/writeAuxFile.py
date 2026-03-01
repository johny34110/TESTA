"""Write auxiliary files for rectification (stub).

The original CoastSnap toolbox uses auxiliary files to store
intermediate data required for rectifying images.  This might
include calibration matrices, lookup tables, or metadata about
the rectification process.

This module currently defines a placeholder function
:func:`write_aux_file` that raises :class:`NotImplementedError`.  It
exists to preserve the structure of the MATLAB code.  If you need to
serialize intermediate data for your own rectification workflow,
consider using Python's built‑in :mod:`pickle` module, JSON, or other
serialization libraries.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
import pickle
import os


def write_aux_file(path: str | Path, data: Any) -> None:
    """Serialize arbitrary Python data to a binary file using pickle.

    This helper writes data to disk in a binary format using the
    :mod:`pickle` module.  The file will be overwritten if it already
    exists.  Use this function to store intermediate calibration data,
    rectification grids or other objects that are inconvenient to
    recompute.  When reading the file back, you can use
    ``pickle.load``.

    Parameters
    ----------
    path : str or pathlib.Path
        Destination file path where the auxiliary data should be saved.
    data : any
        Arbitrary Python object to be serialized.
    """
    p = Path(path)
    # Ensure parent directory exists
    if p.parent and not p.parent.exists():
        os.makedirs(p.parent, exist_ok=True)
    with open(p, "wb") as f:
        pickle.dump(data, f)


__all__ = ["write_aux_file"]