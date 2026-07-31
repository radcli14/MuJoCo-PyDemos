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
MODEL_PATH = HERE / "four_bar_linkage.xml"
VIDEO_PATH = HERE / "four_bar_linkage_sim.mp4"
PLOT_PATH  = HERE / "four_bar_linkage_states.png"

# ── simulation knobs ─────────────────────────────────────────────────────────
SIM_DURATION = 20.0     # seconds
RENDER_FPS   = 60
RENDER_W     = 1280
RENDER_H     = 720

# Initial angles from the notebook (θ₀ drives crank; θ₁, θ₂ satisfy closure).
THETA0_0 = np.deg2rad(85.00)     # crank: world angle from +x
THETA1_0 = np.deg2rad(31.30)     # coupler: world angle from +x
THETA2_0 = np.deg2rad(-42.72)    # follower: world angle from +x (notebook sign)

# Link lengths (m) — used for position reconstruction and energy.
L = np.array([1.0, 2.0, 3.0, 4.0])   # l0 crank, l1 coupler, l2 follower, l3 ground
M = np.array([1.0, 2.0, 3.0])         # m0, m1, m2
I_rod = M * L[:3]**2 / 12             # thin-rod inertia about CG, per link
G = 9.81                               # m/s²


# ── MuJoCo ↔ notebook angle conversions ─────────────────────────────────────
# j0 (crank):   axis="0 -1 0", default +x → q0 = θ₀ directly.
# j1 (coupler): axis="0 -1 0", child of crank → q1 = θ₁ - θ₀ (relative).
# j2 (follower): axis="0 +1 0", default −x → q2 = -θ₂ (sign flip).
def notebook_to_mujoco(th0, th1, th2):
    return th0, th1 - th0, -th2

def mujoco_to_notebook(q0, q1, q2):
    return q0, q0 + q1, -q2


# ── simulation ───────────────────────────────────────────────────────────────
def run_simulation():
    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
    data  = mujoco.MjData(model)
    mujoco.mj_resetData(model, data)

    q0_0, q1_0, q2_0 = notebook_to_mujoco(THETA0_0, THETA1_0, THETA2_0)
    data.qpos[0] = q0_0
    data.qpos[1] = q1_0
    data.qpos[2] = q2_0
    mujoco.mj_forward(model, data)

    cam = make_free_camera(lookat=(2.0, 0.0, 1.0), distance=7.0,
                           azimuth=180.0, elevation=-20.0)

    dt           = model.opt.timestep
    n_steps      = int(SIM_DURATION / dt)
    render_every = steps_per_frame(RENDER_FPS, dt)

    times  = np.empty(n_steps)
    theta  = np.empty((n_steps, 3))   # θ₀, θ₁, θ₂ world angles (rad)
    omega  = np.empty((n_steps, 3))   # ω₀, ω₁, ω₂ world rates (rad/s)
    energy = np.empty((n_steps, 2))   # [KE, PE]
    frames = []

    print(f"Simulating {SIM_DURATION} s  "
          f"({n_steps:,} steps, Δt = {dt * 1e3:.1f} ms) …")

    renderer = mujoco.Renderer(model, height=RENDER_H, width=RENDER_W)
    for i in range(n_steps):
        times[i]    = data.time
        q0, q1, q2  = data.qpos[0], data.qpos[1], data.qpos[2]
        dq0, dq1, dq2 = data.qvel[0], data.qvel[1], data.qvel[2]
        th0, th1, th2 = mujoco_to_notebook(q0, q1, q2)
        theta[i]    = th0, th1, th2

        # World-frame angular rates: ω₀ = q̇₀, ω₁ = q̇₀ + q̇₁, ω₂ = −q̇₂
        omega[i]    = dq0, dq0 + dq1, -dq2

        # Mechanical energy (thin-rod model, Z-up gravity)
        z0 = 0.5 * L[0] * np.sin(th0)                          # crank CG height
        z1 = L[0]*np.sin(th0) + 0.5*L[1]*np.sin(th1)           # coupler CG height
        z2 = -0.5*L[2]*np.sin(th2)                             # follower CG height (from P₃)

        # Linear velocities of each CG (planar: x-z components only)
        vx0 = -0.5*L[0]*omega[i,0]*np.sin(th0)
        vz0 =  0.5*L[0]*omega[i,0]*np.cos(th0)
        vx1 = -L[0]*omega[i,0]*np.sin(th0) - 0.5*L[1]*omega[i,1]*np.sin(th1)
        vz1 =  L[0]*omega[i,0]*np.cos(th0) + 0.5*L[1]*omega[i,1]*np.cos(th1)
        vx2 =  0.5*L[2]*omega[i,2]*np.sin(th2)
        vz2 = -0.5*L[2]*omega[i,2]*np.cos(th2)

        KE = (0.5*M[0]*(vx0**2+vz0**2) + 0.5*I_rod[0]*omega[i,0]**2
            + 0.5*M[1]*(vx1**2+vz1**2) + 0.5*I_rod[1]*omega[i,1]**2
            + 0.5*M[2]*(vx2**2+vz2**2) + 0.5*I_rod[2]*omega[i,2]**2)
        PE = G * (M[0]*z0 + M[1]*z1 + M[2]*z2)
        energy[i] = KE, PE

        if i % render_every == 0:
            renderer.update_scene(data, camera=cam)
            frames.append(renderer.render().copy())

        mujoco.mj_step(model, data)

    renderer.close()
    print(f"Captured {len(frames)} frames.")
    return times, theta, omega, energy, frames


