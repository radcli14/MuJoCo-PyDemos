const MUJOCO_CDN = 'https://cdn.jsdelivr.net/npm/@mujoco/mujoco@3.10.0';

const statusEl  = document.getElementById('mujoco-status');
const resetBtn  = document.getElementById('mujoco-reset');
const container = document.getElementById('mujoco-canvas-container');
const canvas    = document.getElementById('mujoco-canvas');

function setStatus(msg) {
  statusEl.textContent = msg;
  statusEl.style.display = 'block';
}

// Ball drops from 2 m, bounces on a 10x10 m floor.
const XML = `\
<mujoco>
  <option timestep="0.002"/>
  <worldbody>
    <light pos="0 0 5" dir="0 0 -1" diffuse="1 1 1" specular="0.3 0.3 0.3"/>
    <geom name="floor" type="plane" size="5 5 .1" rgba=".5 .5 .5 1"/>
    <body name="ball" pos="0 0 2">
      <joint type="free"/>
      <!-- solref damping ratio 0.01 (nearly undamped) gives ~e=0.95 restitution -->
      <geom type="sphere" size="0.15" rgba="0.9 0.2 0.2 1" mass="0.5" solref="0.005 0.01"/>
    </body>
  </worldbody>
</mujoco>`;

function makeCheckerTexture(THREE) {
  const sz = 512, tile = 64;
  const c = Object.assign(document.createElement('canvas'), { width: sz, height: sz });
  const ctx = c.getContext('2d');
  for (let row = 0; row < sz; row += tile)
    for (let col = 0; col < sz; col += tile) {
      ctx.fillStyle = ((row / tile + col / tile) % 2 === 0) ? '#2a3a4a' : '#1a2030';
      ctx.fillRect(col, row, tile, tile);
    }
  const tex = new THREE.CanvasTexture(c);
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
  tex.repeat.set(10, 10);
  return tex;
}

// Wait until the container has a non-zero layout size (important on mobile,
// where the element may be zero-height until the browser finishes layout).
function waitForSize(el) {
  return new Promise(resolve => {
    if (el.clientWidth > 0 && el.clientHeight > 0) { resolve(); return; }
    const ro = new ResizeObserver(() => {
      if (el.clientWidth > 0 && el.clientHeight > 0) { ro.disconnect(); resolve(); }
    });
    ro.observe(el);
  });
}

