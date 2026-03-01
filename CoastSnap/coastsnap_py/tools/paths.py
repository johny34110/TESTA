"""Path configuration management for CoastSnap.

The original MATLAB toolbox stores user‑specific path settings in
``CSPloadPaths.m``.  In the Python version we store these
settings in a JSON file named ``paths.json`` located in the
package directory or a user‑specified location.  This module
provides functions to load this configuration and fall back to
reasonable defaults if the file is missing.

The JSON file should define the following keys:

- ``base_path``: the base directory containing CoastSnap data
  (Images, Database, Shorelines, etc.)
- ``DB_path``: path to the CoastSnap database (.xlsx) file
- ``image_path``: path where images are stored
- ``shoreline_path``: path where shoreline data are stored
- ``tide_path``: path where tide data are stored
- ``transect_dir``: path where transect files are stored

If any of these values are omitted the loader will attempt to
construct them relative to ``base_path``.
"""

from __future__ import annotations

import json
import os
from typing import Dict

DEFAULT_CONFIG = {
    "base_path": ".",
    "DB_path": "./Database",
    "image_path": "./Images",
    "shoreline_path": "./Shorelines",
    "tide_path": "./Tide Data",
    "transect_dir": "./Shorelines/Transect Files",
}

# Attempt to load a user‑defined path configuration module.  If the
# user creates a file named ``paths_config.py`` in the same folder as
# this module and defines a dictionary ``PATHS`` within it, those
# values will override the defaults below.  This allows
# configuration without using JSON and provides a simple way to set
# the base path on a per‑installation basis.  Example usage:
#
#     # coastsnap_py/tools/paths_config.py
#     PATHS = {
#         "base_path": "C:/Users/username/CoastSnap",
#         "DB_path": "Database/CoastSnapDB.xlsx",
#         "image_path": "Images",
#         "tide_path": "Tide Data",
#         "transect_dir": "Shorelines/Transect Files",
#     }
#
# Only keys present in ``PATHS`` will be overridden; others fall back
# to their defaults or JSON values.
try:
    from .paths_config import PATHS as _USER_PATHS  # type: ignore
    if isinstance(_USER_PATHS, dict):
        DEFAULT_CONFIG.update(_USER_PATHS)
except Exception:
    # No user‑provided configuration; ignore import errors
    _USER_PATHS = None


def load_paths(config_file: str | None = None) -> Dict[str, str]:
    """Load CoastSnap path configuration from a JSON file.

    If ``config_file`` is ``None`` the function looks for
    ``paths.json`` in the same directory as this module.  If the
    file is missing or cannot be decoded, :data:`DEFAULT_CONFIG`
    is returned instead.

    Parameters
    ----------
    config_file : str or None
        Optional path to a JSON configuration file.  If provided,
        this file takes precedence over the default location.

    Returns
    -------
    dict
        Mapping of path names to strings.
    """
    if config_file is None:
        module_dir = os.path.dirname(__file__)
        config_file = os.path.join(module_dir, "paths.json")
    if os.path.isfile(config_file):
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            cfg = {}
    else:
        cfg = {}
    # Merge with defaults
    merged = DEFAULT_CONFIG.copy()
    merged.update(cfg)
    # Expand relative paths relative to base_path
    base = os.path.abspath(merged.get("base_path", "."))
    for key in ("DB_path", "image_path", "shoreline_path", "tide_path", "transect_dir"):
        value = merged.get(key)
        if value and not os.path.isabs(value):
            merged[key] = os.path.abspath(os.path.join(base, value))
    merged["base_path"] = base
    return merged


__all__ = ["load_paths"]