# ── plots ─────────────────────────────────────────────────────────────────────
def plot_states(times, theta, omega, energy):
    print(f"Saving plots  → {PLOT_PATH}")

    BG, TEXT, MUTED = Palette.BG, Palette.TEXT, Palette.MUTED
    RED, GREEN, BLUE = Palette.RED, Palette.GREEN, Palette.BLUE
    ORANGE = "#f59e0b"

    th_deg = np.degrees(theta)
    om_deg = np.degrees(omega)
    KE, PE = energy[:, 0], energy[:, 1]
    E_total = KE + PE

    # Coupler joint position P₂ = P₁ + l₁*(cos θ₁, sin θ₁)
    p2_x = L[0]*np.cos(theta[:,0]) + L[1]*np.cos(theta[:,1])
    p2_z = L[0]*np.sin(theta[:,0]) + L[1]*np.sin(theta[:,1])

    fig, axes = plt.subplots(2, 3, figsize=(16, 9))
    fig.patch.set_facecolor(BG)
    fig.suptitle("Four-Bar Linkage — MuJoCo Simulation",
                 fontsize=14, fontweight="bold", color=TEXT)

    def label(ax, xlabel, ylabel, title):
        ax.set_title(title, color=TEXT, fontsize=11)
        ax.set_xlabel(xlabel, color=MUTED, fontsize=9)
        ax.set_ylabel(ylabel, color=MUTED, fontsize=9)

    def legend(ax):
        ax.legend(fontsize=9, labelcolor=TEXT,
                  facecolor=Palette.CARD, edgecolor=Palette.EDGE)

    # 1 ── link angles
    ax = axes[0, 0]
    style_ax(ax)
    ax.plot(times, th_deg[:, 0], lw=1.5, color=RED,    label=r"$\theta_0$ crank")
    ax.plot(times, th_deg[:, 1], lw=1.5, color=GREEN,  label=r"$\theta_1$ coupler")
    ax.plot(times, th_deg[:, 2], lw=1.5, color=BLUE,   label=r"$\theta_2$ follower")
    ax.axhline(0, color=MUTED, lw=0.5, ls="--")
    label(ax, "Time (s)", "Angle (°)", "Link Angles")
    legend(ax)

    # 2 ── angular rates
    ax = axes[0, 1]
    style_ax(ax)
    ax.plot(times, om_deg[:, 0], lw=1.5, color=RED,   label=r"$\omega_0$ crank")
    ax.plot(times, om_deg[:, 1], lw=1.5, color=GREEN, label=r"$\omega_1$ coupler")
    ax.plot(times, om_deg[:, 2], lw=1.5, color=BLUE,  label=r"$\omega_2$ follower")
    ax.axhline(0, color=MUTED, lw=0.5, ls="--")
    label(ax, "Time (s)", "Rate (°/s)", "Angular Rates")
    legend(ax)

    # 3 ── coupler joint P₂ trajectory in the XZ plane
    ax = axes[0, 2]
    style_ax(ax)
    sc = ax.scatter(p2_x, p2_z, c=times, cmap="plasma",
                    s=2, alpha=0.8, rasterized=True)
    # Draw fixed pivot markers
    ax.plot([0, 4], [0, 0], "o", color=MUTED, ms=6, zorder=5)
    cb = plt.colorbar(sc, ax=ax)
    cb.set_label("Time (s)", color=MUTED, fontsize=9)
    cb.ax.yaxis.set_tick_params(color=MUTED)
    plt.setp(cb.ax.yaxis.get_ticklabels(), color=MUTED)
    ax.set_aspect("equal")
    label(ax, "x (m)", "z (m)", "Coupler Joint Trajectory")

    # 4 ── crank angle alone (shows oscillation pattern)
    ax = axes[1, 0]
    style_ax(ax)
    ax.plot(times, th_deg[:, 0], lw=1.8, color=RED)
    ax.fill_between(times, th_deg[:, 0], 0,
                    where=(th_deg[:, 0] > 0), alpha=0.2, color=RED)
    ax.axhline(0, color=MUTED, lw=0.5, ls="--")
    label(ax, "Time (s)", r"$\theta_0$ (°)", "Crank Angle")

    # 5 ── crank vs coupler phase portrait
    ax = axes[1, 1]
    style_ax(ax)
    sc2 = ax.scatter(th_deg[:, 0], th_deg[:, 1], c=times, cmap="viridis",
                     s=2, alpha=0.8, rasterized=True)
    cb2 = plt.colorbar(sc2, ax=ax)
    cb2.set_label("Time (s)", color=MUTED, fontsize=9)
    cb2.ax.yaxis.set_tick_params(color=MUTED)
    plt.setp(cb2.ax.yaxis.get_ticklabels(), color=MUTED)
    label(ax, r"$\theta_0$ — Crank (°)", r"$\theta_1$ — Coupler (°)",
          "Phase Portrait: Crank vs Coupler")

    # 6 ── total mechanical energy (should be conserved)
    ax = axes[1, 2]
    style_ax(ax)
    ax.plot(times, KE,      lw=1.2, color=RED,    label="KE")
    ax.plot(times, PE,      lw=1.2, color=BLUE,   label="PE")
    ax.plot(times, E_total, lw=2.0, color=GREEN,  label="KE + PE")
    label(ax, "Time (s)", "Energy (J)", "Mechanical Energy")
    legend(ax)

    plt.tight_layout()
    fig.savefig(str(PLOT_PATH), dpi=150, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    print("  Plots saved.")


# ── entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    times, theta, omega, energy, frames = run_simulation()
    save_video(frames, VIDEO_PATH, RENDER_FPS)
    plot_states(times, theta, omega, energy)
