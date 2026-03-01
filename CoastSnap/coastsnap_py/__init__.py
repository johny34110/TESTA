"""Python implementation of the CoastSnap toolbox.

This package mirrors the structure of the original MATLAB
CoastSnap-Toolbox.  It provides modules for the graphical
user interface (GUI), image rectification, and assorted
utility functions for handling CoastSnap data.  Only a
subset of the original functionality has been implemented
so far; missing functions are included as stubs so that the
package structure matches the original repository and can
be extended incrementally.

The core GUI can be started via

```bash
python -m coastsnap_py.gui.CSP
```

or by importing the `CSP` class from `coastsnap_py.gui` and
embedding it in your own application.
"""

__all__ = ["gui", "rectify_code", "tools"]

# Make the day timex generator available at the top level for convenience.
try:
    from .CSPmakeDayTimex import make_day_timex  # noqa: F401
    __all__.append("make_day_timex")
except Exception:
    # If the module fails to import, silently ignore.  This can happen if
    # optional dependencies are missing at runtime.
    pass