---
layout: page
title: "Catcher"
description: "A baseball pitched at 90 mph toward a simplified catcher — articulated torso, arm, and mitt — simulated live in the browser via MuJoCo WebAssembly."
permalink: /catcher/
sitemap: false
---

A baseball pitched at 90 mph toward a catcher modeled as a simplified torso, arm, and mitt — simulated live in the browser using the MuJoCo physics engine compiled to WebAssembly and rendered with Three.js.

<p id="mujoco-status" class="mujoco-status">Downloading MuJoCo WASM (~10 MB)&hellip;</p>

<div id="mujoco-canvas-container">
  <canvas id="mujoco-canvas"></canvas>
</div>

<div class="mujoco-controls">
  <button id="mujoco-reset" class="btn-mujoco-reset" disabled>Reset</button>
</div>

<script type="module" src="{{ '/catcher/catcher.js' | relative_url }}"></script>
