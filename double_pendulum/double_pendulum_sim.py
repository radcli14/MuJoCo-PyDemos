#!/usr/bin/env python3
"""
double_pendulum_sim.py — MuJoCo double pendulum under lunar gravity

Outputs (written to the same directory):
  double_pendulum_sim.mp4     rendered video  (1280 × 720, 60 fps)
  double_pendulum_states.png  six-panel state plots
"""

import sys
from pathlib import Path

# Make the repo-root common.py importable, then import it before mujoco
# (it selects the OpenGL backend on import).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import common                                                       # noqa: E402
from common import (Palette, style_ax, make_free_camera,            # noqa: E402
                    save_video, steps_per_frame, plt)

import numpy as np                                                  # noqa: E402
import mujoco                                                       # noqa: E402

# ── file paths ───────────────────────────────────────────────────────────────
HERE       = Path(__file__).parent
MODEL_PATH = HERE / "double_pendulum.xml"
VIDEO_PATH = HERE / "double_pendulum_sim.mp4"
PLOT_PATH  = HERE / "double_pendulum_states.png"

# ── simulation knobs ─────────────────────────────────────────────────────────
SIM_DURATION = 31.4159  # seconds
RENDER_FPS   = 60
# Portrait 9:16 to match standard mobile screens (e.g. 1080×1920).
RENDER_W     = 720
RENDER_H     = 1280

# Initial joint angles in radians 
THETA1_0 = 0.001
THETA2_0 = 0.0


# ── simulation ───────────────────────────────────────────────────────────────
def run_simulation():
    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
    data  = mujoco.MjData(model)
    mujoco.mj_resetData(model, data)

    data.qpos[0] = THETA1_0
    data.qpos[1] = THETA2_0
    mujoco.mj_forward(model, data)

    # World position of link 2's end cap is read from geom_xpos each step.
    end_cap_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, "end_cap")

    # Isometric view
    cam = make_free_camera(lookat=(-0.025, 0.0, -0.1), distance=2.2,
                           azimuth=300.0, elevation=-35)

    dt           = model.opt.timestep
    n_steps      = int(SIM_DURATION / dt)
    render_every = steps_per_frame(RENDER_FPS, dt)

    times  = np.empty(n_steps)
    theta1 = np.empty(n_steps)
    theta2 = np.empty(n_steps)
    omega1 = np.empty(n_steps)
    omega2 = np.empty(n_steps)
    tip    = np.empty((n_steps, 3))   # end-cap world position [x, y, z]
    frames = []

    print(f"Simulating {SIM_DURATION} s  "
          f"({n_steps:,} steps, Δt = {dt * 1e3:.1f} ms) …")

    renderer = mujoco.Renderer(model, height=RENDER_H, width=RENDER_W)
    for i in range(n_steps):
        times[i]  = data.time
        theta1[i] = data.qpos[0]
        theta2[i] = data.qpos[1]
        omega1[i] = data.qvel[0]
        omega2[i] = data.qvel[1]
        tip[i]    = data.geom_xpos[end_cap_id]

        if i % render_every == 0:
            renderer.update_scene(data, camera=cam)
            frames.append(renderer.render().copy())

        mujoco.mj_step(model, data)

    renderer.close()
    print(f"Captured {len(frames)} frames.")
    return times, theta1, theta2, omega1, omega2, tip, frames


