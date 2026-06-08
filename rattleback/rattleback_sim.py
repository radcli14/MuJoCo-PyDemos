#!/usr/bin/env python3
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

# ── file paths ──────────────────────────────────────────────────────────────
HERE       = Path(__file__).parent
MODEL_PATH = HERE / "rattleback.xml"
VIDEO_PATH = HERE / "rattleback_sim.mp4"
PLOT_PATH  = HERE / "rattleback_states.png"

# ── simulation knobs ────────────────────────────────────────────────────────
SIM_DURATION = 24.0    # seconds — long enough for at least one reversal
RENDER_FPS   = 60      # video frame rate
RENDER_W     = 1280    # video width  (px)
RENDER_H     = 720     # video height (px)

# rad/s CCW about world-z; this direction (with the 20° inertia tilt) triggers reversal.
INITIAL_SPIN = 5.0

# Small roll-rate seed to break the upright-spin equilibrium (see README).
SEED_ROCK = 2.0


# ── simulation ──────────────────────────────────────────────────────────────
def run_simulation():
    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
    data  = mujoco.MjData(model)
    mujoco.mj_resetData(model, data)

    # Freejoint qvel: [vx, vy, vz, wx, wy, wz] — all in the world frame.
    data.qvel[5] = INITIAL_SPIN
    data.qvel[3] = SEED_ROCK     # small roll-rate seed to break the upright-spin equilibrium

    # Resolve contacts and compute all derived quantities before the loop.
    mujoco.mj_forward(model, data)

    renderer = mujoco.Renderer(model, height=RENDER_H, width=RENDER_W)

    # Fixed lookat avoids camera shake as the stone rocks and drifts.
    cam = make_free_camera(lookat=(0.0, 0.0, 0.03), distance=0.55,
                           azimuth=135.0, elevation=-25.0)

    dt           = model.opt.timestep
    n_steps      = int(SIM_DURATION / dt)
    render_every = steps_per_frame(RENDER_FPS, dt)

    # Pre-allocate state arrays for performance.
    times  = np.empty(n_steps)
    pos    = np.empty((n_steps, 3))   # world-frame position  [x, y, z]
    quat   = np.empty((n_steps, 4))   # orientation quaternion [w, x, y, z]
    angvel = np.empty((n_steps, 3))   # world-frame ang. vel.  [wx, wy, wz]
    frames = []

    print(f"Simulating {SIM_DURATION} s  "
          f"({n_steps:,} steps, Δt = {dt * 1e3:.1f} ms) …")

    for i in range(n_steps):
        times[i]  = data.time
        pos[i]    = data.qpos[0:3]
        quat[i]   = data.qpos[3:7]   # MuJoCo quaternion: [w, x, y, z]
        angvel[i] = data.qvel[3:6]

        if i % render_every == 0:
            renderer.update_scene(data, camera=cam)
            frames.append(renderer.render().copy())

        mujoco.mj_step(model, data)

    renderer.close()
    print(f"Captured {len(frames)} frames.")
    return times, pos, quat, angvel, frames


# ── helpers ──────────────────────────────────────────────────────────────────
def quat_to_euler_deg(q):
    """ZYX Euler angles in degrees from (N, 4) quaternion array [w, x, y, z]."""
    w, x, y, z = q[:, 0], q[:, 1], q[:, 2], q[:, 3]
    roll  = np.degrees(np.arctan2(2 * (w * x + y * z),
                                  1 - 2 * (x**2 + y**2)))
    pitch = np.degrees(np.arcsin(np.clip(2 * (w * y - z * x), -1.0, 1.0)))
    yaw   = np.degrees(np.arctan2(2 * (w * z + x * y),
                                  1 - 2 * (y**2 + z**2)))
    return roll, pitch, yaw