try {
  setStatus('Loading graphics library...');
  // esm.sh resolves bare specifiers ('three') server-side, so OrbitControls
  // works in any browser without an import map.
  const ESM = 'https://esm.sh/three@0.170.0';
  const [THREE, { OrbitControls }] = await Promise.all([
    import(`${ESM}`),
    import(`${ESM}/examples/jsm/controls/OrbitControls.js`),
  ]);

  // Check WebGL support before continuing.
  const testCtx = canvas.getContext('webgl2') || canvas.getContext('webgl');
  if (!testCtx) throw new Error('WebGL is not supported on this device or browser.');

  setStatus('Downloading physics engine (~10 MB)...');
  const { default: loadMujoco } = await import(`${MUJOCO_CDN}/mujoco.js`);
  const mj = await loadMujoco({ locateFile: f => `${MUJOCO_CDN}/${f}` });

  setStatus('Building physics model...');
  const model   = mj.MjModel.from_xml_string(XML);
  const data    = new mj.MjData(model);
  const mjScene = new mj.MjvScene(model, 1000);
  const option  = new mj.MjvOption();
  const camMj   = new mj.MjvCamera();
  const perturb = new mj.MjvPerturb();

  // Snapshot initial state so Reset can replay from the same starting point.
  const nq = model.nq, nv = model.nv;
  const qpos0 = Float64Array.from({ length: nq }, (_, i) => data.qpos[i]);
  const qvel0 = Float64Array.from({ length: nv }, (_, i) => data.qvel[i]);

  setStatus('Initializing renderer...');
  await waitForSize(container);

  // -- Three.js --
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
  renderer.setPixelRatio(window.devicePixelRatio);
  renderer.setSize(container.clientWidth, container.clientHeight);

  const threeScene = new THREE.Scene();
  threeScene.background = new THREE.Color(0x121e2d);

  const cam3 = new THREE.PerspectiveCamera(
    45, container.clientWidth / container.clientHeight, 0.1, 100
  );
  cam3.position.set(0, -5, 3);
  cam3.up.set(0, 0, 1); // MuJoCo is Z-up

  const controls = new OrbitControls(cam3, renderer.domElement);
  controls.target.set(0, 0, 0.5);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;
  controls.update();

  threeScene.add(new THREE.AmbientLight(0xffffff, 0.4));
  const sun = new THREE.DirectionalLight(0xffffff, 1.2);
  sun.position.set(3, -3, 6);
  threeScene.add(sun);

  const checkerTex = makeCheckerTexture(THREE);
  const meshPool   = []; // index matches MuJoCo scene.geoms index

  function getMesh(i, type, size, rgba) {
    if (meshPool[i]) return meshPool[i];

    const G = mj.mjtGeom;
    let geo;
    if      (type === G.mjGEOM_SPHERE.value)
      geo = new THREE.SphereGeometry(size[0], 32, 16);
    else if (type === G.mjGEOM_PLANE.value)
      geo = new THREE.PlaneGeometry(
        size[0] > 0 ? size[0] * 2 : 20,
        size[1] > 0 ? size[1] * 2 : 20
      );
    else if (type === G.mjGEOM_BOX.value)
      geo = new THREE.BoxGeometry(size[0]*2, size[1]*2, size[2]*2);
    else if (type === G.mjGEOM_CYLINDER.value)
      geo = new THREE.CylinderGeometry(size[0], size[0], size[1]*2, 32);
    else if (type === G.mjGEOM_CAPSULE.value)
      geo = new THREE.CapsuleGeometry(size[0], size[1]*2, 8, 16);
    else
      return null; // skip connector lines and other visual helpers

    const mat = (type === G.mjGEOM_PLANE.value)
      ? new THREE.MeshPhongMaterial({ map: checkerTex })
      : new THREE.MeshPhongMaterial({
          color: new THREE.Color(rgba[0], rgba[1], rgba[2]),
          opacity: rgba[3], transparent: rgba[3] < 0.99
        });

    const mesh = new THREE.Mesh(geo, mat);
    mesh.matrixAutoUpdate = false;
    threeScene.add(mesh);
    meshPool[i] = mesh;
    return mesh;
  }

  // MuJoCo provides a row-major 3x3 rotation + world position.
  // THREE.Matrix4.set() also takes row-major, so we map directly.
  function applyPose(mesh, g) {
    mesh.matrix.set(
      g.mat[0], g.mat[1], g.mat[2], g.pos[0],
      g.mat[3], g.mat[4], g.mat[5], g.pos[1],
      g.mat[6], g.mat[7], g.mat[8], g.pos[2],
      0, 0, 0, 1
    );
    mesh.matrixWorldNeedsUpdate = true;
  }

  new ResizeObserver(() => {
    const w = container.clientWidth, h = container.clientHeight;
    if (w === 0 || h === 0) return;
    cam3.aspect = w / h;
    cam3.updateProjectionMatrix();
    renderer.setSize(w, h);
  }).observe(container);

  resetBtn.addEventListener('click', () => {
    for (let i = 0; i < nq; i++) data.qpos[i] = qpos0[i];
    for (let i = 0; i < nv; i++) data.qvel[i] = qvel0[i];
    mj.mj_forward(model, data);
  });

  setStatus('Starting simulation...');
  let firstFrame = true;

  // -- Render loop --
  (function animate() {
    requestAnimationFrame(animate);

    // Advance physics ~1/60 s per displayed frame.
    const t0 = data.time;
    while (data.time - t0 < 1 / 60) mj.mj_step(model, data);

    mj.mjv_updateScene(
      model, data, option, perturb, camMj,
      mj.mjtCatBit.mjCAT_ALL.value, mjScene
    );

    const geoms = mjScene.geoms;
    const n = geoms.size();

    // Hide meshes for geom slots that didn't appear this frame.
    for (let i = n; i < meshPool.length; i++)
      if (meshPool[i]) meshPool[i].visible = false;

    for (let i = 0; i < n; i++) {
      const g    = geoms.get(i);
      const mesh = getMesh(i, g.type, g.size, g.rgba);
      if (mesh) { mesh.visible = true; applyPose(mesh, g); }
      g.delete(); // every C++ object returned by geoms.get() must be freed
    }
    geoms.delete();

    controls.update();
    renderer.render(threeScene, cam3);

    if (firstFrame) {
      firstFrame = false;
      statusEl.style.display = 'none';
      resetBtn.disabled = false;
    }
  })();

} catch (err) {
  setStatus(`Failed to load: ${err.message}`);
  statusEl.classList.add('mujoco-status--error');
}
