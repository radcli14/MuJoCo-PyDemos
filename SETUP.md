# Setup

Setup instructions for running the MuJoCo-PyDemos on **macOS (Apple Silicon)**.

## Requirements

- macOS on Apple Silicon (arm64)
- [Homebrew](https://brew.sh)
- Python **3.11 or 3.12** (see note below)

> **Why not the system Python?** macOS ships Python 3.9 (`/usr/bin/python3`,
> from the Command Line Tools). Recent `mujoco` releases no longer publish
> prebuilt wheels for Python 3.9, so `pip` falls back to compiling `mujoco`
> from source (which needs `MUJOCO_PATH`, CMake, and a C++ toolchain). Using a
> modern Python gets you a prebuilt wheel — no compiler, no env vars. The wheel
> bundles its own copy of the MuJoCo engine, so a separate MuJoCo.app install is
> *not* required.

## Install

```bash
# 1. Install a modern Python (one-time)
brew install python@3.12

# 2. From the repo root, create and activate a virtual environment
/opt/homebrew/bin/python3.12 -m venv .venv
source .venv/bin/activate

# 3. Upgrade pip, then install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Verify the install:

```bash
python -c "import mujoco; print('mujoco', mujoco.__version__)"
```

## Running a demo (macOS rendering backend)

The demo scripts default to `MUJOCO_GL=egl`, which is a **Linux** headless
backend. On macOS, offscreen rendering uses GLFW, so set `MUJOCO_GL=glfw`:

```bash
cd rattleback
MUJOCO_GL=glfw python rattleback_sim.py
```

This writes `rattleback_sim.mp4` (rendered video) and
`rattleback_states.png` (state plots) into the demo's directory.

| Platform                | `MUJOCO_GL` value     |
| ----------------------- | --------------------- |
| macOS                   | `glfw`                |
| Linux (GPU/CPU offscreen) | `egl` (script default) |
| Linux (CPU software)    | `osmesa`              |

## Troubleshooting

- **`RuntimeError: MUJOCO_PATH environment variable is not set`** during
  `pip install` — pip is trying to build `mujoco` from source because no wheel
  matches your Python. Use Python 3.11/3.12 (see above) instead of 3.9.
- **`RuntimeError: invalid value for environment variable MUJOCO_GL: egl`** —
  you're on macOS; use `MUJOCO_GL=glfw`.
