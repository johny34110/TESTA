"""CSP GUI implementation in Python.

This module defines a Tkinter‑based GUI that mirrors the
functionality of the MATLAB `CSP.m` script.  It allows users
to load oblique beach photographs, select ground control
points (GCPs) for rectification, warp the image to plan
view, digitise shoreline points, and save the resulting
shoreline coordinates.  Additional GUI functions present in
the original toolbox are represented by stub functions and
modules whose names begin with `CSPG`; these can be
implemented incrementally to extend the capabilities of the
application.
"""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import numpy as np
import cv2
import traceback

# Import tools from our package
from ..tools import file_utils, paths, transect_utils, tide_utils
from ..tools.read_db import CoastSnapDB
from typing import List, Tuple


class CoastSnapGUI:
    """Tkinter application for CoastSnap image rectification and shoreline mapping."""

    def __init__(self, master: tk.Tk) -> None:
        self.master = master
        self.master.title("CoastSnap Python GUI")
        self.master.geometry("1000x500")

        # Create frames for controls and canvases
        control_frame = tk.Frame(master)
        control_frame.pack(side=tk.TOP, fill=tk.X)

        # --- Prominent GCP prompt (requested): shown above the images ---
        prompt_frame = tk.Frame(master)
        prompt_frame.pack(side=tk.TOP, fill=tk.X)
        self.gcp_prompt_var = tk.StringVar(value="")
        self.gcp_prompt_label = tk.Label(
            prompt_frame,
            textvariable=self.gcp_prompt_var,
            anchor="w",
            justify="left",
            font=("Segoe UI", 12, "bold"),
        )
        self.gcp_prompt_label.pack(side=tk.LEFT, padx=8, pady=(0, 4), fill=tk.X, expand=True)

        self.canvas_frame = tk.Frame(master)
        self.canvas_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Buttons
        load_btn = tk.Button(control_frame, text="Load Image", command=self.load_image)
        rect_btn = tk.Button(control_frame, text="Rectify Image", command=self.rectify_image)
        # Button to define a region of interest (ROI) on the rectified image
        roi_btn = tk.Button(control_frame, text="Set ROI", command=self.select_roi)
        # Button to load transect definitions from a CSV file
        transect_btn = tk.Button(control_frame, text="Load Transects", command=self.load_transects)
        # Auto‑detection button to compute shoreline automatically
        auto_btn = tk.Button(control_frame, text="Auto Detect", command=self.auto_detect_shoreline)
        map_btn = tk.Button(control_frame, text="Map Shoreline", command=self.map_shoreline)
        save_btn = tk.Button(control_frame, text="Save Shoreline", command=self.save_shoreline)
        reset_btn = tk.Button(control_frame, text="Reset", command=self.reset_session)
        # Pack buttons in order
        for btn in (load_btn, rect_btn, roi_btn, transect_btn, auto_btn, map_btn, save_btn, reset_btn):
            btn.pack(side=tk.LEFT, padx=5, pady=5)

        # Canvases for displaying images
        self.oblq_canvas = tk.Canvas(self.canvas_frame, bg="lightgray", width=500, height=400)
        self.plan_canvas = tk.Canvas(self.canvas_frame, bg="lightgray", width=500, height=400)
        self.oblq_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.plan_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Bind events for collecting points
        self.oblq_canvas.bind("<Button-1>", self._on_oblq_click)
        self.plan_canvas.bind("<Button-1>", self._on_plan_click)
        self.oblq_canvas.bind("<Motion>", self._on_oblq_motion)
        self.plan_canvas.bind("<Motion>", lambda e: setattr(self, "_last_hover", "plan"))
        # Bind drag events on the plan canvas for editing shoreline points
        self.plan_canvas.bind("<B1-Motion>", self._on_plan_motion)
        self.plan_canvas.bind("<ButtonRelease-1>", self._on_plan_release)
        # Mouse wheel zoom on the oblique image and spacebar to drop a GCP
        self.oblq_canvas.bind("<MouseWheel>", self._on_oblq_zoom)
        master.bind("<space>", self._on_space_press)

        # Internal state
        self.oblq_image: Image.Image | None = None  # PIL image (RGB)
        self.oblq_cv: np.ndarray | None = None      # OpenCV image (BGR)
        self.plan_image: Image.Image | None = None  # rectified image
        self.plan_cv: np.ndarray | None = None
        self.oblq_photo: ImageTk.PhotoImage | None = None
        self.plan_photo: ImageTk.PhotoImage | None = None
        self.oblq_display_size = (0, 0)
        self.plan_display_size = (0, 0)
        self.src_points: list[tuple[int, int]] = []
        self.shoreline_points: list[tuple[int, int]] = []
        self.rectified: bool = False

        # Flags controlling point collection
        self.collecting_gcp = False
        self.collecting_shoreline = False

        # Variables for editing shoreline points
        self.selected_point_index: int | None = None
        self.dragging: bool = False

        # Variables for region of interest (ROI) selection on rectified image
        # ROI is stored as (x0, y0, x1, y1) in pixel coordinates of plan_cv
        self.roi: tuple[int, int, int, int] | None = None
        self.selecting_roi: bool = False
        self._roi_start: tuple[int, int] | None = None
        self._roi_rect_id: int | None = None

        # Zoom/pan state for the oblique canvas
        self.oblq_zoom: float = 1.0
        self.oblq_pan: list[float] = [0.0, 0.0]  # [x, y] offsets in canvas pixels
        self.oblq_base_size: tuple[int, int] = (0, 0)
        self._last_mouse_pos: tuple[int, int] | None = None
        self._last_hover: str | None = None

        # Homography matrix computed during rectification (3x3).  None until image is rectified.
        self.homography: np.ndarray | None = None

        # Store loaded transects; each transect is a tuple ((x0, y0), (x1, y1)) in pixel coordinates
        self.transects: list[tuple[tuple[float, float], tuple[float, float]]] | None = None

        # Load path configuration from package if available
        db_err = None
        try:
            self.config = paths.load_paths()
        except Exception:
            self.config = {}

        # Site database loaded from JSON or Excel.  Will be populated
        # automatically based on the db_path in the configuration or
        # packaged resources.  Populated in the block below.
        self.site_database: dict = {}
        # Will hold metadata for the site associated with the currently loaded image
        self.current_site_info: dict | None = None

        # Expected number of GCPs to collect based on site database (defaults to 4)
        self.expected_gcp_count: int = 4
        # Ordered list of ground control point metadata (from site database)
        self.gcp_world_points: list[dict] | None = None
        # Ordered list of GCP names for user instruction
        self.gcp_names_order: list[str] | None = None

        # Attempt to load site database based on configuration or packaged data
        try:
            db_path: str | None = None
            if self.config:
                # Accept both lower‑case and upper‑case keys for DB_path
                db_cfg = self.config.get('db_path') or self.config.get('DB_path')
                if db_cfg:
                    # If a directory is given, search for a JSON/XLS/XLSX file inside it
                    if os.path.isdir(db_cfg):
                        for fname in os.listdir(db_cfg):
                            low = fname.lower()
                            if low.endswith('.json') or low.endswith('.xls') or low.endswith('.xlsx'):
                                db_path = os.path.join(db_cfg, fname)
                                break
                    # If a file is given directly, use it
                    elif os.path.isfile(db_cfg):
                        db_path = db_cfg
                    # If it is a relative path, combine with base_path
                    else:
                        # Interpret relative path with respect to base_path
                        base = self.config.get('base_path') or os.getcwd()
                        candidate = os.path.join(base, db_cfg)
                        if os.path.isfile(candidate):
                            db_path = candidate
            # If still not found, attempt common locations relative to base_path
            if db_path is None and self.config:
                base = self.config.get('base_path') or os.getcwd()
                possible_dirs = [self.config.get('DB_path'), os.path.join(base, 'Database'), base]
                for directory in possible_dirs:
                    if directory and os.path.isdir(directory):
                        for fname in os.listdir(directory):
                            low = fname.lower()
                            if low.endswith('.json') or low.endswith('.xls') or low.endswith('.xlsx'):
                                db_path = os.path.join(directory, fname)
                                break
                        if db_path:
                            break
            # Final fallback: look in package data folder
            if db_path is None:
                module_dir = os.path.dirname(__file__)
                pkg_root = os.path.abspath(os.path.join(module_dir, os.pardir, os.pardir))
                for fname in ["site_db.json", "site_db.xlsx", "CoastSnapDB.xlsx"]:
                    candidate = os.path.join(pkg_root, "data", fname)
                    if os.path.isfile(candidate):
                        db_path = candidate
                        break
            if db_path:
                # MATLAB-like DB reader (fixed Excel layout)
                db = CoastSnapDB(db_path)
                self._db_reader = db
                # Build a lightweight dict compatible with the rest of the GUI
                self.site_database = {}
                for s in db.all_sites:
                    try:
                        site_obj = db.site(s)
                        gcps = site_obj.gcps
                        gcp_combo0 = site_obj.gcp_combo  # 0-based
                        # Convert to 1-based for UI legacy code
                        gcp_combo1 = [i + 1 for i in gcp_combo0] if gcp_combo0 else []
                        self.site_database[s.strip().lower()] = {
                            "Tide file": site_obj.tide_file,
                            "Transect file": site_obj.transect_file,
                            "gcp_combo": gcp_combo1,
                            "gcp_world": [
                                {
                                    "name": g.name,
                                    "easting": g.eastings,
                                    "northing": g.northings,
                                    "elevation": g.elevation,
                                }
                                for g in gcps
                            ],
                        }
                    except Exception:
                        continue
        except Exception as e:
            # Leave database empty on any error, but keep the error for display
            db_err = e
            self.site_database = {}

        # --- Production guardrails: refuse to run with a bad DB ---
        if not self.site_database:
            extra = f"\n\nDetails: {type(db_err).__name__}: {db_err}" if db_err else ""
            messagebox.showerror(
                "Database error",
                "Unable to load CoastSnapDB (no sites parsed).\n"
                "Check your CoastSnapDB.xlsx path and Excel readability."
                "\n\nTip: install 'pandas' (recommended) or 'openpyxl' to read .xlsx files."
                + extra
            )
            self.master.after(0, self.master.destroy)
            return
        has_any_gcps = any(
            isinstance(v, dict) and v.get("gcp_world") for v in self.site_database.values()
        )
        if not has_any_gcps:
            messagebox.showerror(
                "Database error",
                "CoastSnapDB loaded but no GCPs were found in any site sheet.\n"
                "This strongly suggests the Excel parser failed (units/merged cells)."
            )
            self.master.after(0, self.master.destroy)
            return

        # Label to display site name and tide information
        self.info_var = tk.StringVar(value="")
        self.info_label = tk.Label(control_frame, textvariable=self.info_var, fg="darkblue")
        self.info_label.pack(side=tk.LEFT, padx=5)

        # Debug panel (requested): show site, GCP count, combo
        self.debug_site_var = tk.StringVar(value="Site: -")
        self.debug_gcp_count_var = tk.StringVar(value="GCP count: -")
        self.debug_combo_var = tk.StringVar(value="Combo: -")

        dbg = tk.LabelFrame(control_frame, text="Debug", padx=6, pady=4)
        dbg.pack(side=tk.LEFT, padx=10)
        tk.Label(dbg, textvariable=self.debug_site_var, anchor="w", justify="left").pack(fill="x")
        tk.Label(dbg, textvariable=self.debug_gcp_count_var, anchor="w", justify="left").pack(fill="x")
        tk.Label(dbg, textvariable=self.debug_combo_var, anchor="w", justify="left").pack(fill="x")

        # Base portion of the info text (excluding any "Next GCP" indicator).
        # This will be set each time an image is loaded and reused while
        # collecting GCP clicks.  It allows us to append instructions
        # without permanently altering the original information.
        self.base_info: str = ""

        # Default to using nearest tide level (True) vs interpolated (False)
        # This can be toggled if future GUI enhancements allow user preference.
        self.use_nearest_tide: bool = True

        # Calibration results (FOV and reprojection error)
        self.calib_fov: float | None = None
        self.calib_error: float | None = None

        # Store world limits, resolution, and output size after rectification
        # These allow conversion from rectified image pixel coordinates to
        # real world Easting/Northing coordinates.
        self.rect_world_limits: tuple[float, float, float, float] | None = None
        self.rect_resolution: float | None = None
        self.rect_out_size: tuple[int, int] | None = None

    # ------------------------------------------------------------------
    # GUI update methods
    def display_oblique(self) -> None:
        """Render the oblique image on the left canvas."""
        if self.oblq_image is None:
            self.oblq_canvas.delete("all")
            return
        canvas_w, canvas_h, base_w, base_h, disp_w, disp_h = self._compute_oblq_sizes()
        self.oblq_base_size = (base_w, base_h)
        resample = Image.Resampling.LANCZOS if hasattr(Image, "Resampling") else (Image.LANCZOS if hasattr(Image, "LANCZOS") else Image.NEAREST)
        img = self.oblq_image.resize((disp_w, disp_h), resample)
        self.oblq_display_size = (disp_w, disp_h)
        # Clamp pan so the image does not slide fully out of view
        max_dx = max(0.0, (disp_w - canvas_w) / 2.0)
        max_dy = max(0.0, (disp_h - canvas_h) / 2.0)
        pan_x = min(max(self.oblq_pan[0], -max_dx), max_dx)
        pan_y = min(max(self.oblq_pan[1], -max_dy), max_dy)
        self.oblq_pan = [pan_x, pan_y]
        self.oblq_photo = ImageTk.PhotoImage(img)
        self.oblq_canvas.delete("all")
        self.oblq_canvas.create_image(
            canvas_w // 2 + int(pan_x),
            canvas_h // 2 + int(pan_y),
            image=self.oblq_photo,
            anchor=tk.CENTER,
        )
        # Draw any existing GCP markers
        for pt in self.src_points:
            self._draw_circle(self.oblq_canvas, pt[0], pt[1], radius=4, color="red", display_scale=True, is_plan=False)

    def _update_next_gcp_info(self) -> None:
        """
        Update the information label to indicate which ground control point
        should be selected next.  Uses `self.base_info` as the base text and
        appends a "Next GCP" instruction if appropriate.
        """
        # If there is no list of GCP names, clear the prompt and do nothing
        if not self.gcp_names_order or self.expected_gcp_count <= 0:
            self.gcp_prompt_var.set("")
            return
        # Determine how many points have been clicked so far
        clicked = len(self.src_points)
        # If we still need to collect points, display the next name
        if clicked < self.expected_gcp_count:
            try:
                next_name = self.gcp_names_order[clicked]
            except IndexError:
                next_name = None
            # Construct new info string
            info_str = self.base_info
            if next_name:
                info_str = info_str + f" | Next GCP: {next_name}"
            self.info_var.set(info_str)

            # Prominent prompt above the images
            if next_name:
                self.gcp_prompt_var.set(
                    f"Click GCP {clicked + 1}/{self.expected_gcp_count}: {next_name}"
                )
            else:
                self.gcp_prompt_var.set(f"Click GCP {clicked + 1}/{self.expected_gcp_count}")
        else:
            # All points collected; restore base info
            self.info_var.set(self.base_info)

            # Clear prominent prompt
            self.gcp_prompt_var.set("")

    def display_plan(self) -> None:
        """Render the rectified image on the right canvas."""
        if self.plan_image is None:
            self.plan_canvas.delete("all")
            return
        canvas_w = int(self.plan_canvas.winfo_width()) or 500
        canvas_h = int(self.plan_canvas.winfo_height()) or 400
        img = self.plan_image.copy()
        if hasattr(Image, "Resampling"):
            resample = Image.Resampling.LANCZOS
        else:
            resample = Image.LANCZOS if hasattr(Image, "LANCZOS") else Image.NEAREST
        img.thumbnail((canvas_w, canvas_h), resample)
        self.plan_display_size = img.size
        self.plan_photo = ImageTk.PhotoImage(img)
        self.plan_canvas.delete("all")
        self.plan_canvas.create_image(canvas_w // 2, canvas_h // 2, image=self.plan_photo, anchor=tk.CENTER)
        # Draw shoreline points and connecting lines
        # Draw circles first
        for pt in self.shoreline_points:
            self._draw_circle(self.plan_canvas, pt[0], pt[1], radius=3, color="blue", display_scale=True, is_plan=True)
        # Draw lines connecting consecutive points
        if len(self.shoreline_points) > 1:
            # Convert image coordinates to canvas coordinates for each point
            coords = []
            disp_w, disp_h = self.plan_display_size
            if self.plan_cv is not None:
                orig_h, orig_w, _ = self.plan_cv.shape
                canvas_w = int(self.plan_canvas.winfo_width()) or disp_w
                canvas_h = int(self.plan_canvas.winfo_height()) or disp_h
                x0 = (canvas_w - disp_w) / 2
                y0 = (canvas_h - disp_h) / 2
                for (img_x, img_y) in self.shoreline_points:
                    x_rel = img_x / orig_w
                    y_rel = img_y / orig_h
                    canvas_x = x0 + x_rel * disp_w
                    canvas_y = y0 + y_rel * disp_h
                    coords.append((canvas_x, canvas_y))
                # Draw lines between consecutive points
                for i in range(len(coords) - 1):
                    x1, y1 = coords[i]
                    x2, y2 = coords[i + 1]
                    self.plan_canvas.create_line(x1, y1, x2, y2, fill="blue", width=2)

        # Draw region of interest rectangle if defined
        if self.roi is not None and self.plan_cv is not None:
            disp_w, disp_h = self.plan_display_size
            orig_h, orig_w, _ = self.plan_cv.shape
            canvas_w = int(self.plan_canvas.winfo_width()) or disp_w
            canvas_h = int(self.plan_canvas.winfo_height()) or disp_h
            x0_canvas = (canvas_w - disp_w) / 2
            y0_canvas = (canvas_h - disp_h) / 2
            x_min, y_min, x_max, y_max = self.roi
            cx0 = x0_canvas + (x_min / orig_w) * disp_w
            cy0 = y0_canvas + (y_min / orig_h) * disp_h
            cx1 = x0_canvas + (x_max / orig_w) * disp_w
            cy1 = y0_canvas + (y_max / orig_h) * disp_h
            # Draw rectangle border; use dashed line to distinguish
            self.plan_canvas.create_rectangle(cx0, cy0, cx1, cy1, outline="green", width=2, dash=(4, 4))

        # Draw transects if loaded
        if self.transects is not None and self.plan_cv is not None:
            # Convert transect endpoints from image space to canvas coordinates
            disp_w, disp_h = self.plan_display_size
            orig_h, orig_w, _ = self.plan_cv.shape
            canvas_w = int(self.plan_canvas.winfo_width()) or disp_w
            canvas_h = int(self.plan_canvas.winfo_height()) or disp_h
            x0_canvas = (canvas_w - disp_w) / 2
            y0_canvas = (canvas_h - disp_h) / 2
            for (p0, p1) in self.transects:
                (x0_t, y0_t) = p0
                (x1_t, y1_t) = p1
                cx0_t = x0_canvas + (x0_t / orig_w) * disp_w
                cy0_t = y0_canvas + (y0_t / orig_h) * disp_h
                cx1_t = x0_canvas + (x1_t / orig_w) * disp_w
                cy1_t = y0_canvas + (y1_t / orig_h) * disp_h
                self.plan_canvas.create_line(cx0_t, cy0_t, cx1_t, cy1_t, fill="magenta", width=2, dash=(4, 2))

    # ------------------------------------------------------------------
    # Oblique canvas helpers (zoom, pan, coordinate transforms)
    def _compute_oblq_sizes(self) -> tuple[int, int, int, int, int, int]:
        """Return canvas dims, fitted base size, and zoomed display size."""
        canvas_w = int(self.oblq_canvas.winfo_width()) or 500
        canvas_h = int(self.oblq_canvas.winfo_height()) or 400
        if self.oblq_image is None:
            return canvas_w, canvas_h, 1, 1, 1, 1
        orig_w, orig_h = self.oblq_image.size
        scale = min(canvas_w / max(orig_w, 1), canvas_h / max(orig_h, 1))
        if scale <= 0:
            scale = 1.0
        base_w = max(1, int(orig_w * scale))
        base_h = max(1, int(orig_h * scale))
        disp_w = max(1, int(base_w * self.oblq_zoom))
        disp_h = max(1, int(base_h * self.oblq_zoom))
        return canvas_w, canvas_h, base_w, base_h, disp_w, disp_h

    def _canvas_to_image_oblq(self, canvas_x: float, canvas_y: float, clamp: bool = True) -> Tuple[int, int] | None:
        """Map canvas coords to original image pixel coords on the oblique canvas."""
        if self.oblq_image is None:
            return None
        canvas_w, canvas_h, _, _, disp_w, disp_h = self._compute_oblq_sizes()
        pan_x, pan_y = self.oblq_pan
        x0 = (canvas_w - disp_w) / 2 + pan_x
        y0 = (canvas_h - disp_h) / 2 + pan_y
        x_rel = (canvas_x - x0) / disp_w
        y_rel = (canvas_y - y0) / disp_h
        if clamp:
            x_rel = min(max(x_rel, 0.0), 1.0)
            y_rel = min(max(y_rel, 0.0), 1.0)
        elif x_rel < 0.0 or x_rel > 1.0 or y_rel < 0.0 or y_rel > 1.0:
            return None
        orig_w, orig_h = self.oblq_image.size
        img_x = int(x_rel * orig_w)
        img_y = int(y_rel * orig_h)
        return img_x, img_y

    def _image_to_canvas_oblq(self, img_x: float, img_y: float) -> Tuple[float, float] | None:
        """Map original image coords to canvas coords on the oblique canvas."""
        if self.oblq_image is None:
            return None
        canvas_w, canvas_h, _, _, disp_w, disp_h = self._compute_oblq_sizes()
        pan_x, pan_y = self.oblq_pan
        x0 = (canvas_w - disp_w) / 2 + pan_x
        y0 = (canvas_h - disp_h) / 2 + pan_y
        orig_w, orig_h = self.oblq_image.size
        canvas_x = x0 + (img_x / orig_w) * disp_w
        canvas_y = y0 + (img_y / orig_h) * disp_h
        return canvas_x, canvas_y

    def _recenter_on_image_point(self, img_x: float, img_y: float, canvas_x: float, canvas_y: float) -> None:
        """Adjust pan so that img point stays under the given canvas position after zoom."""
        if self.oblq_image is None:
            return
        canvas_w, canvas_h, _, _, disp_w, disp_h = self._compute_oblq_sizes()
        x0 = canvas_x - (img_x / self.oblq_image.size[0]) * disp_w
        y0 = canvas_y - (img_y / self.oblq_image.size[1]) * disp_h
        pan_x = x0 - (canvas_w - disp_w) / 2.0
        pan_y = y0 - (canvas_h - disp_h) / 2.0
        max_dx = max(0.0, (disp_w - canvas_w) / 2.0)
        max_dy = max(0.0, (disp_h - canvas_h) / 2.0)
        self.oblq_pan = [
            min(max(pan_x, -max_dx), max_dx),
            min(max(pan_y, -max_dy), max_dy),
        ]

    def _add_gcp_from_canvas(self, canvas_x: float, canvas_y: float) -> None:
        """Record a GCP using canvas coordinates (mouse click or spacebar)."""
        if self.oblq_image is None or self.oblq_cv is None:
            return
        coords = self._canvas_to_image_oblq(canvas_x, canvas_y, clamp=True)
        if coords is None:
            return
        img_x, img_y = coords
        self.src_points.append((img_x, img_y))
        # Draw the point where it actually lands after clamping
        canvas_pt = self._image_to_canvas_oblq(img_x, img_y)
        if canvas_pt is not None:
            self._draw_circle(self.oblq_canvas, canvas_pt[0], canvas_pt[1], radius=4, color="red", display_scale=False, is_plan=False)
        # After collecting a point, update the info label to show next GCP name
        self._update_next_gcp_info()
        # Proceed to rectification once we have at least 3 GCPs (MATLAB parity).
        if len(self.src_points) >= 3:
            self.collecting_gcp = False
            # Restore the base info (remove "Next GCP" label) prior to rectification
            self.info_var.set(self.base_info)
            self.compute_rectification()

    def _on_oblq_motion(self, event: tk.Event) -> None:
        """Track mouse position over the oblique canvas for spacebar placement."""
        self._last_mouse_pos = (event.x, event.y)
        self._last_hover = "oblq"

    def _on_space_press(self, event: tk.Event) -> None:
        """Allow placing a GCP with the spacebar at the current mouse position."""
        if not self.collecting_gcp:
            return
        if self._last_hover != "oblq":
            return
        canvas_w = int(self.oblq_canvas.winfo_width()) or 500
        canvas_h = int(self.oblq_canvas.winfo_height()) or 400
        cx, cy = self._last_mouse_pos if self._last_mouse_pos is not None else (canvas_w // 2, canvas_h // 2)
        self._add_gcp_from_canvas(cx, cy)

    def _on_oblq_zoom(self, event: tk.Event) -> None:
        """Zoom the oblique image with the mouse wheel, keeping the cursor position fixed."""
        if self.oblq_image is None:
            return
        self._last_hover = "oblq"
        self._last_mouse_pos = (event.x, event.y)
        # Determine zoom direction
        factor = 1.1 if event.delta > 0 else 0.9
        new_zoom = min(max(self.oblq_zoom * factor, 0.2), 8.0)
        if abs(new_zoom - self.oblq_zoom) < 1e-4:
            return
        # Compute image coordinates under the cursor before changing zoom
        img_coords = self._canvas_to_image_oblq(event.x, event.y, clamp=False)
        self.oblq_zoom = new_zoom
        if img_coords is not None:
            self._recenter_on_image_point(img_coords[0], img_coords[1], event.x, event.y)
        self.display_oblique()

    # ------------------------------------------------------------------
    # Button callbacks
    def load_image(self) -> None:
        """Prompt the user to select an image and load it."""
        filetypes = [
            ("Image files", "*.jpg;*.jpeg;*.png;*.tif;*.tiff;*.bmp"),
            ("All files", "*.*"),
        ]
        filepath = filedialog.askopenfilename(title="Select image file", filetypes=filetypes)
        if not filepath:
            return
        try:
            pil_img = Image.open(filepath).convert("RGB")
        except Exception as exc:
            messagebox.showerror("Error", f"Unable to load image: {exc}")
            return
        # Assign images
        self.oblq_image = pil_img
        self.oblq_cv = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        # Reset state but keep loaded image
        self.reset_session(clear_image=False)
        self.display_oblique()
        # Parse metadata from filename to infer site and time
        fname = os.path.basename(filepath)
        parsed = file_utils.parse_filename(fname)
        # Determine epoch time from filename
        epoch_str = parsed.get('epochtime', '')
        epoch_time: float | None = None
        try:
            if epoch_str:
                epoch_time = float(epoch_str)
        except Exception:
            epoch_time = None
        # Determine site identifier
        site_id = parsed.get('site', '')
        # If site id missing, attempt to infer from filename segments (e.g., underscores)
        if not site_id:
            # Attempt to find a site key that is contained in the filename
            lower_fname = fname.lower()
            for sid in self.site_database.keys():
                if str(sid).lower() in lower_fname:
                    site_id = sid
                    break
        # Look up site info
        site_info = None
        if site_id and site_id in self.site_database:
            site_info = self.site_database[site_id]
        # If no site info found, prompt the user to select a site
        if site_info is None and self.site_database:
            try:
                site_keys = list(self.site_database.keys())
                if len(site_keys) == 1:
                    # Only one site available; use it automatically
                    site_id = site_keys[0]
                    site_info = self.site_database[site_id]
                else:
                    # Ask user to choose a site identifier
                    from tkinter import simpledialog
                    choices = ", ".join(site_keys)
                    site_choice = simpledialog.askstring(
                        "Select Site",
                        f"Cannot determine site from filename. Available sites:\n{choices}\nPlease enter a site ID:",
                    )
                    if site_choice and site_choice in self.site_database:
                        site_id = site_choice
                        site_info = self.site_database[site_choice]
            except Exception:
                pass
        # Save current site info for later rectification
        self.current_site_info = site_info
        # Configure GCP expectations based on site database
        # If site info defines ground control points and a combo, set expected count accordingly
        self.gcp_world_points = None
        self.gcp_names_order = None
        if site_info and isinstance(site_info, dict):
            # Retrieve list of GCP definitions
            gcp_list = site_info.get('gcp_world')
            if gcp_list and isinstance(gcp_list, list):
                # Determine combo indices (1-based in DB) if provided
                combo = site_info.get('gcp_combo')
                # Build list of indices to use (0-based)
                indices: list[int]
                if isinstance(combo, list) and combo:
                    # Convert to 0-based indices
                    indices = [max(0, int(i) - 1) for i in combo if isinstance(i, int)]
                    # Filter indices within range
                    indices = [idx for idx in indices if 0 <= idx < len(gcp_list)]
                    if not indices:
                        indices = list(range(len(gcp_list)))
                else:
                    indices = list(range(len(gcp_list)))
                # Extract GCPs in order.  If a GCP combination is specified, use all
                # indices from that combination; otherwise use all available GCPs.  We
                # no longer limit to four points here because the camera calibration
                # can handle more points.  When only a homography is computed (no
                # calibration), the four first points will still be used implicitly.
                selected_indices = indices
                self.gcp_world_points = [gcp_list[idx] for idx in selected_indices]
                # Extract names for instructions
                self.gcp_names_order = [gcp['name'] for gcp in self.gcp_world_points if isinstance(gcp, dict)]
                # Set expected GCP count to the number of selected GCPs
                self.expected_gcp_count = len(self.gcp_world_points)
            else:
                # No GCPs defined for this site: disable rectification until DB is fixed
                self.expected_gcp_count = 0
        else:
            # No site info; disable rectification until a valid site is selected
            self.expected_gcp_count = 0

        # Update debug panel
        try:
            self.debug_site_var.set(f"Site: {site_id if site_id else '-'}")
            gcp_count = len(self.gcp_world_points) if self.gcp_world_points else 0
            self.debug_gcp_count_var.set(f"GCP count: {gcp_count}")
            combo = None
            if site_info and isinstance(site_info, dict):
                combo = site_info.get("gcp_combo")
            if isinstance(combo, list) and combo:
                self.debug_combo_var.set(f"Combo: {combo}")
            else:
                self.debug_combo_var.set("Combo: -")
        except Exception:
            pass
        # Attempt to compute tide level
        tide_level: float | None = None
        if epoch_time is not None:
            tide_file = None
            # First, try to use site-specific tide file from site_info
            if site_info and 'Tide file' in site_info:
                tide_file_name = str(site_info['Tide file'])
                # Combine with configured tide_path if set and file exists there
                if self.config:
                    tide_path_cfg = self.config.get('tide_path')
                    if tide_path_cfg:
                        if os.path.isdir(tide_path_cfg):
                            candidate = os.path.join(tide_path_cfg, tide_file_name)
                            if os.path.isfile(candidate):
                                tide_file = candidate
                        elif os.path.isfile(tide_path_cfg):
                            tide_file = tide_path_cfg
                # If not found, look in working directory
                if tide_file is None and os.path.isfile(tide_file_name):
                    tide_file = tide_file_name
            # Fall back to generic tide file search as before
            if tide_file is None and self.config:
                tide_path = self.config.get('tide_path')
                if tide_path and os.path.isdir(tide_path):
                    if site_id:
                        for f in os.listdir(tide_path):
                            if f.lower().startswith(site_id.lower()) and f.lower().endswith(('.csv', '.mat')):
                                tide_file = os.path.join(tide_path, f)
                                break
                    if tide_file is None:
                        for f in os.listdir(tide_path):
                            if f.lower().endswith(('.csv', '.mat')):
                                tide_file = os.path.join(tide_path, f)
                                break
                elif tide_path and os.path.isfile(tide_path):
                    tide_file = tide_path
            try:
                # Choose between nearest tide level or interpolated depending on flag
                if self.use_nearest_tide and hasattr(tide_utils, "get_nearest_tide_level"):
                    tide_val = tide_utils.get_nearest_tide_level(epoch_time, tide_file=tide_file)
                else:
                    tide_val = tide_utils.get_tide_level(epoch_time, tide_file=tide_file)
                # Apply tidal offset if defined for this site
                if tide_val is not None and site_info and 'Tidal offset' in site_info:
                    try:
                        offset = float(site_info['Tidal offset'])
                        tide_val += offset
                    except Exception:
                        pass
                tide_level = tide_val
            except Exception:
                tide_level = None

        # Persist tide for downstream rectification (MATLAB uses it as rectz input)
        self.tide_level = tide_level
        # Attempt to automatically load transects for the site
        auto_transects_loaded = False
        # Try using site-specific transect file from site_info first
        candidate_file = None
        if site_info and 'Transect file' in site_info:
            tran_fname = str(site_info['Transect file'])
            # Compose full path using configured directory
            if self.config:
                tran_dir = self.config.get('transect_dir')
                if tran_dir and os.path.isdir(tran_dir):
                    cf = os.path.join(tran_dir, tran_fname)
                    if os.path.isfile(cf):
                        candidate_file = cf
            # If not found, check current directory
            if candidate_file is None and os.path.isfile(tran_fname):
                candidate_file = tran_fname
        # Fallback: search by site_id as before
        if candidate_file is None and site_id:
            tran_dir = self.config.get('transect_dir') if self.config else None
            if tran_dir and os.path.isdir(tran_dir):
                for fname_t in os.listdir(tran_dir):
                    low_name = fname_t.lower()
                    if site_id.lower() in low_name and low_name.endswith(('.mat', '.csv', '.txt')):
                        candidate_file = os.path.join(tran_dir, fname_t)
                        break
        if candidate_file:
            endpoints: list[tuple[tuple[float, float], tuple[float, float]]] = []
            if candidate_file.lower().endswith('.mat'):
                endpoints = transect_utils.load_transects_from_mat(candidate_file)
            else:
                try:
                    with open(candidate_file, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if not line or line.startswith("#"):
                                continue
                            parts = [p for p in line.replace(",", " ").split() if p]
                            if len(parts) >= 4:
                                try:
                                    x0, y0, x1, y1 = map(float, parts[:4])
                                    endpoints.append(((x0, y0), (x1, y1)))
                                except ValueError:
                                    continue
                except Exception:
                    endpoints = []
            if endpoints:
                self.transects = endpoints
                auto_transects_loaded = True
        # Compose info text to display
        info_parts: list[str] = []
        # Include image filename (without path)
        info_parts.append(f"Image: {fname}")
        if site_info:
            info_parts.append(f"Site: {site_info.get('site_name', site_id)}")
        elif site_id:
            info_parts.append(f"Site: {site_id}")
        if epoch_time is not None:
            # Convert epoch to human date/time for display
            import datetime
            dt = datetime.datetime.utcfromtimestamp(epoch_time)
            info_parts.append(dt.strftime("%Y-%m-%d %H:%M UTC"))
        if tide_level is not None:
            info_parts.append(f"Tide: {tide_level:.2f} m")
        # Show expected GCP names if available
        if self.gcp_names_order and len(self.gcp_names_order) == self.expected_gcp_count:
            gcp_names_str = ", ".join(self.gcp_names_order)
            info_parts.append(f"GCPs: {gcp_names_str}")
        if auto_transects_loaded:
            info_parts.append("Transects loaded")
        # Build the info string and update the base info.  Store it so we can
        # append instructions (such as "Next GCP") during GCP collection.
        info_str = " | ".join(info_parts)
        self.base_info = info_str
        # Update info label
        self.info_var.set(info_str)
        messagebox.showinfo(
            "Image loaded",
            "Image loaded. Click 'Rectify Image' and then select the ground control points.\n"
            + ("\n".join(info_parts) if info_parts else "")
        )

    def rectify_image(self) -> None:
        """Start GCP selection to compute and apply the homography."""
        if self.oblq_image is None:
            messagebox.showwarning("Warning", "Load an image before rectifying.")
            return
        # Clear previous rectification state
        self.src_points.clear()
        self.plan_image = None
        self.plan_cv = None
        self.rectified = False
        # Always prompt the user to manually click GCPs; automatic detection of markers is disabled
        self.collecting_gcp = True
        # Determine how many points to request and build instruction message
        msg = ""
        # Show detailed instructions with GCP names if available
        if self.gcp_names_order:
            # Build a detailed instruction including GCP names
            names_list = '\n'.join([
                f"{i+1}. {name}" for i, name in enumerate(self.gcp_names_order)
            ])
            msg = (
                "Please click the ground control points in the order listed below:\n\n"
                f"{names_list}\n\n"
                "Use the zoom tools of your mouse if needed."
            )
            # Ensure expected count matches the number of names
            self.expected_gcp_count = len(self.gcp_names_order)
            messagebox.showinfo("Select GCPs", msg)
            # Update the info bar to prompt for the first GCP (if applicable)
            self._update_next_gcp_info()
        else:
            # If no GCP information is available from the database, do not allow generic point selection
            messagebox.showerror(
                "GCP information missing",
                "The selected site does not have ground control points defined in the database.\n"
                "Please check your CoastSnapDB.xlsx or select a different site."
            )
            # Prevent collecting GCP points
            self.collecting_gcp = False
            self.expected_gcp_count = 0
            return
    def map_shoreline(self) -> None:
        """Enable shoreline digitisation on the rectified image."""
        if not self.rectified:
            messagebox.showwarning("Warning", "Rectify the image before mapping the shoreline.")
            return
        self.collecting_shoreline = True
        messagebox.showinfo(
            "Digitise shoreline",
            "Click points along the shoreline on the rectified image.\n"
            "When finished, click 'Save Shoreline' to export the coordinates."
        )

    def save_shoreline(self) -> None:
        """Save digitised shoreline points to a CSV file."""
        if not self.shoreline_points:
            messagebox.showwarning("Warning", "No shoreline points to save.")
            return
        filepath = filedialog.asksaveasfilename(
            title="Save shoreline points",
            defaultextension=".csv",
            initialfile="shoreline_points.csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not filepath:
            return
        try:
            with open(filepath, "w", newline="") as f:
                # If we have rectification metadata, output world coordinates
                if self.rect_world_limits and self.rect_resolution:
                    x_min, x_max, y_min, y_max = self.rect_world_limits
                    res = self.rect_resolution
                    f.write("easting,northing\n")
                    for px, py in self.shoreline_points:
                        try:
                            # Convert rectified pixel coords to world coordinates
                            easting = x_min + float(px) * res
                            northing = y_max - float(py) * res
                            f.write(f"{easting},{northing}\n")
                        except Exception:
                            f.write(f"{px},{py}\n")
                else:
                    # Fallback: write pixel coordinates
                    f.write("x,y\n")
                    for x, y in self.shoreline_points:
                        f.write(f"{x},{y}\n")
            messagebox.showinfo("Success", f"Saved {len(self.shoreline_points)} points to {os.path.basename(filepath)}")
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to save points: {exc}")

    # ------------------------------------------------------------------
    # ROI selection
    def select_roi(self) -> None:
        """Enable selection of a region of interest on the rectified image.

        The user will be prompted to click two points (top‑left and
        bottom‑right corners) on the plan canvas to define a rectangular
        ROI.  This ROI will limit the area used for automatic shoreline
        detection.  Selecting a new ROI overrides any existing one.
        """
        if not self.rectified:
            messagebox.showwarning("Warning", "Rectify the image before selecting an ROI.")
            return
        self.selecting_roi = True
        self._roi_start = None
        # Temporarily disable shoreline digitisation while selecting ROI
        self.collecting_shoreline = False
        # Remove any existing ROI rectangle from the canvas
        if self._roi_rect_id is not None:
            self.plan_canvas.delete(self._roi_rect_id)
            self._roi_rect_id = None
        messagebox.showinfo(
            "Select ROI",
            "Click two points on the rectified image: top‑left and bottom‑right corners of the desired region."
        )

    def load_transects(self) -> None:
        """Load transect definitions from a CSV or text file.

        The file should contain one transect per line, with four values
        separated by commas or whitespace: ``x0, y0, x1, y1``.  These
        coordinates are assumed to be in the coordinate system of the
        rectified image (pixel units).  After loading, the transects
        will be drawn on the plan canvas and a bounding box covering
        all transects will be used as the region of interest (ROI) for
        automatic detection.
        """
        if not self.rectified or self.plan_cv is None:
            messagebox.showwarning(
                "Warning", "Rectify the image before loading transects."
            )
            return
        filetypes = [
            ("CSV or text files", "*.csv;*.txt"),
            ("CSV files", "*.csv"),
            ("Text files", "*.txt"),
            ("All files", "*.*"),
        ]
        filepath = filedialog.askopenfilename(
            title="Select transect file", filetypes=filetypes
        )
        if not filepath:
            return
        endpoints: list[tuple[tuple[float, float], tuple[float, float]]] = []
        # If a MATLAB .mat file is selected, try to parse using transect_utils
        if filepath.lower().endswith(".mat"):
            endpoints = transect_utils.load_transects_from_mat(filepath)
        # Otherwise assume CSV/text format with x0,y0,x1,y1 per line
        if not endpoints:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        parts = [p for p in line.replace(",", " ").split() if p]
                        if len(parts) < 4:
                            continue
                        try:
                            x0, y0, x1, y1 = map(float, parts[:4])
                            endpoints.append(((x0, y0), (x1, y1)))
                        except ValueError:
                            continue
            except Exception as exc:
                messagebox.showerror("Error", f"Failed to load transects: {exc}")
                return
        if not endpoints:
            messagebox.showwarning("Warning", "No valid transects found in file.")
            return
        self.transects = endpoints
        # Compute bounding box across all transect endpoints
        xs = []
        ys = []
        for (p0, p1) in endpoints:
            xs.extend([p0[0], p1[0]])
            ys.extend([p0[1], p1[1]])
        if xs and ys:
            x_min = int(min(xs))
            x_max = int(max(xs))
            y_min = int(min(ys))
            y_max = int(max(ys))
            # Ensure values within image bounds
            h, w, _ = self.plan_cv.shape
            x_min = max(0, min(x_min, w - 1))
            x_max = max(0, min(x_max, w - 1))
            y_min = max(0, min(y_min, h - 1))
            y_max = max(0, min(y_max, h - 1))
            self.roi = (x_min, y_min, x_max, y_max)
        else:
            self.roi = None
        # Refresh plan display to draw transects and ROI
        self.display_plan()
        messagebox.showinfo(
            "Transects loaded",
            f"Loaded {len(endpoints)} transects. ROI set to x[{self.roi[0]}:{self.roi[2]}], y[{self.roi[1]}:{self.roi[3]}].",
        )

    def auto_detect_shoreline(self) -> None:
        """Automatically detect the shoreline on the rectified image.

        This method uses a simple image segmentation approach to separate
        land and water based on grayscale intensity.  For each column in
        the rectified image, it locates the transition between water
        (darker) and land (lighter) by finding the first white pixel
        after thresholding.  The resulting pixels form a polyline
        approximation of the shoreline.
        """
        if not self.rectified or self.plan_cv is None:
            messagebox.showwarning("Warning", "Rectify the image before running auto detection.")
            return
        # Improved shoreline detection based on vertical intensity gradients.
        # Convert rectified image to grayscale and apply a Gaussian blur to reduce noise.
        img_cv = self.plan_cv.copy()
        h, w, _ = img_cv.shape
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (5, 5), 0)

        # Determine region of interest (ROI).  If ROI is defined, restrict detection to that rectangle.
        if self.roi is not None:
            x_start, y_start, x_end, y_end = self.roi
        else:
            x_start, y_start, x_end, y_end = 0, 0, w - 1, h - 1
        # Clamp ROI to image bounds
        x_start = int(max(0, min(x_start, w - 1)))
        x_end = int(max(0, min(x_end, w - 1)))
        y_start = int(max(0, min(y_start, h - 1)))
        y_end = int(max(0, min(y_end, h - 1)))
        # Ensure ROI ranges are ordered
        if x_end < x_start:
            x_start, x_end = x_end, x_start
        if y_end < y_start:
            y_start, y_end = y_end, y_start
        detected_points: List[Tuple[int, int]] = []
        # For each column within the ROI, find the vertical position with the largest positive intensity change
        for x in range(x_start, x_end + 1):
            # Extract the column segment within the ROI
            col = gray[y_start : y_end + 1, x]
            if col.size < 2:
                continue
            # Compute the first derivative (difference between adjacent pixel intensities)
            diff = np.diff(col.astype(np.float32), axis=0)
            # Compute absolute gradient values to find significant changes
            abs_diff = np.abs(diff)
            # Identify the index of the maximum gradient
            idx_max = int(np.argmax(abs_diff))
            # Map index back to full image coordinates
            y_coord = y_start + idx_max
            # Optional: ensure the gradient is a transition from darker (water) to lighter (sand)
            # i.e., diff[idx_max] > 0.  If not, we could skip or use another index, but here we accept any.
            detected_points.append((x, y_coord))
        # If no points detected, abort
        if not detected_points:
            messagebox.showwarning("Warning", "Auto detection failed to identify shoreline in the selected region.")
            return
        # Smooth the y positions using a moving average to reduce noise
        ys = np.array([pt[1] for pt in detected_points], dtype=np.float32)
        xs = np.array([pt[0] for pt in detected_points], dtype=np.float32)
        # Determine smoothing window size: 2% of ROI width, minimum 5 and make it odd
        window = max(5, int((x_end - x_start + 1) * 0.02))
        if window % 2 == 0:
            window += 1
        kernel_smooth = np.ones(window, dtype=np.float32) / window
        ys_smooth = np.convolve(ys, kernel_smooth, mode='same')
        smoothed_points = [(int(xs[i]), int(ys_smooth[i])) for i in range(len(xs))]
        # Update shoreline points and refresh display
        self.shoreline_points = smoothed_points
        self.collecting_shoreline = False
        self.display_plan()
        messagebox.showinfo(
            "Detection complete",
            f"Detected shoreline with {len(smoothed_points)} points in the selected region."
        )

    def reset_session(self, clear_image: bool = True) -> None:
        """Reset the current session state.  Optionally clear loaded images."""
        self.collecting_gcp = False
        self.collecting_shoreline = False
        self.src_points.clear()
        self.shoreline_points.clear()
        self.rectified = False
        # Clear prominent GCP prompt
        self.gcp_prompt_var.set("")
        # Reset editing state
        self.selected_point_index = None
        self.dragging = False
        # Reset zoom/pan and hover state
        self.oblq_zoom = 1.0
        self.oblq_pan = [0.0, 0.0]
        self._last_mouse_pos = None
        self._last_hover = None
        # Reset ROI selection state
        self.roi = None
        self.selecting_roi = False
        self._roi_start = None
        # Remove ROI rectangle from canvas
        if self._roi_rect_id is not None:
            self.plan_canvas.delete(self._roi_rect_id)
            self._roi_rect_id = None
        # Reset loaded transects
        self.transects = None
        if clear_image:
            self.oblq_image = None
            self.oblq_cv = None
            self.plan_image = None
            self.plan_cv = None
            # Reset homography
            self.homography = None
            self.oblq_canvas.delete("all")
            self.plan_canvas.delete("all")
        else:
            self.display_oblique()
            self.display_plan()

    # ------------------------------------------------------------------
    # Automatic GCP detection
    def _auto_detect_gcp_markers(self) -> List[Tuple[int, int]]:
        """Attempt to detect ground control point markers automatically.

        This function uses simple image processing heuristics to locate
        high‑contrast circular or bright features that may correspond to
        ground control points (GCPs) on the oblique image.  It first
        attempts to detect circular features using the Hough Circles
        transform.  If insufficient circles are found, it performs a
        brightness threshold and contour analysis to identify bright
        blobs.  The detected markers are sorted top‑to‑bottom and
        left‑to‑right to approximate the order expected for GCP
        collection (clockwise from top‑left).

        Returns
        -------
        list of (int, int)
            A list of (x, y) pixel coordinates for the detected GCP
            markers.  The length of the list may be less than the
            expected number of points; in that case, manual selection
            should be used as a fallback.
        """
        points: List[Tuple[int, int]] = []
        if self.oblq_cv is None:
            return points
        img_cv = self.oblq_cv.copy()
        # Convert to grayscale
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        # Apply median blur to reduce noise while preserving edges
        gray_blur = cv2.medianBlur(gray, 5)
        # Try to detect circles using Hough transform
        try:
            circles = cv2.HoughCircles(
                gray_blur,
                cv2.HOUGH_GRADIENT,
                dp=1.5,
                minDist=max(10, gray.shape[1] // 20),
                param1=50,
                param2=30,
                minRadius=3,
                maxRadius=50,
            )
            if circles is not None:
                circ_list = np.round(circles[0, :]).astype(int).tolist()
                # Sort by y (ascending) then x (ascending) to approximate top‑left, top‑right, bottom‑right, bottom‑left
                circ_list.sort(key=lambda c: (c[1], c[0]))
                for c in circ_list:
                    points.append((int(c[0]), int(c[1])))
        except Exception:
            pass
        # If not enough points, fallback to bright blob detection
        if len(points) < self.expected_gcp_count:
            points = []  # reset
            # Threshold bright regions; assume GCP markers are brighter than surrounding sand or water
            _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
            # Morphological opening to remove noise
            kernel = np.ones((3, 3), np.uint8)
            thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
            # Find contours
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            blobs: List[Tuple[int, int, float]] = []  # x, y, area
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area < 50 or area > 5000:
                    continue
                x, y, w, h = cv2.boundingRect(cnt)
                # Skip elongated shapes; prefer roughly square/round
                if w == 0 or h == 0:
                    continue
                ratio = max(w, h) / max(1.0, min(w, h))
                if ratio > 3.0:
                    continue
                # Compute centroid
                M = cv2.moments(cnt)
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                    blobs.append((cx, cy, area))
            # Sort blobs by y then x
            blobs.sort(key=lambda b: (b[1], b[0]))
            for b in blobs:
                points.append((b[0], b[1]))
        # Limit to expected number of GCPs
        if points:
            points = points[: self.expected_gcp_count]
        return points

    # ------------------------------------------------------------------
    # Event handlers
    def _on_oblq_click(self, event: tk.Event) -> None:
        """Mouse clicks on oblique canvas are disabled; use spacebar instead."""
        return

    def _on_plan_click(self, event: tk.Event) -> None:
        """Handle clicks on the plan image canvas during shoreline digitisation."""
        # If we are selecting a region of interest, handle ROI clicks first
        if self.selecting_roi:
            if self.plan_image is None or self.plan_cv is None:
                return
            # Convert canvas click to image coordinates
            disp_w, disp_h = self.plan_display_size
            orig_h, orig_w, _ = self.plan_cv.shape
            canvas_w = int(self.plan_canvas.winfo_width()) or disp_w
            canvas_h = int(self.plan_canvas.winfo_height()) or disp_h
            x0_canvas = (canvas_w - disp_w) / 2
            y0_canvas = (canvas_h - disp_h) / 2
            x_rel = (event.x - x0_canvas) / disp_w
            y_rel = (event.y - y0_canvas) / disp_h
            x_rel = min(max(x_rel, 0.0), 1.0)
            y_rel = min(max(y_rel, 0.0), 1.0)
            img_x = int(x_rel * orig_w)
            img_y = int(y_rel * orig_h)
            if self._roi_start is None:
                # First click defines top‑left corner (temporarily)
                self._roi_start = (img_x, img_y)
            else:
                # Second click defines bottom‑right; compute bounding box
                x0, y0 = self._roi_start
                x1, y1 = img_x, img_y
                # Ensure x0 <= x1 and y0 <= y1
                x_min, x_max = sorted((x0, x1))
                y_min, y_max = sorted((y0, y1))
                self.roi = (x_min, y_min, x_max, y_max)
                self.selecting_roi = False
                self._roi_start = None
                # Draw rectangle overlay on canvas
                # Convert image coordinates to canvas coords for both corners
                cx0 = x0_canvas + (self.roi[0] / orig_w) * disp_w
                cy0 = y0_canvas + (self.roi[1] / orig_h) * disp_h
                cx1 = x0_canvas + (self.roi[2] / orig_w) * disp_w
                cy1 = y0_canvas + (self.roi[3] / orig_h) * disp_h
                self._roi_rect_id = self.plan_canvas.create_rectangle(
                    cx0, cy0, cx1, cy1, outline="green", width=2
                )
                messagebox.showinfo(
                    "ROI set",
                    f"Region of interest defined: x[{self.roi[0]}:{self.roi[2]}], y[{self.roi[1]}:{self.roi[3]}]"
                )
            return

        # Normal shoreline digitisation and editing
        if not self.collecting_shoreline:
            return
        if self.plan_image is None or self.plan_cv is None:
            return
        # Determine displayed and original image dimensions
        disp_w, disp_h = self.plan_display_size
        orig_h, orig_w, _ = self.plan_cv.shape
        canvas_w = int(self.plan_canvas.winfo_width()) or disp_w
        canvas_h = int(self.plan_canvas.winfo_height()) or disp_h
        # Offset of image in canvas (centred)
        x0 = (canvas_w - disp_w) / 2
        y0 = (canvas_h - disp_h) / 2
        # Check if the click is near an existing shoreline point (for editing)
        threshold = 8  # pixel radius on canvas to select a point
        for idx, (img_x_p, img_y_p) in enumerate(self.shoreline_points):
            # Convert existing point image coordinates to canvas coordinates
            x_rel_p = img_x_p / orig_w
            y_rel_p = img_y_p / orig_h
            canvas_x_p = x0 + x_rel_p * disp_w
            canvas_y_p = y0 + y_rel_p * disp_h
            dist = ((event.x - canvas_x_p) ** 2 + (event.y - canvas_y_p) ** 2) ** 0.5
            if dist <= threshold:
                # Select this point for dragging/editing
                self.selected_point_index = idx
                self.dragging = True
                return
        # Not near existing point: add a new point
        x_rel = (event.x - x0) / disp_w
        y_rel = (event.y - y0) / disp_h
        x_rel = min(max(x_rel, 0.0), 1.0)
        y_rel = min(max(y_rel, 0.0), 1.0)
        img_x = int(x_rel * orig_w)
        img_y = int(y_rel * orig_h)
        self.shoreline_points.append((img_x, img_y))
        # Draw on canvas
        self._draw_circle(self.plan_canvas, event.x, event.y, radius=3, color="blue", display_scale=False, is_plan=True)

    # ------------------------------------------------------------------
    # Processing functions
    def compute_rectification(self) -> None:
        """Rectify the image.

        Primary path: MATLAB-style camera model (CSPGrectifyImage):
          * fixed camera position at station origin (0,0,z0)
          * fit az/tilt/roll with non-linear least squares
          * grid-search focal length between Min/Max FOV limits
          * rectify by projecting z = tide + tidal_offset onto a local (x,y) grid

        Fallback: simple homography.
        """
        print(f"[DEBUG] compute_rectification called with {len(self.src_points)} GCPs")
        # MATLAB-style can be attempted with >=3 (ambiguous) but is reliable with >=4.
        if len(self.src_points) < 3:
            messagebox.showwarning("Not enough GCPs", "Place au moins 3 points pour lancer la rectification.")
            return
        if self.oblq_cv is None:
            return
        # Convert source points to numpy array
        src_pts = np.array(self.src_points[: len(self.src_points)], dtype=np.float32)
        # Helper for tolerant key lookup on GCP dicts (handles easting/eastings, etc.)
        def _g(v: dict, *keys: str) -> float:
            for k in keys:
                if k in v and v[k] is not None:
                    try:
                        return float(v[k])
                    except Exception:
                        continue
            raise KeyError(keys[0])
        # Determine destination image and homography using site metadata or fallback
        site_info = self.current_site_info if self.current_site_info else None
        gcp_world_list = self.gcp_world_points if self.gcp_world_points else None
        print("[DEBUG] site_info keys:", list(site_info.keys()) if isinstance(site_info, dict) else None)
        print("[DEBUG] gcp_world_list len:", len(gcp_world_list) if gcp_world_list else 0)
        dest_pts = None
        out_width: int | None = None
        out_height: int | None = None
        # --- MATLAB-style camera model rectification (preferred) ---
        if (
            site_info
            and gcp_world_list
            and isinstance(site_info, dict)
            and 'Min FOV' in site_info
            and 'Max FOV' in site_info
            and all(k in site_info for k in ['Xlimit left', 'Xlimit right', 'Ylimit lower', 'Ylimit upper', 'Resolution'])
            and 'Eastings' in site_info
            and 'Northings' in site_info
        ):
            try:
                img_h, img_w = self.oblq_cv.shape[:2]
                camera_res = (int(img_w), int(img_h))

                origin_east = float(site_info['Eastings'])
                origin_north = float(site_info['Northings'])
                origin_z = float(site_info.get('Elevation', 0.0))

                # MATLAB-style xyz: x/y local (metres), z absolute datum
                xyz_list = []
                for g in gcp_world_list:
                    east = _g(g, 'eastings', 'easting')
                    north = _g(g, 'northings', 'northing')
                    elev = float(g.get('elevation', 0.0))
                    xyz_list.append([east - origin_east, north - origin_north, elev])
                xyz = np.array(xyz_list, dtype=float)
                uv_obs = src_pts.astype(float)

                # Initial angles from DB (degrees)
                az0 = float(site_info.get('Initial Azimuth Estimate', 0.0))
                tilt0 = float(site_info.get('Initial Tilt Estimate', 90.0))
                roll0 = float(site_info.get('Initial Roll Estimate', 0.0))

                # FOV limits from DB
                fov_min = float(site_info['Min FOV'])
                fov_max = float(site_info['Max FOV'])

                # Camera position fixed at station (MATLAB): x=y=0 local, z=station elevation
                cam_xyz = (0.0, 0.0, origin_z)

                # Rectification limits (local metres)
                xlim_left = float(site_info['Xlimit left'])
                xlim_right = float(site_info['Xlimit right'])
                ylim_lower = float(site_info['Ylimit lower'])
                ylim_upper = float(site_info['Ylimit upper'])
                res = float(site_info['Resolution'])
                rectxy = (xlim_left, res, xlim_right, ylim_lower, res, ylim_upper)

                # Rectification z (absolute) = tide + tidal_offset (we store it at load)
                rectz_abs = float(getattr(self, 'tide_level', None) or 0.0)
                if rectz_abs == 0.0:
                    rectz_abs = origin_z

                from ..tools.matlab_camera_rectify import matlab_style_calibrate, rectify_image_matlab_style

                calib = matlab_style_calibrate(
                    xyz=xyz,
                    uv_obs=uv_obs,
                    camera_res=camera_res,
                    cam_xyz=cam_xyz,
                    angles0_deg=(az0, tilt0, roll0),
                    fov_limits_deg=(fov_min, fov_max),
                )

                rect_cv, xgrid, ygrid = rectify_image_matlab_style(
                    bgr_image=self.oblq_cv,
                    calib=calib,
                    cam_xyz=cam_xyz,
                    rectxy=rectxy,
                    rectz_abs=rectz_abs,
                )

                self.plan_cv = rect_cv
                rect_rgb = cv2.cvtColor(rect_cv, cv2.COLOR_BGR2RGB)
                self.plan_image = Image.fromarray(rect_rgb)
                self.rectified = True

                # Absolute EN limits for exports
                world_limits = (
                    xlim_left + origin_east,
                    xlim_right + origin_east,
                    ylim_lower + origin_north,
                    ylim_upper + origin_north,
                )
                self.rect_world_limits = world_limits
                self.rect_resolution = res
                self.rect_out_size = (rect_cv.shape[1], rect_cv.shape[0])

                self.calib_fov = float(calib.get('fov_deg', 0.0))
                self.calib_error = float(calib.get('rmse', 0.0))
                self.calib_zplane = float(rectz_abs)

                info_txt = self.base_info if hasattr(self, 'base_info') else (self.info_var.get() or "")
                add_parts = [
                    f"FOV: {self.calib_fov:.1f}°",
                    f"RMSE: {self.calib_error:.2f}px",
                    f"Zrect: {self.calib_zplane:.2f}m",
                ]
                self.info_var.set((info_txt + " | " if info_txt else "") + " | ".join(add_parts))

                self.display_plan()
                return
            except Exception:
                print("[DEBUG] Camera-model rectification failed, falling back to homography/affine")
                print(traceback.format_exc())
                # If calibration fails, fall back to homography method
                pass

        # Homography/affine fallback needs at least 3 points
        if len(self.src_points) < 3:
            print("[DEBUG] Fallback skipped: fewer than 3 points")
            return
        # If advanced calibration not performed, fallback to simpler homography method
        # Determine destination points and output size based on site metadata as before
        dest_pts = None
        out_width = None
        out_height = None
        gcp_world = gcp_world_list
        if (
            site_info
            and gcp_world
            and isinstance(site_info, dict)
            and all(k in site_info for k in ['Xlimit left', 'Xlimit right', 'Ylimit lower', 'Ylimit upper', 'Resolution'])
            and 'Eastings' in site_info
            and 'Northings' in site_info
        ):
            try:
                xlim_left = float(site_info['Xlimit left'])
                xlim_right = float(site_info['Xlimit right'])
                ylim_lower = float(site_info['Ylimit lower'])
                ylim_upper = float(site_info['Ylimit upper'])
                res = float(site_info['Resolution'])
                origin_east = float(site_info['Eastings'])
                origin_north = float(site_info['Northings'])
                out_width = int(round((xlim_right - xlim_left) / res))
                out_height = int(round((ylim_upper - ylim_lower) / res))
                dest_list: list[list[float]] = []
                for gcp in gcp_world:
                    east = _g(gcp, 'eastings', 'easting')
                    north = _g(gcp, 'northings', 'northing')
                    x_rel = east - origin_east
                    y_rel = north - origin_north
                    dest_x = (x_rel - xlim_left) / res
                    dest_y = (ylim_upper - y_rel) / res
                    dest_list.append([dest_x, dest_y])
                dest_pts = np.array(dest_list[: len(src_pts)], dtype=np.float32)
            except Exception:
                dest_pts = None
        print("[DEBUG] dest_pts before fallback:", None if dest_pts is None else dest_pts.shape)
        if dest_pts is None or len(dest_pts) < 3:
            out_width = 800
            out_height = 800
            dest_pts = np.array(
                [[0, 0], [out_width - 1, 0], [out_width - 1, out_height - 1], [0, out_height - 1]], dtype=np.float32
            )
        # Check if any dest point is out of bounds
        need_bbox = False
        if dest_pts is not None and out_width is not None and out_height is not None:
            for (dx, dy) in dest_pts:
                if dx < 0 or dy < 0 or dx > out_width or dy > out_height:
                    need_bbox = True
                    break
        if need_bbox and gcp_world:
            try:
                x_coords = []
                y_coords = []
                for g in gcp_world:
                    east = _g(g, 'eastings', 'easting')
                    north = _g(g, 'northings', 'northing')
                    x_rel = (east - origin_east) / res
                    y_rel = (north - origin_north) / res
                    x_coords.append(x_rel)
                    y_coords.append(y_rel)
                x_min = min(x_coords)
                x_max = max(x_coords)
                y_min = min(y_coords)
                y_max = max(y_coords)
                out_width = int(round((x_max - x_min)))
                out_height = int(round((y_max - y_min)))
                if out_width <= 0 or out_height <= 0:
                    out_width = out_height = 800
                dest_pts_list = []
                for g in gcp_world[: len(src_pts)]:
                    east = _g(g, 'eastings', 'easting')
                    north = _g(g, 'northings', 'northing')
                    x_rel = (east - origin_east) / res
                    y_rel = (north - origin_north) / res
                    dest_x = x_rel - x_min
                    dest_y = (y_max - y_rel)
                    dest_pts_list.append([dest_x, dest_y])
                dest_pts = np.array(dest_pts_list, dtype=np.float32)
            except Exception as e:
                print("[DEBUG] need_bbox fallback failed", e)
                print(traceback.format_exc())
                out_width = 800
                out_height = 800
                dest_pts = np.array(
                    [[0, 0], [out_width - 1, 0], [out_width - 1, out_height - 1], [0, out_height - 1]], dtype=np.float32
                )
        # Compute homography using simple method
        pair_count = min(len(src_pts), len(dest_pts))
        print(f"[DEBUG] pair_count={pair_count}, src_pts shape={src_pts.shape}, dest_pts shape={dest_pts.shape}, out_size={(out_width, out_height)}")
        if pair_count < 3:
            messagebox.showerror("Error", "At least 3 GCPs are required for rectification.")
            return
        if pair_count == 3:
            # Affine transform using 3-point mapping
            try:
                M = cv2.getAffineTransform(
                    src_pts[:3].astype(np.float32),
                    dest_pts[:3].astype(np.float32),
                )
                if out_width is None or out_height is None:
                    out_width = 800
                    out_height = 800
                rectified_cv = cv2.warpAffine(self.oblq_cv, M, (int(out_width), int(out_height)))
                # Store as 3x3 for consistency in downstream usage
                self.homography = np.vstack([M, [0.0, 0.0, 1.0]])
                print("[DEBUG] Applied affine rectification (3-point)")
            except Exception as e:
                print("[DEBUG] Affine rectification failed", e)
                print(traceback.format_exc())
                messagebox.showerror("Error", f"Affine rectification failed: {e}")
                return
        else:
            try:
                H, mask = cv2.findHomography(src_pts[:pair_count], dest_pts[:pair_count])
                if H is None:
                    messagebox.showerror("Error", "Failed to compute homography.")
                    return
                self.homography = H
                if out_width is None or out_height is None:
                    out_width = 800
                    out_height = 800
                rectified_cv = cv2.warpPerspective(self.oblq_cv, H, (int(out_width), int(out_height)))
                print("[DEBUG] Applied homography rectification (>=4 points)")
            except Exception as e:
                print("[DEBUG] Homography rectification failed", e)
                print(traceback.format_exc())
                messagebox.showerror("Error", f"Homography rectification failed: {e}")
                return
        self.plan_cv = rectified_cv
        rect_rgb = cv2.cvtColor(rectified_cv, cv2.COLOR_BGR2RGB)
        self.plan_image = Image.fromarray(rect_rgb)
        self.rectified = True
        # Clear calibration results when using simple homography
        self.calib_fov = None
        self.calib_error = None
        # If transects were loaded prior to rectification, compute ROI now
        if self.transects is not None:
            xs = []
            ys = []
            for (p0, p1) in self.transects:
                xs.extend([p0[0], p1[0]])
                ys.extend([p0[1], p1[1]])
            if xs and ys:
                x_min = max(0, int(min(xs)))
                x_max = max(0, int(max(xs)))
                y_min = max(0, int(min(ys)))
                y_max = max(0, int(max(ys)))
                self.roi = (x_min, y_min, x_max, y_max)
        # Refresh plan view and inform user of completion
        self.display_plan()
        messagebox.showinfo("Rectification complete", "Image has been rectified.")
        return

    # ------------------------------------------------------------------
    # Event handlers for editing shoreline points
    def _on_plan_motion(self, event: tk.Event) -> None:
        """Handle mouse motion on the plan canvas when dragging a point."""
        if not self.collecting_shoreline:
            return
        if not self.dragging or self.selected_point_index is None:
            return
        if self.plan_image is None or self.plan_cv is None:
            return
        # Convert canvas coordinates back to image coordinates
        disp_w, disp_h = self.plan_display_size
        orig_h, orig_w, _ = self.plan_cv.shape
        canvas_w = int(self.plan_canvas.winfo_width()) or disp_w
        canvas_h = int(self.plan_canvas.winfo_height()) or disp_h
        x0 = (canvas_w - disp_w) / 2
        y0 = (canvas_h - disp_h) / 2
        x_rel = (event.x - x0) / disp_w
        y_rel = (event.y - y0) / disp_h
        x_rel = min(max(x_rel, 0.0), 1.0)
        y_rel = min(max(y_rel, 0.0), 1.0)
        img_x = int(x_rel * orig_w)
        img_y = int(y_rel * orig_h)
        # Update the selected point
        self.shoreline_points[self.selected_point_index] = (img_x, img_y)
        # Refresh display to show updated point positions and lines
        self.display_plan()

    def _on_plan_release(self, event: tk.Event) -> None:
        """Reset dragging state on mouse release."""
        if self.dragging:
            self.dragging = False
            self.selected_point_index = None

    # ------------------------------------------------------------------
    # Utility drawing
    def _draw_circle(
        self,
        canvas: tk.Canvas,
        x: float,
        y: float,
        radius: int,
        color: str,
        display_scale: bool,
        is_plan: bool,
    ) -> None:
        """Draw a circle marker on a canvas.  If display_scale is True,
        the provided x/y values correspond to image coordinates and
        will be scaled to the current canvas dimensions."""
        if display_scale:
            if is_plan:
                disp_w, disp_h = self.plan_display_size
                if self.plan_cv is None:
                    return
                orig_h, orig_w, _ = self.plan_cv.shape
                canvas_w = int(self.plan_canvas.winfo_width()) or disp_w
                canvas_h = int(self.plan_canvas.winfo_height()) or disp_h
                x0 = (canvas_w - disp_w) / 2
                y0 = (canvas_h - disp_h) / 2
                x_rel = x / orig_w
                y_rel = y / orig_h
                canvas_x = x0 + x_rel * disp_w
                canvas_y = y0 + y_rel * disp_h
            else:
                disp_w, disp_h = self.oblq_display_size
                if self.oblq_image is None:
                    return
                orig_w, orig_h = self.oblq_image.size
                canvas_w = int(self.oblq_canvas.winfo_width()) or disp_w
                canvas_h = int(self.oblq_canvas.winfo_height()) or disp_h
                pan_x, pan_y = self.oblq_pan
                x0 = (canvas_w - disp_w) / 2 + pan_x
                y0 = (canvas_h - disp_h) / 2 + pan_y
                x_rel = x / orig_w
                y_rel = y / orig_h
                canvas_x = x0 + x_rel * disp_w
                canvas_y = y0 + y_rel * disp_h
        else:
            canvas_x, canvas_y = x, y
        r = radius
        canvas.create_oval(canvas_x - r, canvas_y - r, canvas_x + r, canvas_y + r, outline=color, fill=color)


def main() -> None:
    """Entry point for launching the CoastSnap GUI."""
    root = tk.Tk()
    app = CoastSnapGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
