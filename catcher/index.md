---
layout: page
title: "Catcher"
description: "MuJoCo physics running live in the browser via WebAssembly — a proof of concept for an in-browser robot simulation."
permalink: /catcher/
sitemap: false
---

A red ball dropping onto a checkered floor, simulated live in the browser using the MuJoCo physics engine compiled to WebAssembly and rendered with Three.js.

<p id="mujoco-status" class="mujoco-status">Downloading MuJoCo WASM (~10 MB)&hellip;</p>

<div id="mujoco-canvas-container">
  <canvas id="mujoco-canvas"></canvas>
</div>

<div class="mujoco-controls">
  <button id="mujoco-reset" class="btn-mujoco-reset" disabled>Reset</button>
</div>

<script type="module" src="{{ '/catcher/catcher.js' | relative_url }}"></script>
