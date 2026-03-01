"""Bulk shoreline mapping module.

This module corresponds to the MATLAB ``CSPGbulkShorelineMapper.m``
file.  In the original toolbox it processes images to map
shorelines in bulk.  The functionality has not yet been ported to
Python and the ``bulk_shoreline_mapper`` function currently
raises :class:`NotImplementedError`.
"""

from __future__ import annotations


def bulk_shoreline_mapper(site: str) -> None:
    """Placeholder for the bulk shoreline mapping routine."""
    raise NotImplementedError("CSPGbulkShorelineMapper functionality not implemented.")


__all__ = ["bulk_shoreline_mapper"]