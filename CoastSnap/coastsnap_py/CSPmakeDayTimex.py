"""Create a day timex image from CoastSnap photos (stub).

The MATLAB script ``CSPmakeDayTimex.m`` builds a time‑exposure
composite image (often called a timex) from all images captured on
a given day.  Timex images smooth out short‑term variability in
waves and provide a clear view of persistent shoreline features.

This Python module defines a :func:`make_day_timex` function which
currently raises :class:`NotImplementedError`.  A full implementation
would iterate over a list of images, average them or perform
statistical operations, and save the result to disk.
"""

from __future__ import annotations

from typing import Iterable, Union
from pathlib import Path
import numpy as np
import cv2  # type: ignore


def make_day_timex(images: Iterable[Union[str, Path]], output_path: Union[str, Path]) -> None:
    """Assemble a day timex image by averaging multiple photographs.

    This function reads all images supplied in ``images``, converts
    them to floating point arrays, and computes the per‑pixel mean
    across the stack.  The resulting image is converted back to
    unsigned 8‑bit integers and saved to ``output_path``.

    Parameters
    ----------
    images : iterable of str or pathlib.Path
        Paths to the images taken throughout a single day.
    output_path : str or pathlib.Path
        Filepath where the resulting timex image should be saved.
    """
    arrs = []
    for img_path in images:
        img = cv2.imread(str(img_path))
        if img is None:
            continue
        arrs.append(img.astype(np.float32))
    if not arrs:
        raise ValueError("No valid images provided to make_day_timex")
    stack = np.stack(arrs, axis=0)
    mean_img = np.mean(stack, axis=0).astype(np.uint8)
    # Ensure output directory exists
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), mean_img)


__all__ = ["make_day_timex"]