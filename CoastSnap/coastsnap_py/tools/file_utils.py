"""File‑handling utilities for the CoastSnap toolbox.

This module implements Python equivalents of several
MATLAB helper functions that operate on CoastSnap
filenames and directories.  The functions provided here
are designed to be general enough to be reused by both the
GUI and headless scripts.
"""

from __future__ import annotations

import os
from typing import Iterable, List, Tuple, Dict

from .paths import load_paths


def parse_filename(fname: str) -> Dict[str, str]:
    """Parse a CoastSnap image filename into its constituent parts.

    The MATLAB function ``CSPparseFilename.m`` splits a filename on
    periods and returns a structure containing the epoch time,
    dayname, year, month, day, hour, minute, second, timezone, site,
    type, user and format.  This Python implementation performs
    the same split and returns a dictionary with equivalent keys.

    Parameters
    ----------
    fname : str
        Name of the file to parse (e.g. '1521515037.Mon.May.01.050000.GMT.site.Registered.user.jpg').

    Returns
    -------
    dict
        Mapping of component names to strings.
    """
    parts = fname.split('.')
    out = {
        'epochtime': parts[0] if len(parts) > 0 else '',
        'dayname': parts[1] if len(parts) > 1 else '',
        'year': parts[5] if len(parts) > 5 else '',
        'month': parts[2] if len(parts) > 2 else '',
        'day': parts[3][0:2] if len(parts) > 3 and len(parts[3]) >= 2 else '',
        'hour': parts[3][3:5] if len(parts) > 3 and len(parts[3]) >= 5 else '',
        'min': parts[3][6:8] if len(parts) > 3 and len(parts[3]) >= 8 else '',
        'sec': parts[3][9:11] if len(parts) > 3 and len(parts[3]) >= 11 else '',
        'timezone': parts[4] if len(parts) > 4 else '',
        'site': parts[6] if len(parts) > 6 else '',
        'type': parts[7] if len(parts) > 7 else '',
        'user': parts[8] if len(parts) > 8 else '',
        'format': parts[9] if len(parts) > 9 else '',
    }
    return out


def get_image_list(site: str, image_type: str) -> Tuple[List[int], List[str], List[str], List[float]]:
    """Generate a list of images and associated metadata for a site.

    This function mirrors the behaviour of ``CSPgetImageList.m``:
    it traverses the directory tree at ``image_path/site/image_type``
    and extracts epoch times from filenames.  Tide levels are not
    computed in this implementation; the returned list is filled with
    ``float('nan')`` values to preserve the interface.

    Parameters
    ----------
    site : str
        Name of the CoastSnap site (e.g. 'byron').
    image_type : str
        Subdirectory type ('Processed', 'Registered' or 'Rectified').

    Returns
    -------
    tuple
        A 4‑tuple ``(epochtimes, filenames, filepaths, tide_levels)`` where
        ``epochtimes`` is a list of integers representing UNIX epoch
        times in seconds, ``filenames`` is a list of image
        filenames, ``filepaths`` is a list of their parent
        directories, and ``tide_levels`` is a list of dummy values.
    """
    paths_cfg = load_paths()
    image_path = paths_cfg.get('image_path', '')
    search_root = os.path.join(image_path, site, image_type)
    epochtimes: List[int] = []
    filenames: List[str] = []
    filepaths: List[str] = []
    tide_levels: List[float] = []
    if not os.path.isdir(search_root):
        return epochtimes, filenames, filepaths, tide_levels
    # Iterate over subdirectories; directories with 4‑digit names are interpreted as years
    for folder_name in os.listdir(search_root):
        folder_path = os.path.join(search_root, folder_name)
        if os.path.isdir(folder_path) and len(folder_name) == 4 and folder_name.isdigit():
            for fname in os.listdir(folder_path):
                if fname.lower().endswith(('.jpg', '.jpeg', '.png', '.tif', '.tiff', '.bmp')):
                    parsed = parse_filename(fname)
                    try:
                        epochtime = int(parsed.get('epochtime', '0'))
                    except ValueError:
                        epochtime = 0
                    epochtimes.append(epochtime)
                    filenames.append(fname)
                    filepaths.append(folder_path)
                    tide_levels.append(float('nan'))  # placeholder
    return epochtimes, filenames, filepaths, tide_levels


__all__ = ["parse_filename", "get_image_list"]