# ── plots ────────────────────────────────────────────────────────────────────
def plot_states(times, pos, quat, angvel):
    print(f"Saving plots  → {PLOT_PATH}")

    # Shared dark palette (see common.Palette)
    BG, TEXT, MUTED = Palette.BG, Palette.TEXT, Palette.MUTED
    RED, BLUE, GREEN = Palette.RED, Palette.BLUE, Palette.GREEN
    ORANGE = "#f59e0b"

    def label(ax, xlabel, ylabel, title):
        ax.set_title(title, color=TEXT, fontsize=11)
        ax.set_xlabel(xlabel, color=MUTED, fontsize=9)
        ax.set_ylabel(ylabel, color=MUTED, fontsize=9)

    def legend(ax):
        ax.legend(fontsize=9, labelcolor=TEXT,
                  facecolor=Palette.CARD, edgecolor=Palette.EDGE)

    roll, pitch, _ = quat_to_euler_deg(quat)
    spin = angvel[:, 2]

    # Indices where the spin crosses zero (sign change).
    reversal_idxs = np.where(np.diff(np.sign(spin)))[0]

    fig, axes = plt.subplots(3, 2, figsize=(14, 11))
    fig.patch.set_facecolor(BG)
    fig.suptitle(
        "Rattleback (Celtic Stone) — MuJoCo Simulation",
        fontsize=14, fontweight="bold", color=TEXT,
    )

    # 1 ── all three angular velocity components
    ax = axes[0, 0]
    style_ax(ax)
    ax.plot(times, angvel[:, 0], lw=1.0, color=BLUE,  label=r"$\omega_x$ roll rate")
    ax.plot(times, angvel[:, 1], lw=1.0, color=GREEN, label=r"$\omega_y$ pitch rate")
    ax.plot(times, spin,         lw=1.8, color=RED,   label=r"$\omega_z$ spin")
    ax.axhline(0, color=MUTED, lw=0.5, ls="--")
    label(ax, "Time (s)", "rad/s", "Angular Velocities")
    legend(ax)

    # 2 ── spin with reversal events highlighted
    ax = axes[0, 1]
    style_ax(ax)
    ax.plot(times, spin, lw=2.0, color=RED)
    ax.fill_between(times, spin, 0, where=(spin > 0),
                    alpha=0.25, color=BLUE,   label="CCW (+)")
    ax.fill_between(times, spin, 0, where=(spin < 0),
                    alpha=0.25, color=ORANGE, label="CW  (−)")
    for idx in reversal_idxs:
        ax.axvline(times[idx], color=GREEN, lw=1.4, ls=":", alpha=0.9)
    ax.axhline(0, color=MUTED, lw=0.7, ls="--")
    label(ax, "Time (s)", r"$\omega_z$ (rad/s)",
          "Spin about Vertical — Reversal Events  (green ┊)")
    legend(ax)

    # 3 ── CoM height (bouncing / rocking amplitude)
    ax = axes[1, 0]
    style_ax(ax)
    ax.plot(times, pos[:, 2] * 1e3, color=GREEN, lw=1.4)
    label(ax, "Time (s)", "Height (mm)", "Centre-of-Mass Height")

    # 4 ── tilt angles
    ax = axes[1, 1]
    style_ax(ax)
    ax.plot(times, roll,  lw=1.2, color=RED,  label="Roll")
    ax.plot(times, pitch, lw=1.2, color=BLUE, label="Pitch")
    label(ax, "Time (s)", "Angle (°)", "Tilt Angles (Roll & Pitch)")
    legend(ax)

    # 5 ── horizontal position drift
    ax = axes[2, 0]
    style_ax(ax)
    ax.plot(times, pos[:, 0] * 1e2, lw=1.2, color=BLUE,  label="x")
    ax.plot(times, pos[:, 1] * 1e2, lw=1.2, color=GREEN, label="y")
    label(ax, "Time (s)", "Position (cm)", "Horizontal Drift")
    legend(ax)

    # 6 ── phase portrait: spin vs roll-rate, coloured by time
    ax = axes[2, 1]
    style_ax(ax)
    sc = ax.scatter(spin, angvel[:, 0], c=times, cmap="plasma",
                    s=2, alpha=0.7, rasterized=True)
    cb = plt.colorbar(sc, ax=ax)
    cb.set_label("Time (s)", color=MUTED, fontsize=9)
    cb.ax.yaxis.set_tick_params(color=MUTED)
    plt.setp(cb.ax.yaxis.get_ticklabels(), color=MUTED)
    label(ax, r"$\omega_z$ — Spin (rad/s)", r"$\omega_x$ — Roll rate (rad/s)",
          "Phase Portrait: Roll Rate vs Spin")

    plt.tight_layout()
    fig.savefig(str(PLOT_PATH), dpi=150, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    print("  Plots saved.")

    # Summary printout
    if len(reversal_idxs):
        t_rev = times[reversal_idxs]
        print(f"  Spin reversals at: {', '.join(f'{t:.2f} s' for t in t_rev)}")
    else:
        print("  No spin reversal detected — try extending SIM_DURATION "
              "or negating INITIAL_SPIN.")


# ── entry point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    times, pos, quat, angvel, frames = run_simulation()
    save_video(frames, VIDEO_PATH, RENDER_FPS)
    plot_states(times, pos, quat, angvel)
