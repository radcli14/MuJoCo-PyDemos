#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import common                                                       # noqa: E402
from common import (Palette, style_ax, make_free_camera,            # noqa: E402
                    save_video, steps_per_frame, plt)

import numpy as np                                                  # noqa: E402
import mujoco                                                       # noqa: E402

# ── file paths ───────────────────────────────────────────────────────────────
HERE       = Path(__file__).parent
MODEL_PATH = HERE / "t_handle.xml"
VIDEO_PATH = HERE / "t_handle_sim.mp4"
PLOT_PATH  = HERE / "t_handle_states.png"

# ── simulation knobs ─────────────────────────────────────────────────────────
SIM_DURATION = 20.0
RENDER_FPS   = 60
RENDER_W     = 1280
RENDER_H     = 720

# rad/s about body-Y (intermediate principal axis); triggers Dzhanibekov flipping.
INITIAL_SPIN = 5.0
# Small perturbation about body-X to break the unstable equilibrium (see README).
SEED_PERTURB = 0.05


# ── simulation ───────────────────────────────────────────────────────────────
def run_simulation():
    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
    data  = mujoco.MjData(model)
    mujoco.mj_resetData(model, data)

    body_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "handle")

    # Rotate principal moments into the body frame (body_iquat maps body → principal).
    Ip = model.body_inertia[body_id].copy()
    qw, qx, qy, qz = model.body_iquat[body_id]
    R_bp = np.array([
        [1-2*(qy**2+qz**2), 2*(qx*qy-qw*qz),   2*(qx*qz+qw*qy)],
        [2*(qx*qy+qw*qz),   1-2*(qx**2+qz**2),  2*(qy*qz-qw*qx)],
        [2*(qx*qz-qw*qy),   2*(qy*qz+qw*qx),    1-2*(qx**2+qy**2)]
    ])
    I_body = np.diag(R_bp.T @ np.diag(Ip) @ R_bp)  # [Ixx, Iyy, Izz] in body frame
    print(f"Body-frame inertia  Ixx={I_body[0]:.4e}  Iyy={I_body[1]:.4e}  Izz={I_body[2]:.4e}  kg·m²")

    # qvel[3:6] for a free joint is angular velocity in the body frame.
    data.qvel[3] = SEED_PERTURB   # ωx — breaks the unstable equilibrium
    data.qvel[4] = INITIAL_SPIN   # ωy — intermediate axis
    mujoco.mj_forward(model, data)

    renderer = mujoco.Renderer(model, height=RENDER_H, width=RENDER_W)
    cam = make_free_camera(lookat=(0.0, 0.02, 0.0), distance=0.65,
                           azimuth=135.0, elevation=-30.0)

    dt           = model.opt.timestep
    n_steps      = int(SIM_DURATION / dt)
    render_every = steps_per_frame(RENDER_FPS, dt)

    times  = np.empty(n_steps)
    angvel = np.empty((n_steps, 3))   # body-frame angular velocity [ωx, ωy, ωz]
    frames = []

    print(f"Simulating {SIM_DURATION} s  "
          f"({n_steps:,} steps, Δt = {dt * 1e3:.1f} ms) …")

    for i in range(n_steps):
        times[i]  = data.time
        angvel[i] = data.qvel[3:6]

        if i % render_every == 0:
            renderer.update_scene(data, camera=cam)
            frames.append(renderer.render().copy())

        mujoco.mj_step(model, data)

    renderer.close()
    print(f"Captured {len(frames)} frames.")
    return times, angvel, frames, I_body


