"""Create a video of shoreline evolution.

In the MATLAB toolbox, ``CSPGmakeVideoOfShoreline`` assembles a
sequence of rectified images and overlays the mapped shoreline on
each frame to create a video.  This Python implementation uses
``opencv-python`` to write an MP4 file.  The user must provide a
list of images and a corresponding list of shoreline coordinate
series.  Optionally, a homography matrix can be supplied to
transform shoreline coordinates from metric space to pixel space.
"""

from __future__ import annotations

from typing import Iterable, Tuple, Optional
import cv2  # type: ignore
import numpy as np

from ..rectify_code.m2P import metric_to_pixel


def run(
    image_files: Iterable[str],
    shoreline_series: Iterable[Iterable[Tuple[float, float]]],
    output_video: str,
    fps: float = 5.0,
    homography: Optional[np.ndarray] = None,
    color: Tuple[int, int, int] = (0, 0, 255),
    thickness: int = 2,
) -> None:
    """Create a video showing shoreline evolution.

    Parameters
    ----------
    image_files : iterable of str
        Paths to rectified images.  All images must have the same
        dimensions and correspond to successive shoreline surveys.
    shoreline_series : iterable of iterable of (float, float)
        A list of shoreline point lists.  Each element in
        ``shoreline_series`` corresponds to the shoreline to overlay on
        the image at the same index in ``image_files``.  The points
        should be given in metric coordinates if a homography is
        provided, otherwise they are interpreted as pixel coordinates.
    output_video : str
        Destination path for the output video file.  The container
        format is determined by the file extension (e.g., ``.mp4``).
    fps : float, optional
        Frames per second for the output video.  Default is 5.0.
    homography : numpy.ndarray, optional
        3×3 matrix mapping image coordinates to metric coordinates.
        If provided, shoreline points will be converted from metric
        coordinates to pixel coordinates using the inverse homography.
    color : tuple of int, optional
        BGR colour of the shoreline overlay.  Default is red.
    thickness : int, optional
        Line thickness of the shoreline overlay.  Default is 2.
    """
    # Convert image_files and shoreline_series to lists to allow indexing
    images = list(image_files)
    shorelines = list(shoreline_series)
    if len(images) != len(shorelines):
        raise ValueError("image_files and shoreline_series must have the same length")
    if not images:
        raise ValueError("No images provided for video creation")
    # Determine frame size from the first image
    first_img = cv2.imread(images[0])
    if first_img is None:
        raise FileNotFoundError(f"Unable to load image {images[0]}")
    height, width = first_img.shape[:2]
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(output_video, fourcc, fps, (width, height))
    # Precompute inverse homography if provided
    if homography is not None:
        inv_H = np.linalg.inv(homography)
    else:
        inv_H = None
    for img_path, shore_pts in zip(images, shorelines):
        frame = cv2.imread(img_path)
        if frame is None:
            continue
        if shore_pts:
            pts = []
            for pt in shore_pts:
                x, y = pt
                if inv_H is not None:
                    # Convert metric to pixel using inverse homography
                    px, py = metric_to_pixel(x, y, homography)  # type: ignore[arg-type]
                else:
                    px, py = x, y
                pts.append((int(px), int(py)))
            # Draw polyline on frame
            pts_arr = np.array([pts], dtype=np.int32)
            cv2.polylines(frame, pts_arr, isClosed=False, color=color, thickness=thickness)
        out.write(frame)
    out.release()


__all__ = ["run"]