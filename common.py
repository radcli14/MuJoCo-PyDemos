#!/usr/bin/env python3
"""
common.py — shared helpers for the MuJoCo-PyDemos simulations.

Lives at the repo root.  The demo scripts live in sub-directories, so add the
repo root to sys.path and import this *before* mujoco — selecting the OpenGL
backend only works if MUJOCO_GL is set before mujoco is first imported, which
this module does on import:

    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    import common          # selects the GL backend, then imports mujoco
    import mujoco
"""
import os
import sys

# Choose the OpenGL backend before mujoco is imported anywhere.
# macOS has no EGL; Linux defaults to EGL for headless offscreen rendering.
os.environ.setdefault("MUJOCO_GL", "glfw" if sys.platform == "darwin" else "egl")

import mujoco                       # noqa: E402  (must follow the MUJOCO_GL line)
import imageio                      # noqa: E402
import matplotlib                   # noqa: E402
matplotlib.use("Agg")               # non-interactive backend; safe for headless use
import matplotlib.pyplot as plt     # noqa: E402


# ── plot theme (shared dark palette) ──────────────────────────────────────────
class Palette:
    """Dark UI palette shared by the demo state plots."""
    BG    = "#070c17"
    CARD  = "#10192b"
    EDGE  = "#1b2e45"
    TEXT  = "#e6edf5"
    MUTED = "#7a92ab"
    RED   = "#ef4444"
    BLUE  = "#3b82f6"
    GREEN = "#4ade80"


def style_ax(ax):
    """Apply the dark card style to a matplotlib Axes."""
    ax.set_facecolor(Palette.CARD)
    for spine in ax.spines.values():
        spine.set_edgecolor(Palette.EDGE)
    ax.tick_params(colors=Palette.MUTED)
    ax.grid(alpha=0.15, color=Palette.EDGE)


# ── camera ────────────────────────────────────────────────────────────────────
def make_free_camera(lookat, distance, azimuth, elevation):
    """Create a free MjvCamera at the given orbit parameters."""
    cam = mujoco.MjvCamera()
    mujoco.mjv_defaultCamera(cam)
    cam.type      = mujoco.mjtCamera.mjCAMERA_FREE
    cam.lookat[:] = lookat
    cam.distance  = distance
    cam.azimuth   = azimuth
    cam.elevation = elevation
    return cam


# ── simulation / rendering helpers ────────────────────────────────────────────
def steps_per_frame(fps, dt):
    """Number of physics steps between rendered frames for a target video fps."""
    return max(1, round(1.0 / (fps * dt)))


def save_video(frames, path, fps=60):
    """Write a list of RGB frames to an mp4 via imageio/ffmpeg."""
    print(f"Saving video → {path}")
    writer = imageio.get_writer(
        str(path), fps=fps, format="ffmpeg", quality=8, macro_block_size=None,
    )
    for frame in frames:
        writer.append_data(frame)
    writer.close()
    print(f"  {len(frames)} frames written.")


def save_thumbnail(plot_path, quality="70-85"):
    """Generate a compressed thumbnail alongside a plot PNG using pngquant."""
    import subprocess
    from pathlib import Path
    plot_path = Path(plot_path)
    thumb_path = plot_path.with_name(plot_path.stem + "_thumb" + plot_path.suffix)
    result = subprocess.run(
        ["pngquant", f"--quality={quality}", "--output", str(thumb_path), "--force", str(plot_path)],
        capture_output=True,
    )
    if result.returncode == 0:
        print(f"  Thumbnail saved → {thumb_path}")
    else:
        print(f"  pngquant not available; skipping thumbnail.")