# ── plots ─────────────────────────────────────────────────────────────────────
def plot_states(times, angvel):
    print(f"Saving plots  → {PLOT_PATH}")

    BG, TEXT, MUTED = Palette.BG, Palette.TEXT, Palette.MUTED
    RED, BLUE, GREEN = Palette.RED, Palette.BLUE, Palette.GREEN

    spin_y = angvel[:, 1]
    flip_idxs = np.where(np.diff(np.sign(spin_y)))[0]

    fig = plt.figure(figsize=(12, 13))
    fig.patch.set_facecolor(BG)
    fig.suptitle("T-Handle — Intermediate-Axis Instability  (MuJoCo Simulation)",
                 fontsize=14, fontweight="bold", color=TEXT)
    gs = fig.add_gridspec(2, 1, height_ratios=[1, 1.4], hspace=0.4)

    # ── Top: all three angular velocity components with flip markers ──────────
    ax1 = fig.add_subplot(gs[0])
    style_ax(ax1)
    ax1.plot(times, angvel[:, 0], lw=1.0, color=BLUE,  label=r"$\omega_x$  (min. inertia)")
    ax1.plot(times, angvel[:, 1], lw=1.8, color=RED,   label=r"$\omega_y$  (intermediate)")
    ax1.plot(times, angvel[:, 2], lw=1.0, color=GREEN, label=r"$\omega_z$  (max. inertia)")
    ax1.axhline(0, color=MUTED, lw=0.5, ls="--")
    for idx in flip_idxs:
        ax1.axvline(times[idx], color=GREEN, lw=1.4, ls=":", alpha=0.9)
    ax1.set_title("Body-Frame Angular Velocities  (flip events: green ┊)",
                  color=TEXT, fontsize=11)
    ax1.set_xlabel("Time (s)", color=MUTED, fontsize=9)
    ax1.set_ylabel("rad/s", color=MUTED, fontsize=9)
    ax1.legend(fontsize=9, labelcolor=TEXT,
               facecolor=Palette.CARD, edgecolor=Palette.EDGE)

    # ── Bottom: 3-D phase portrait ────────────────────────────────────────────
    ax2 = fig.add_subplot(gs[1], projection="3d")
    ax2.set_facecolor(BG)
    for axis in [ax2.xaxis, ax2.yaxis, ax2.zaxis]:
        axis.pane.fill = True
        axis.pane.set_facecolor(Palette.CARD)
        axis.pane.set_edgecolor(Palette.EDGE)
        axis.set_tick_params(labelcolor=MUTED)
    ax2.grid(True, color=Palette.EDGE, alpha=0.25)

    sc = ax2.scatter(angvel[:, 0], angvel[:, 1], angvel[:, 2],
                     c=times, cmap="plasma", s=2, alpha=0.8, rasterized=True)
    cb = plt.colorbar(sc, ax=ax2, shrink=0.55, pad=0.1)
    cb.set_label("Time (s)", color=MUTED, fontsize=9)
    cb.ax.yaxis.set_tick_params(color=MUTED)
    plt.setp(cb.ax.yaxis.get_ticklabels(), color=MUTED)

    ax2.set_xlabel(r"$\omega_x$ (rad/s)", color=MUTED, fontsize=9, labelpad=8)
    ax2.set_ylabel(r"$\omega_y$ (rad/s)", color=MUTED, fontsize=9, labelpad=8)
    ax2.set_zlabel(r"$\omega_z$ (rad/s)", color=MUTED, fontsize=9, labelpad=8)
    ax2.set_title("3-D Phase Portrait", color=TEXT, fontsize=11)

    fig.savefig(str(PLOT_PATH), dpi=150, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    print("  Plots saved.")

    if len(flip_idxs):
        t_flip = times[flip_idxs]
        periods = np.diff(t_flip)
        print(f"  Flip events at: {', '.join(f'{t:.2f} s' for t in t_flip)}")
        if len(periods):
            print(f"  Mean flip period: {periods.mean():.2f} s")
    else:
        print("  No flip detected — try reducing SEED_PERTURB or extending SIM_DURATION.")


# ── entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    times, angvel, frames, I_body = run_simulation()
    save_video(frames, VIDEO_PATH, RENDER_FPS)
    plot_states(times, angvel)