# ── state plots ───────────────────────────────────────────────────────────────
def plot_states(times, theta1, theta2, omega1, omega2, tip):
    print(f"Saving plots  → {PLOT_PATH}")

    # Shared dark palette (see common.Palette)
    BG, TEXT, MUTED = Palette.BG, Palette.TEXT, Palette.MUTED
    RED, BLUE = Palette.RED, Palette.BLUE

    fig, axes = plt.subplots(2, 3, figsize=(15, 8))
    fig.patch.set_facecolor(BG)
    fig.suptitle(
        "Double Pendulum — MuJoCo Simulation (Moon Gravity, g = 1.62 m/s²)",
        fontsize=13, fontweight="bold", color=TEXT,
    )

    deg1 = np.degrees(theta1)
    deg2 = np.degrees(theta2)

    # ── Panel 1: θ₁ vs time ─────────────────────────────────────────────────
    ax = axes[0, 0]
    style_ax(ax)
    ax.plot(times, deg1, color=RED, lw=1.1)
    ax.set_title("θ₁ — Link 1 Angle", color=TEXT, fontsize=10)
    ax.set_xlabel("time (s)", color=MUTED, fontsize=9)
    ax.set_ylabel("degrees", color=MUTED, fontsize=9)

    # ── Panel 2: θ₂ vs time ─────────────────────────────────────────────────
    ax = axes[0, 1]
    style_ax(ax)
    ax.plot(times, deg2, color=BLUE, lw=1.1)
    ax.set_title("θ₂ — Link 2 Angle", color=TEXT, fontsize=10)
    ax.set_xlabel("time (s)", color=MUTED, fontsize=9)
    ax.set_ylabel("degrees", color=MUTED, fontsize=9)

    # ── Panel 3: end-cap position trace, coloured by time ─────────────────
    # The pendulum swings in the x-z plane (rotation about y), so the tip path
    # is its horizontal x vs vertical (world z); world y is the ~constant depth.
    ax = axes[0, 2]
    style_ax(ax)
    sc = ax.scatter(tip[:, 0], tip[:, 2], c=times, cmap="plasma", s=1, alpha=0.6, rasterized=True)
    cb = plt.colorbar(sc, ax=ax)
    cb.set_label("Time (s)", color=MUTED, fontsize=9)
    cb.ax.yaxis.set_tick_params(color=MUTED)
    plt.setp(cb.ax.yaxis.get_ticklabels(), color=MUTED)
    ax.set_title("End-Cap Position Trace", color=TEXT, fontsize=10)
    ax.set_xlabel("x (m)", color=MUTED, fontsize=9)
    ax.set_ylabel("z — vertical (m)", color=MUTED, fontsize=9)
    ax.set_aspect("equal", adjustable="datalim")

    # ── Panel 4: ω₁ vs time ─────────────────────────────────────────────────
    ax = axes[1, 0]
    style_ax(ax)
    ax.plot(times, omega1, color=RED, lw=1.1)
    ax.set_title("ω₁ — Link 1 Angular Velocity", color=TEXT, fontsize=10)
    ax.set_xlabel("time (s)", color=MUTED, fontsize=9)
    ax.set_ylabel("rad/s", color=MUTED, fontsize=9)

    # ── Panel 5: ω₂ vs time ─────────────────────────────────────────────────
    ax = axes[1, 1]
    style_ax(ax)
    ax.plot(times, omega2, color=BLUE, lw=1.1)
    ax.set_title("ω₂ — Link 2 Angular Velocity", color=TEXT, fontsize=10)
    ax.set_xlabel("time (s)", color=MUTED, fontsize=9)
    ax.set_ylabel("rad/s", color=MUTED, fontsize=9)

    # ── Panel 6: angular velocity phase portrait ω₁ vs ω₂ ──────────────────
    ax = axes[1, 2]
    style_ax(ax)
    sc2 = ax.scatter(omega1, omega2, c=times, cmap="viridis", s=1, alpha=0.6, rasterized=True)
    cb2 = plt.colorbar(sc2, ax=ax)
    cb2.set_label("Time (s)", color=MUTED, fontsize=9)
    cb2.ax.yaxis.set_tick_params(color=MUTED)
    plt.setp(cb2.ax.yaxis.get_ticklabels(), color=MUTED)
    ax.set_title("Angular Velocity Portrait  ω₁ vs ω₂", color=TEXT, fontsize=10)
    ax.set_xlabel("ω₁ (rad/s)", color=MUTED, fontsize=9)
    ax.set_ylabel("ω₂ (rad/s)", color=MUTED, fontsize=9)

    plt.tight_layout()
    fig.savefig(str(PLOT_PATH), dpi=150, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    print("  Plots saved.")


# ── entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    times, theta1, theta2, omega1, omega2, tip, frames = run_simulation()
    save_video(frames, VIDEO_PATH, RENDER_FPS)
    plot_states(times, theta1, theta2, omega1, omega2, tip)
