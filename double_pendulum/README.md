---
layout: demo
permalink: /double_pendulum/
title: "Double Pendulum"
subtitle: "Deterministic chaos under lunar gravity"
description: >-
  Two rigid plexiglass links joined by cylindrical hinges, swinging in a
  vertical plane on the Moon. Starting from a near-inverted position, tiny
  differences in initial angle grow exponentially — a hallmark of chaos.
youtube: M5NC8nGev6o
youtube_short: true
date: 2026-06-08
plot_image: /double_pendulum/double_pendulum_states.png
plot_image_thumb: /double_pendulum/double_pendulum_states_thumb.png
image: "https://img.youtube.com/vi/M5NC8nGev6o/maxresdefault.jpg"
tags: [chaos, rigid body, nonlinear dynamics]
specs:
  - { label: "Integrator",   value: "RK4, Δt = 1 ms" }
  - { label: "Duration",     value: "31.4 s (π × 10 s)" }
  - { label: "Link length",  value: "0.25 m each" }
  - { label: "Link mass",    value: "≈ 0.29 kg each (acrylic)" }
  - { label: "Gravity",      value: "−1.62 m/s² (Moon)" }
  - { label: "Initial θ₁",  value: "0.001 rad (near inverted)" }
  - { label: "Initial θ₂",  value: "0.0 rad (aligned with link 1)" }
source_dir: double_pendulum
files:
  - { label: "MJCF Model",    name: "double_pendulum.xml" }
  - { label: "Python Script", name: "double_pendulum_sim.py" }
---

The double pendulum is two rigid links connected end-to-end, each free to rotate about a frictionless cylindrical hinge.
Despite its simple construction it is one of the most studied examples of **deterministic chaos**: the future trajectory is fully determined by the equations of motion, yet is practically unpredictable because tiny errors in the initial state grow exponentially.

## Physics

### Lunar Gravity

Setting $g = 1.62\ \text{m/s}^2$ (Moon surface gravity, roughly $\tfrac{1}{6}$ of Earth's) slows the natural frequency of each link, making each tumble and swing easier to follow in video while preserving the same chaotic character.

### Near-Inverted Start and Sensitivity to Initial Conditions

Both links start nearly upright — $\theta_1 = 0.001\ \text{rad}$ from the inverted position, $\theta_2 = 0$ — just off the unstable equilibrium at the top.
The Lyapunov exponent (the rate at which the separation between nearby trajectories grows over time) is positive for this system, meaning two paths that start within $\varepsilon$ of each other diverge exponentially: changing the starting angle by $10^{-6}\ \text{rad}$ is enough to produce a completely different trajectory within a few seconds.
The angular velocity phase portrait $(\omega_1, \omega_2)$ shows no closed orbits, confirming the system never settles into a periodic limit cycle.

## MJCF Model

Two frictionless hinge joints constrained to the $y$-axis enforce strictly planar motion:

```xml
<joint name="j1" type="hinge" axis="0 1 0"/>
<joint name="j2" type="hinge" axis="0 1 0"/>
```

Each bar's mass and rotational inertia are computed automatically by MuJoCo from the box geometry and `density="1180"` kg/m³ (acrylic).
Hinge pin and end-cap geoms use `density="0"` so they are purely visual.
All geoms use `contype="0" conaffinity="0"` — collision detection is disabled.

The inertia tilt `euler="0 0 20"` technique used in the rattleback is intentionally absent here — the asymmetry driving chaos is purely geometric and in the initial conditions, not in any material property.

The static door body behind the pendulum uses a `type="plane"` geom to carry the DC Engineer shield as a texture — MuJoCo 2D textures render correctly on plane geoms but not on box faces.

## Video

The video shows the two links — red for link 1 (attached to the pivot), blue for link 2 — starting nearly vertical and slowly tilting away from the top.
The first several seconds look almost periodic as the small initial angle drives low-amplitude oscillation, but within a few cycles the motion becomes visibly irregular and the links begin tumbling in seemingly random directions.
Lunar gravity keeps the swings slow enough that each individual tumble and reversal can be followed, but the long-term trajectory is entirely unpredictable.

## Plots

The six panels show the evolution of both links over the full 31.4-second run.

The **top row** contains θ₁ (red) and θ₂ (blue) in degrees, alongside the **end-cap position trace** — the x-z path of the tip of link 2 colored by time from purple (early) to yellow (late).
The angle histories begin as smooth near-sinusoidal oscillations and quickly become irregular large-amplitude excursions as chaos develops.
The position trace starts as a narrow arc near the top of the frame and progressively fills a wider region, showing the trajectory becoming space-filling rather than repeating.

The **bottom row** contains ω₁ and ω₂ (angular velocities of each link), and the **angular velocity portrait** (ω₁ vs ω₂) as a time-colored scatter.
The portrait contains no closed orbits — the trajectory does not revisit the same region in a regular pattern — which visually confirms the non-periodic, chaotic character of the motion.

## Running the Simulation

```bash
cd double_pendulum
python double_pendulum_sim.py
```

Outputs written to the same directory:

| File | Contents |
|---|---|
| `double_pendulum_sim.mp4` | Rendered video (720 × 1280 portrait, 60 fps) |
| `double_pendulum_states.png` | Six-panel state plots |

See [Setup & Installation](/setup/) for environment and dependency instructions.
