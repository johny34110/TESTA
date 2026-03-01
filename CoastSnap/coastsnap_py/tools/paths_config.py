"""
User‑defined path configuration for CoastSnap.

This file overrides the default paths defined in ``paths.py``.  You can
edit the ``PATHS`` dictionary below to point to the base directory
containing your CoastSnap data (Images, Database, Tide Data, etc.).
Only keys present in ``PATHS`` will be used; all other paths will
inherit their default locations relative to the base path.

The example values here assume your CoastSnap installation is located at
``C:/Users/johnn/Desktop/CoastSnap_Starter_Kit_v3/CoastSnap``.  Adjust
these paths if your setup differs.
"""

# Define a dictionary of paths.  Each entry may be absolute or relative.
PATHS = {
    # Base directory where CoastSnap data folders are located.
    "base_path": r"C:/Users/johnn/Desktop/CoastSnap_Starter_Kit_v3/CoastSnap",
    # Path to the database file (relative to base_path)
    "DB_path": r"Database/CoastSnapDB.xlsx",
    # Path to the folder containing CoastSnap images
    "image_path": r"Images",
    # Path to the folder containing tide data files
    "tide_path": r"Tide Data",
    # Path to the folder containing shoreline data
    "shoreline_path": r"Shorelines",
    # Path to the folder containing transect files
    "transect_dir": r"Shorelines/Transect Files",
}