"""CoastSnapDB reader (Excel) - MATLAB-like fixed layout.

This module is designed to mirror the assumptions made by the original
MATLAB CoastSnap toolbox: each site is represented by a worksheet in
``CoastSnapDB.xlsx`` with a fixed layout.

Key features
------------
- Robust parsing of numeric values that include decimal commas and units
  (e.g. ``"341761,07 m MGA94"``).
- Robust parsing of MATLAB-style GCP combos (e.g. ``"[1:7]"``,
  ``"[1 2 5:9]"``).
- Extraction of Ground Control Points (GCP name, Eastings, Northings,
  Elevation) in a way that tolerates merged cells and shifted columns.

The GUI should use this reader to ensure the same behaviour as MATLAB.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional, Tuple
import os
import re

import numpy as np

try:
    import pandas as pd  # type: ignore
except Exception as e:  # pragma: no cover
    pd = None
    _PANDAS_IMPORT_ERROR = e


_IGNORE_SHEETS = {
    "database",
    "tidal offset calculation",
    "insert_newsitename_here",
}


def _norm(x: Any) -> str:
    return str(x).strip() if x is not None else ""


_num_re = re.compile(r"[-+]?\d+(?:[.,]\d+)?")


def _parse_num(val: Any) -> Optional[float]:
    """Parse a float from values like '341761,07 m MGA94' or '0,4'."""
    if val is None:
        return None
    if isinstance(val, float) and np.isnan(val):
        return None
    s = _norm(val)
    if not s:
        return None
    m = _num_re.search(s)
    if not m:
        return None
    x = m.group(0).replace(",", ".")
    try:
        return float(x)
    except Exception:
        return None


def _parse_combo(combo: Any) -> List[int]:
    """Parse MATLAB combo strings like '[1:7]' into 0-based indices."""
    if combo is None:
        return []
    if isinstance(combo, float) and np.isnan(combo):
        return []
    s = _norm(combo).strip()
    if not s:
        return []
    s = s.strip("[]")
    s = s.replace(",", " ")
    parts = [p for p in s.split() if p.strip()]
    indices_1based: List[int] = []
    for part in parts:
        if ":" in part:
            a, b = part.split(":", 1)
            try:
                ia = int(a)
                ib = int(b)
            except Exception:
                continue
            step = 1 if ib >= ia else -1
            indices_1based.extend(list(range(ia, ib + step, step)))
        else:
            try:
                indices_1based.append(int(part))
            except Exception:
                continue
    seen = set()
    out: List[int] = []
    for i in indices_1based:
        if i not in seen:
            seen.add(i)
            out.append(i - 1)
    return out


def _find_label_cell(df: "pd.DataFrame", label: str) -> Optional[Tuple[int, int]]:
    """Find first cell equal to label (case-insensitive) in first columns."""
    target = label.strip().lower()
    for i in range(len(df)):
        for j in range(min(8, df.shape[1])):
            cell = df.iat[i, j]
            if isinstance(cell, str) and cell.strip().lower() == target:
                return i, j
    return None


def _cell_right_of(df: "pd.DataFrame", row: int, col: int) -> Any:
    """Return the first non-empty value to the right of (row, col)."""
    for k in range(col + 1, min(col + 10, df.shape[1])):
        v = df.iat[row, k]
        if v is None:
            continue
        if isinstance(v, float) and np.isnan(v):
            continue
        if _norm(v) != "":
            return v
    return None


def _find_label_value(df: "pd.DataFrame", label: str) -> Any:
    pos = _find_label_cell(df, label)
    if pos is None:
        return None
    r, c = pos
    return _cell_right_of(df, r, c)


def _find_rows(df: "pd.DataFrame", label: str) -> List[Tuple[int, int]]:
    """Return (row,col) positions where any cell equals label."""
    target = label.strip().lower()
    hits: List[Tuple[int, int]] = []
    for i in range(len(df)):
        for j in range(min(8, df.shape[1])):
            cell = df.iat[i, j]
            if isinstance(cell, str) and cell.strip().lower() == target:
                hits.append((i, j))
                break
    return hits


@dataclass
class GCP:
    name: str
    eastings: float
    northings: float
    elevation: float

    @property
    def xyz(self) -> Tuple[float, float, float]:
        return (self.eastings, self.northings, self.elevation)


class SiteDB:
    """One site sheet, with MATLAB-like properties."""

    def __init__(self, sitename: str, df: "pd.DataFrame"):
        self.sitename = sitename
        self.df = df
        self._gcps: Optional[List[GCP]] = None
        self._combo: Optional[List[int]] = None

    # --- Station origin ---
    @property
    def x0(self) -> Optional[float]:
        return _parse_num(_find_label_value(self.df, "Eastings"))

    @property
    def y0(self) -> Optional[float]:
        return _parse_num(_find_label_value(self.df, "Northings"))

    @property
    def z0(self) -> Optional[float]:
        return _parse_num(_find_label_value(self.df, "Elevation"))

    # --- Rectification settings ---
    @property
    def xlim(self) -> Optional[np.ndarray]:
        left = _parse_num(_find_label_value(self.df, "Xlimit left"))
        right = _parse_num(_find_label_value(self.df, "Xlimit right"))
        if left is None or right is None:
            return None
        return np.array([left, right], dtype=float)

    @property
    def ylim(self) -> Optional[np.ndarray]:
        low = _parse_num(_find_label_value(self.df, "Ylimit lower"))
        up = _parse_num(_find_label_value(self.df, "Ylimit upper"))
        if low is None or up is None:
            return None
        return np.array([low, up], dtype=float)

    @property
    def resolution(self) -> Optional[float]:
        return _parse_num(_find_label_value(self.df, "Resolution"))

    # --- Tide / transects ---
    @property
    def tide_file(self) -> str:
        return _norm(_find_label_value(self.df, "Tide file"))

    @property
    def transect_file(self) -> str:
        return _norm(_find_label_value(self.df, "Transect file"))

    # --- GCPs ---
    def _parse_gcps(self) -> List[GCP]:
        df = self.df
        hits = _find_rows(df, "GCP name")
        gcps: List[GCP] = []
        for (r, c) in hits:
            name = _cell_right_of(df, r, c)
            # For easting/northing/elevation we look in a small window below this GCP name row
            window = df.iloc[r : min(r + 6, len(df)), :].reset_index(drop=True)
            e = _parse_num(_find_label_value(window, "Eastings"))
            n = _parse_num(_find_label_value(window, "Northings"))
            z = _parse_num(_find_label_value(window, "Elevation"))
            name_s = _norm(name)
            if not name_s or e is None or n is None:
                continue
            if z is None:
                z = 0.0
            gcps.append(GCP(name=name_s, eastings=float(e), northings=float(n), elevation=float(z)))
        return gcps

    @property
    def gcps(self) -> List[GCP]:
        if self._gcps is None:
            self._gcps = self._parse_gcps()
        return self._gcps

    @property
    def gcp_combo(self) -> List[int]:
        if self._combo is None:
            self._combo = _parse_combo(_find_label_value(self.df, "GCP combo"))
        return self._combo

    @property
    def gcps_active(self) -> List[GCP]:
        combo = self.gcp_combo
        all_gcps = self.gcps
        if not combo:
            return all_gcps
        out: List[GCP] = []
        for idx in combo:
            if 0 <= idx < len(all_gcps):
                out.append(all_gcps[idx])
        return out

    @property
    def gcps_names_active(self) -> List[str]:
        return [g.name for g in self.gcps_active]


class CoastSnapDB:
    """Excel workbook wrapper."""

    def __init__(self, xlsx_path: str):
        if pd is None:
            raise ImportError(
                "pandas is required to read CoastSnapDB.xlsx. "
                "Install: python -m pip install pandas openpyxl"
            ) from _PANDAS_IMPORT_ERROR
        if not os.path.isfile(xlsx_path):
            raise FileNotFoundError(xlsx_path)
        self.xlsx_path = xlsx_path
        self._xls = pd.ExcelFile(xlsx_path)
        self.all_sites = [
            s for s in self._xls.sheet_names if s.strip().lower() not in _IGNORE_SHEETS
        ]

    def site(self, sitename: str) -> SiteDB:
        sn = sitename.strip().lower()
        match = None
        for s in self.all_sites:
            if s.strip().lower() == sn:
                match = s
                break
        if match is None:
            raise KeyError(
                f"Site '{sitename}' not found in DB. Available: {self.all_sites}"
            )
        df = self._xls.parse(match, header=None)
        return SiteDB(match, df)


__all__ = ["CoastSnapDB", "SiteDB", "GCP"]
