#!/usr/bin/env python3
import os
# EGL is the default headless backend; set before importing mujoco.
os.environ.setdefault("MUJOCO_GL", "egl")

from pathlib import Path
import numpy as np
import mujoco
import imageio
import matplotlib
matplotlib.use("Agg")   # non-interactive, safe for headless environments
import matplotlib.pyplot as plt

# ── file paths ──────────────────────────────────────────────────────────────
HERE       = Path(__file__).parent
MODEL_PATH = HERE / "rattleback.xml"
VIDEO_PATH = HERE / "rattleback_sim.mp4"
PLOT_PATH  = HERE / "rattleback_states.png"

# ── simulation knobs ────────────────────────────────────────────────────────
SIM_DURATION = 10.0    # seconds — long enough for at least one reversal
RENDER_FPS   = 60      # video frame rate
RENDER_W     = 1280    # video width  (px)
RENDER_H     = 720     # video height (px)

# Initial angular velocity about the world-z (vertical) axis in rad/s.
# Positive = CCW from above.  With the 20° inertia tilt in the XML this
# direction triggers spin reversal; negate if you want the stable direction.
INITIAL_SPIN = 5.0

# Tiny initial rocking-rate seed about world-x (roll), in rad/s.
# A perfectly upright pure vertical spin is an *exact* equilibrium: the
# off-diagonal inertia term I_xy couples roll<->pitch, but it does not couple a
# pure omega_z spin into anything, and with the CoM directly above the contact
# point gravity exerts no torque.  So without a perturbation the stone spins
# forever and the rattleback instability never gets excited.  A real rattleback
# is never placed perfectly level; this seed plays that role and lets the
# instability grow into rocking and spin reversal.  Set to 0.0 to reproduce the
# degenerate pure-spin case.
SEED_ROCK = 0.1


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

    # Stationary free camera aimed at the stone's resting position.  A tracking
    # camera would follow the body as it rocks and drifts, making the view shake;
    # a fixed lookat point keeps the camera perfectly still.
    cam = mujoco.MjvCamera()
    mujoco.mjv_defaultCamera(cam)
    cam.type        = mujoco.mjtCamera.mjCAMERA_FREE
    cam.lookat[:]   = (0.0, 0.0, 0.03)  # stone's initial position (world frame)
    cam.distance    = 0.55   # metres from lookat point
    cam.azimuth     = 135.0  # degrees CCW from -y axis
    cam.elevation   = -25.0  # degrees below horizontal

    dt           = model.opt.timestep
    n_steps      = int(SIM_DURATION / dt)
    render_every = max(1, round(1.0 / (RENDER_FPS * dt)))

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


# ── video export ─────────────────────────────────────────────────────────────
def save_video(frames):
    print(f"Saving video → {VIDEO_PATH}")
    writer = imageio.get_writer(
        str(VIDEO_PATH),
        fps=RENDER_FPS,
        format="ffmpeg",
        quality=8,
        macro_block_size=None,
    )
    for frame in frames:
        writer.append_data(frame)
    writer.close()
    print(f"  {len(frames)} frames written.")


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

    roll, pitch, _ = quat_to_euler_deg(quat)
    spin = angvel[:, 2]

    # Indices where the spin crosses zero (sign change).
    reversal_idxs = np.where(np.diff(np.sign(spin)))[0]

    fig, axes = plt.subplots(3, 2, figsize=(14, 11))
    fig.suptitle(
        "Rattleback (Celtic Stone) — MuJoCo Simulation",
        fontsize=14, fontweight="bold",
    )

    # 1 ── all three angular velocity components
    ax = axes[0, 0]
    ax.plot(times, angvel[:, 0], lw=1.0, label=r"$\omega_x$ roll rate")
    ax.plot(times, angvel[:, 1], lw=1.0, label=r"$\omega_y$ pitch rate")
    ax.plot(times, spin,         lw=1.8, color="tab:red",
            label=r"$\omega_z$ spin")
    ax.axhline(0, color="k", lw=0.5, ls="--")
    ax.set(xlabel="Time (s)", ylabel="rad/s", title="Angular Velocities")
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3)

    # 2 ── spin with reversal events highlighted
    ax = axes[0, 1]
    ax.plot(times, spin, lw=2.0, color="tab:red")
    ax.fill_between(times, spin, 0, where=(spin > 0),
                    alpha=0.20, color="tab:blue",   label="CCW (+)")
    ax.fill_between(times, spin, 0, where=(spin < 0),
                    alpha=0.20, color="tab:orange", label="CW  (−)")
    for idx in reversal_idxs:
        ax.axvline(times[idx], color="limegreen", lw=1.4, ls=":", alpha=0.9)
    ax.axhline(0, color="k", lw=0.7, ls="--")
    ax.set(xlabel="Time (s)", ylabel=r"$\omega_z$ (rad/s)",
           title="Spin about Vertical — Reversal Events  (green ┊)")
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3)

    # 3 ── CoM height (bouncing / rocking amplitude)
    ax = axes[1, 0]
    ax.plot(times, pos[:, 2] * 1e3, color="tab:green", lw=1.4)
    ax.set(xlabel="Time (s)", ylabel="Height (mm)",
           title="Centre-of-Mass Height")
    ax.grid(alpha=0.3)

    # 4 ── tilt angles
    ax = axes[1, 1]
    ax.plot(times, roll,  lw=1.2, label="Roll")
    ax.plot(times, pitch, lw=1.2, label="Pitch")
    ax.set(xlabel="Time (s)", ylabel="Angle (°)",
           title="Tilt Angles (Roll & Pitch)")
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3)

    # 5 ── horizontal position drift
    ax = axes[2, 0]
    ax.plot(times, pos[:, 0] * 1e2, lw=1.2, label="x")
    ax.plot(times, pos[:, 1] * 1e2, lw=1.2, label="y")
    ax.set(xlabel="Time (s)", ylabel="Position (cm)",
           title="Horizontal Drift")
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3)

    # 6 ── phase portrait: spin vs roll-rate, coloured by time
    ax = axes[2, 1]
    sc = ax.scatter(spin, angvel[:, 0], c=times, cmap="plasma",
                    s=2, alpha=0.7, rasterized=True)
    plt.colorbar(sc, ax=ax, label="Time (s)")
    ax.set(xlabel=r"$\omega_z$ — Spin (rad/s)",
           ylabel=r"$\omega_x$ — Roll rate (rad/s)",
           title="Phase Portrait: Roll Rate vs Spin")
    ax.grid(alpha=0.3)

    plt.tight_layout()
    fig.savefig(str(PLOT_PATH), dpi=150, bbox_inches="tight")
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
    save_video(frames)
    plot_states(times, pos, quat, angvel)
