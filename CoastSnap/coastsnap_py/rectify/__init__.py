"""Camera-model based rectification.

This subpackage provides a CoastSnap-style rectification workflow:

1) Build camera intrinsics from image size + candidate FOV.
2) Estimate camera pose (R,t) from GCP 3D world coordinates and 2D pixel clicks (PnP).
3) Project a regular metric grid (X,Y, Z_plane) into the image and resample to create a plan-view.

The intent is to mirror the MATLAB toolbox workflow (makeLCPP3 / findUVnDOF / CSPGrectifyImage).
"""

from .camera_model import build_camera_matrix_from_fov, solve_pnp_pose, optimise_fov_scalar
from .rectifier import rectify_oblique_to_plane

__all__ = [
    "build_camera_matrix_from_fov",
    "solve_pnp_pose",
    "optimise_fov_scalar",
    "rectify_oblique_to_plane",
]
