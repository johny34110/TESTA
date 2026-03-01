"""Rectify an image using provided ground control points.

The MATLAB function ``CSPGrectifyImage`` provides a user interface
for selecting ground control points (GCPs) and performs a
perspective transformation to create a rectified, plan‑view image.

In Python, this functionality is provided via two helper functions:

* :func:`rectify_image` – takes a file path and GCP arrays and
  returns a rectified image as a NumPy array.
* :func:`run_gui` – simple demonstration of image rectification using
  Tkinter.  This GUI does not replicate all features of the MATLAB
  version but illustrates the core rectification procedure.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Tuple, Optional

import cv2  # type: ignore
import numpy as np
from PIL import Image

from ..rectify_code.makeHomogTrans import compute_homography


def rectify_image(
    image_path: str | Path,
    src_points: Iterable[Tuple[float, float]],
    dst_points: Iterable[Tuple[float, float]],
    output_size: Optional[Tuple[int, int]] = None,
) -> np.ndarray:
    """Rectify an image using ground control points.

    Parameters
    ----------
    image_path : str or pathlib.Path
        Path to the image file to be rectified.
    src_points : iterable of (x, y)
        Pixel coordinates of the GCPs in the oblique image.
    dst_points : iterable of (x, y)
        Corresponding coordinates of the GCPs in the rectified plane
        (e.g., metric coordinates scaled to pixels).
    output_size : tuple of (int, int), optional
        Desired size (width, height) of the rectified image.  If
        ``None``, the bounding box of ``dst_points`` determines the
        output canvas size.

    Returns
    -------
    numpy.ndarray
        The rectified image as a NumPy array in BGR format (OpenCV
        convention).

    Notes
    -----
    This function does not perform any reprojection of geographic
    coordinates.  The ``dst_points`` should be provided in the same
    coordinate system you wish the rectified image to be rendered in
    (e.g., pixels scaled to metres).  For interactive use through
    :func:`run_gui`, these coordinates are typically selected by the
    user in an on‑screen window.
    """
    # Load image using cv2 to get BGR array.
    img = cv2.imread(str(image_path))
    if img is None:
        raise FileNotFoundError(f"Unable to load image from {image_path}")
    src = np.asarray(list(src_points), dtype=float)
    dst = np.asarray(list(dst_points), dtype=float)
    # Compute homography
    H = compute_homography(src, dst)
    # Determine output size
    if output_size is None:
        max_x = int(max(p[0] for p in dst))
        max_y = int(max(p[1] for p in dst))
        output_size = (max_x + 1, max_y + 1)
    # Warp the image
    rectified = cv2.warpPerspective(img, H, output_size)
    return rectified


def run_gui(image_path: str | Path) -> None:
    """Demonstrate interactive rectification using Tkinter.

    A simple GUI is provided to select four GCPs on the image and
    rectify it onto a square canvas.  This demonstration is only
    intended for illustrative purposes and lacks many features of the
    full CoastSnap GUI (such as saving results, zooming, etc.).

    Parameters
    ----------
    image_path : str or pathlib.Path
        Path to the image file.
    """
    import tkinter as tk
    from PIL import ImageTk

    img_pil = Image.open(image_path)
    w, h = img_pil.size
    # Convert to Tkinter image
    img_tk = ImageTk.PhotoImage(img_pil)

    root = tk.Tk()
    root.title("Rectify Image")
    canvas = tk.Canvas(root, width=w, height=h)
    canvas.pack()
    canvas.create_image(0, 0, anchor=tk.NW, image=img_tk)
    points: list[Tuple[float, float]] = []

    def on_click(event: tk.Event) -> None:
        if len(points) < 4:
            points.append((event.x, event.y))
            canvas.create_oval(event.x - 3, event.y - 3, event.x + 3, event.y + 3, fill="red")
            if len(points) == 4:
                # Define a simple rectangle for output points (1000×1000 px)
                dst = [(0.0, 0.0), (1000.0, 0.0), (1000.0, 1000.0), (0.0, 1000.0)]
                rect_img = rectify_image(image_path, points, dst, output_size=(1000, 1000))
                # Display rectified image in new window
                rect_pil = Image.fromarray(cv2.cvtColor(rect_img, cv2.COLOR_BGR2RGB))
                rect_tk = ImageTk.PhotoImage(rect_pil)
                rect_window = tk.Toplevel(root)
                rect_window.title("Rectified Image")
                rect_canvas = tk.Canvas(rect_window, width=1000, height=1000)
                rect_canvas.pack()
                rect_canvas.create_image(0, 0, anchor=tk.NW, image=rect_tk)
                # Keep reference to avoid garbage collection
                rect_canvas.rect_image = rect_tk

    canvas.bind("<Button-1>", on_click)
    root.mainloop()


__all__ = ["rectify_image", "run_gui"]