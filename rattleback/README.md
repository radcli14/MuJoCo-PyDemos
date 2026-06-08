---
layout: demo
permalink: /rattleback/
title: "Rattleback (Celtic Stone)"
subtitle: "Spontaneous spin reversal through inertia asymmetry"
description: >-
  A solid ellipsoid whose principal inertia axes are tilted 20° relative to
  its geometric symmetry axes. Spin in the wrong direction creates gyroscopic
  coupling that rocks, slows, and reverses the stone.
youtube: TjvpU8pFmmM
plot_image: /rattleback/rattleback_states.png
image: "https://img.youtube.com/vi/TjvpU8pFmmM/maxresdefault.jpg"
tags: [rigid body, angular momentum, gyroscopic coupling]
specs:
  - { label: "Integrator",    value: "RK4, Δt = 0.5 ms" }
  - { label: "Duration",      value: "24 s" }
  - { label: "Geometry",      value: "Ellipsoid 120 × 60 × 30 mm" }
  - { label: "Mass",          value: "0.5 kg" }
  - { label: "Inertia tilt",  value: "α = 20° about vertical" }
  - { label: "Initial spin",  value: "ωz = 5 rad/s (CCW)" }
  - { label: "Seed rock",     value: "ωx = 2 rad/s" }
source_dir: rattleback
files:
  - { label: "MJCF Model",    name: "rattleback.xml" }
  - { label: "Python Script", name: "rattleback_sim.py" }
---

The rattleback (also called a Celtic stone or *celt*) spontaneously reverses
its spin direction when placed on a flat surface and given an initial spin in
the *wrong* direction — without any apparent external cause.

## Physics

The reversal is driven by a **gyroscopic coupling** between the spin mode and
the rocking (pitch/roll) modes, created when the body's principal inertia axes
are tilted relative to its geometric axes.

### Geometry

The simulated body is a solid ellipsoid with semi-axes:

- $a = 0.12$ m (long axis)
- $b = 0.06$ m (wide axis)
- $c = 0.03$ m (vertical axis)

The body origin is placed at $z = c$ so the stone rests tangent to the ground
plane at $t = 0$.

### Inertia

Diagonal principal moments for a uniform solid ellipsoid of mass $m = 0.5$ kg:

$$I_x = \frac{m(b^2+c^2)}{5} = 4.50 \times 10^{-4}~\text{kg·m}^2$$

$$I_y = \frac{m(a^2+c^2)}{5} = 1.53 \times 10^{-3}~\text{kg·m}^2$$

$$I_z = \frac{m(a^2+b^2)}{5} = 1.80 \times 10^{-3}~\text{kg·m}^2$$

### Asymmetry

The inertia principal frame is rotated $\alpha = 20°$ about body $z$ relative
to the geometric axes, introducing an off-diagonal body-frame coupling:

$$I_{xy} = \frac{I_y - I_x}{2}\sin(2\alpha) \approx 3.47 \times 10^{-4}~\text{kg·m}^2$$

This $I_{xy}$ term causes a spin about $z$ to generate a gyroscopic torque in
the $x$–$y$ plane, which excites rocking. The rocking in turn torques the spin
toward zero and then past it — reversing the direction.

## MJCF Model

The inertia tilt is set in `rattleback.xml` with a single attribute:

```xml
<inertial pos="0 0 0" mass="0.5"
          diaginertia="4.5e-4 1.53e-3 1.8e-3"
          euler="0 0 20"/>
```

`euler="0 0 20"` rotates the principal-axes frame 20° about $z$ relative to
the body frame, creating the $I_{xy}$ coupling without altering the ellipsoid
shape. The axis cylinders attached to the body (red = $x$, green = $y$,
blue = $z$) visualize the geometric frame rotating with the stone.

## Initial Conditions

A pure vertical spin ($\omega_z \ne 0$, all other rates zero) is an *exact* equilibrium: the $I_{xy}$ coupling drives spin into roll/pitch only when angular momentum already has a transverse component.
A perfectly upright initial state would spin indefinitely without reversal.
The small seed roll rate $\omega_x = 2\ \text{rad/s}$ (`SEED_ROCK` in the script) plays the role of the inevitable imperfection when placing a real stone on a surface, allowing the gyroscopic instability to grow.

## Running the Simulation

```bash
cd rattleback
python rattleback_sim.py
```

Outputs written to the same directory:

| File | Contents |
|---|---|
| `rattleback_sim.mp4` | Rendered 3-D video (1280 × 720, 60 fps) |
| `rattleback_states.png` | Six-panel state plots |

See [Setup & Installation](/setup/) for environment and dependency instructions.
