"""Select images for processing (stub).

The CoastSnap GUI includes actions to select a subset of images from
the available dataset for bulk rectification and shoreline mapping.
This module defines a placeholder :func:`run` function that raises
``NotImplementedError``.  A future implementation might display a
list of image filenames with checkboxes or provide filtering options
based on date, tide, or user annotations.
"""

from __future__ import annotations


def run(*args, **kwargs) -> None:
    """Run the image selection GUI.

    Raises
    ------
    NotImplementedError
        Always raised because this function is a placeholder.
    """
    raise NotImplementedError(
        "Image selection functionality has not been implemented in Python."
    )


__all__ = ["run"]