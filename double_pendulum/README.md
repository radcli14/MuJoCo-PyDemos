---
layout: demo
permalink: /double_pendulum/
title: "Double Pendulum"
subtitle: "Deterministic chaos under lunar gravity"
description: >-
  Two rigid plexiglass links joined by cylindrical hinges, swinging in a
  vertical plane on the Moon. Starting from a near-inverted position, tiny
  differences in initial angle grow exponentially — a hallmark of chaos.
plot_image: /double_pendulum/double_pendulum_states.png
image: /double_pendulum/double_pendulum_states.png
tags: [chaos, rigid body, nonlinear dynamics]
specs:
  - { label: "Integrator",   value: "RK4, Δt = 1 ms" }
  - { label: "Duration",     value: "30 s" }
  - { label: "Link length",  value: "0.25 m each" }
  - { label: "Link mass",    value: "≈ 0.29 kg each (acrylic)" }
  - { label: "Gravity",      value: "−1.62 m/s² (Moon)" }
  - { label: "Initial θ₁",  value: "π − 0.05 rad (≈ 177°)" }
  - { label: "Initial θ₂",  value: "0.08 rad from link 1" }
source_dir: double_pendulum
files:
  - { label: "MJCF Model",    name: "double_pendulum.xml" }
  - { label: "Python Script", name: "double_pendulum_sim.py" }
---

The double pendulum is two rigid links connected end-to-end, each free to rotate about a frictionless cylindrical hinge. Despite its simple construction it is one of the most studied examples of **deterministic chaos**: the future trajectory is fully determined by the equations of motion, yet is practically unpredictable because tiny errors in the initial state grow exponentially.

## Physics

### Equations of Motion

Using generalised coordinates $\theta_1$ and $\theta_2$ (angles from the downward vertical, measured at the respective pivots), the Lagrangian $\mathcal{L} = T - V$ for two equal point masses $m$ on massless rods of length $l$ gives:

$$T = \tfrac{1}{2}ml^2\!\left(2\dot\theta_1^2 + \dot\theta_2^2 + 2\dot\theta_1\dot\theta_2\cos\Delta\right)$$

$$V = -mgl\!\left(2\cos\theta_1 + \cos\theta_2\right)$$

where $\Delta = \theta_1 - \theta_2$. The Euler–Lagrange equations yield:

$$(2\ddot\theta_1 + \ddot\theta_2\cos\Delta) + \dot\theta_2^2\sin\Delta + \frac{2g}{l}\sin\theta_1 = 0$$

$$(\ddot\theta_2 + \ddot\theta_1\cos\Delta) - \dot\theta_1^2\sin\Delta + \frac{g}{l}\sin\theta_2 = 0$$

MuJoCo solves the full distributed-mass (rigid rod) form automatically; the equations above are the classic point-mass reduction shown for reference.

### Lunar Gravity

Setting $g = 1.62\ \text{m/s}^2$ (Moon surface gravity, about $\frac{1}{6}$ of Earth's) lowers the natural frequency of each link to:

$$\omega_0 = \sqrt{\frac{g}{l}} \approx 2.5\ \text{rad/s}$$

The slower motion makes each tumble and swing visually easier to follow while preserving the same chaotic character.

### Sensitivity to Initial Conditions

The simulation begins with both links nearly inverted — $\theta_1 \approx \pi - 0.05\ \text{rad}$, $\theta_2 \approx 0.08\ \text{rad}$ from link 1 — near the unstable equilibrium at the top. The **Lyapunov exponent** of the double pendulum is positive, meaning trajectories that start $\varepsilon$ apart diverge as $e^{\lambda t}$. In practice, changing the starting angle by $10^{-6}$ rad produces a completely different trajectory within a few seconds.

The phase portraits of $(\theta_1,\,\theta_2)$ and $(\omega_1,\,\omega_2)$ show no closed orbits, confirming the system is not periodic and does not settle to a limit cycle.

## MJCF Model

The model uses `double_pendulum.xml` with two frictionless hinge joints constrained to the $y$-axis so motion is strictly planar:

```xml
<joint name="j1" type="hinge" axis="0 1 0"/>
<joint name="j2" type="hinge" axis="0 1 0"/>
```

The inertia tilt `euler="0 0 20"` technique used in the rattleback is intentionally absent here — the asymmetry driving chaos is purely in the geometry and initial conditions, not in any material property.

Each bar's mass and rotational inertia are computed automatically by MuJoCo from the box geometry and `density="1180"` kg/m³ (acrylic). Hinge pin and end-cap geoms use `density="0"` so they are purely visual.

A static door body behind the pendulum carries the DC Engineer shield as a texture. All geoms use `contype="0" conaffinity="0"`, so no collision detection runs.

## Running the Simulation

```bash
cd double_pendulum
python double_pendulum_sim.py
```

Outputs written to the same directory:

| File | Contents |
|---|---|
| `double_pendulum_sim.mp4` | Rendered video (1280 × 720, 60 fps) |
| `double_pendulum_states.png` | Six-panel state plots |

See [Setup & Installation](/setup/) for environment and dependency instructions.
