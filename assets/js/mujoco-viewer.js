// General-purpose MuJoCo WASM viewer using Three.js.
// Call initMujocoViewer({ xml, cameraPos, cameraTarget, onSceneReady }) from
// a scene-specific script to spin up the physics engine and render loop.
// The DOM is expected to contain: #mujoco-status, #mujoco-reset,
// #mujoco-canvas-container, #mujoco-canvas.

const MUJOCO_CDN = 'https://cdn.jsdelivr.net/npm/@mujoco/mujoco@3.10.0';
const ESM        = 'https://esm.sh/three@0.170.0';

function makeCheckerTexture(THREE) {
  const sz = 512, tile = sz / 2; // 2x2 checker per texture; repeat is set per-plane in getMesh
  const c = Object.assign(document.createElement('canvas'), { width: sz, height: sz });
  const ctx = c.getContext('2d');
  for (let row = 0; row < sz; row += tile)
    for (let col = 0; col < sz; col += tile) {
      ctx.fillStyle = ((row / tile + col / tile) % 2 === 0) ? '#2a3a4a' : '#1a2030';
      ctx.fillRect(col, row, tile, tile);
    }
  const tex = new THREE.CanvasTexture(c);
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
  return tex;
}

// Defer until the element has a non-zero layout size (mobile layout may not
// be complete at script execution time).
function waitForSize(el) {
  return new Promise(resolve => {
    if (el.clientWidth > 0 && el.clientHeight > 0) { resolve(); return; }
    const ro = new ResizeObserver(() => {
      if (el.clientWidth > 0 && el.clientHeight > 0) { ro.disconnect(); resolve(); }
    });
    ro.observe(el);
  });
}

// Strip <asset> blocks and material attributes before passing XML to the WASM
// runtime, which cannot access local filesystem texture files.
// rgba fallback values on each geom provide browser colors after stripping.
export function prepareXmlForWasm(xml) {
  // Use indexOf/slice to remove <asset>...</asset> — avoids any regex multiline edge cases.
  let s = xml.indexOf('<asset'), e = xml.indexOf('</asset>');
  while (s !== -1 && e !== -1) {
    xml = xml.slice(0, s) + xml.slice(e + 8);
    s = xml.indexOf('<asset'); e = xml.indexOf('</asset>');
  }
  // Remove material="..." attributes; rgba fallback values on geoms are used instead.
  return xml.replace(/\s*material="[^"]*"/g, '');
}

// Parse the <asset> block of a MuJoCo XML to build a geomName → textureUrl map.
// baseUrl is used to resolve relative file paths (typically the xmlUrl).
// This must be called on the original XML before prepareXmlForWasm strips the asset block.
export function parseTextureMap(xml, baseUrl) {
  const doc = new DOMParser().parseFromString(xml, 'text/xml');
  const texFiles = {};
  for (const t of doc.querySelectorAll('texture[file]'))
    texFiles[t.getAttribute('name')] = new URL(t.getAttribute('file'), baseUrl).href;
  const matTex = {};
  for (const m of doc.querySelectorAll('material[texture]'))
    matTex[m.getAttribute('name')] = m.getAttribute('texture');
  const result = {};
  for (const g of doc.querySelectorAll('geom[material]')) {
    const texName = matTex[g.getAttribute('material')];
    const url = texName && texFiles[texName];
    if (url) result[g.getAttribute('name')] = url;
  }
  return result;
}

// Create a Three.js BufferGeometry for a given MuJoCo geom type.
// Reads authoritative dimensions from model.geom_size (not mjvGeom.size,
// which is unreliable for capsule/cylinder half-lengths).
export function createGeometry(type, G, THREE, model, objid) {
  if (type === G.mjGEOM_SPHERE.value)
    return new THREE.SphereGeometry(model.geom_size[objid * 3], 32, 16);

  if (type === G.mjGEOM_ELLIPSOID.value) {
    // Three.js has no EllipsoidGeometry; bake semi-axes into vertex positions.
    const geo = new THREE.SphereGeometry(1, 32, 16);
    geo.applyMatrix4(new THREE.Matrix4().makeScale(
      model.geom_size[objid * 3],
      model.geom_size[objid * 3 + 1],
      model.geom_size[objid * 3 + 2]
    ));
    return geo;
  }

  if (type === G.mjGEOM_PLANE.value) {
    const pw = model.geom_size[objid * 3]     > 0 ? model.geom_size[objid * 3]     * 2 : 20;
    const ph = model.geom_size[objid * 3 + 1] > 0 ? model.geom_size[objid * 3 + 1] * 2 : 20;
    return new THREE.PlaneGeometry(pw, ph);
  }

  if (type === G.mjGEOM_BOX.value)
    return new THREE.BoxGeometry(
      model.geom_size[objid * 3]     * 2,
      model.geom_size[objid * 3 + 1] * 2,
      model.geom_size[objid * 3 + 2] * 2
    );

  if (type === G.mjGEOM_CYLINDER.value) {
    const r  = model.geom_size[objid * 3];
    const hl = model.geom_size[objid * 3 + 1];
    const geo = new THREE.CylinderGeometry(r, r, hl * 2, 32);
    // Three.js CylinderGeometry is Y-axis; MuJoCo cylinder is Z-axis.
    geo.applyMatrix4(new THREE.Matrix4().makeRotationX(Math.PI / 2));
    return geo;
  }

  if (type === G.mjGEOM_CAPSULE.value) {
    const r  = model.geom_size[objid * 3];
    const hl = model.geom_size[objid * 3 + 1];
    const geo = new THREE.CapsuleGeometry(r, hl * 2, 8, 16);
    // Three.js CapsuleGeometry is Y-axis; MuJoCo capsule is Z-axis.
    geo.applyMatrix4(new THREE.Matrix4().makeRotationX(Math.PI / 2));
    return geo;
  }

  return null;
}

export async function initMujocoViewer({
  xml,
  xmlUrl,          // URL/path to an .xml file; fetched and resolved to a string before model load
  cameraPos    = [0, -5, 3],
  cameraTarget = [0, 0, 0.5],
  floorOffset  = 0,    // visual-only z offset applied to the floor plane mesh (m)
  onModelReady,        // (mj, model, data) — set initial conditions before state snapshot
  onSceneReady,        // async ({ threeScene, THREE, ESM }) — add scene-specific objects
  onFrame,             // (mj, model, data, threeScene, THREE) — called each render iteration
  autoRotate      = false,
  autoRotateSpeed = 2.0,
} = {}) {
  const statusEl  = document.getElementById('mujoco-status');
  const resetBtn  = document.getElementById('mujoco-reset');
  const container = document.getElementById('mujoco-canvas-container');
  const canvas    = document.getElementById('mujoco-canvas');

  function setStatus(msg) {
    statusEl.textContent = msg;
    statusEl.style.display = 'block';
  }

  try {
    setStatus('Loading graphics library...');
    const [THREE, { OrbitControls }] = await Promise.all([
      import(ESM),
      import(`${ESM}/examples/jsm/controls/OrbitControls.js`),
    ]);

    const testCtx = canvas.getContext('webgl2') || canvas.getContext('webgl');
    if (!testCtx) throw new Error('WebGL is not supported on this device or browser.');

    setStatus('Downloading physics engine (~10 MB)...');
    const { default: loadMujoco } = await import(`${MUJOCO_CDN}/mujoco.js`);
    const mj = await loadMujoco({ locateFile: f => `${MUJOCO_CDN}/${f}` });

    setStatus('Building physics model...');
    if (xmlUrl) {
      const resp = await fetch(xmlUrl);
      if (!resp.ok) throw new Error(`Failed to fetch model XML: ${resp.status}`);
      xml = await resp.text();
    }

    // Extract texture assignments from the asset block before stripping it.
    // Resolve xmlUrl to an absolute URL so relative texture paths in the XML can be resolved.
    const baseUrl = new URL(xmlUrl || location.href, location.href).href;
    const geomNameToTexUrl = parseTextureMap(xml, baseUrl);

    xml = prepareXmlForWasm(xml);
    const model   = mj.MjModel.from_xml_string(xml);
    const data    = new mj.MjData(model);
    const mjScene = new mj.MjvScene(model, 1000);
    const option  = new mj.MjvOption();
    const camMj   = new mj.MjvCamera();
    const perturb = new mj.MjvPerturb();

    // Allow the scene script to set initial positions/velocities before snapshot.
    if (onModelReady) onModelReady(mj, model, data);

    const nq = model.nq, nv = model.nv;
    const qpos0 = Float64Array.from({ length: nq }, (_, i) => data.qpos[i]);
    const qvel0 = Float64Array.from({ length: nv }, (_, i) => data.qvel[i]);

    setStatus('Initializing renderer...');
    await waitForSize(container);

    const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.setSize(container.clientWidth, container.clientHeight);

    const threeScene = new THREE.Scene();
    threeScene.background = new THREE.Color(0x121e2d);

    const cam3 = new THREE.PerspectiveCamera(
      45, container.clientWidth / container.clientHeight, 0.1, 500
    );
    cam3.position.set(...cameraPos);
    cam3.up.set(0, 0, 1); // MuJoCo is Z-up

    const controls = new OrbitControls(cam3, renderer.domElement);
    controls.target.set(...cameraTarget);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.autoRotate      = autoRotate;
    controls.autoRotateSpeed = autoRotateSpeed;
    controls.update();

    threeScene.add(new THREE.AmbientLight(0xffffff, 0.4));
    const sun = new THREE.DirectionalLight(0xffffff, 1.2);
    sun.position.set(3, -3, 6);
    threeScene.add(sun);

    if (onSceneReady) {
      setStatus('Loading scene assets...');
      await onSceneReady({ threeScene, THREE, ESM });
    }

    // Pre-load all geom textures and map model geom IDs to Three.js Texture objects.
    // Uses mj_name2id so any future model with <texture>/<material>/material= attributes
    // on its geoms gets textures automatically without per-model JS code.
    const geomTextures = new Map();
    const mjObjGeom = mj.mjtObj.mjOBJ_GEOM.value;
    const loader = new THREE.TextureLoader();
    await Promise.all(
      Object.entries(geomNameToTexUrl).map(([name, url]) => {
        const id = mj.mj_name2id(model, mjObjGeom, name);
        if (id < 0) return Promise.resolve();
        return new Promise(resolve =>
          loader.load(url, tex => { geomTextures.set(id, tex); resolve(); }, null, resolve)
        );
      })
    );

    const checkerTex = makeCheckerTexture(THREE);
    const meshPool   = [];
    const G          = mj.mjtGeom;

    function getMesh(i, g) {
      if (meshPool[i]) return meshPool[i];
      const type = g.type, rgba = g.rgba;
      const tex = geomTextures.get(g.objid);
      // Skip fully transparent geoms unless they carry a texture.
      if (rgba[3] === 0 && !tex) return null;
      const geo = createGeometry(type, G, THREE, model, g.objid);
      if (!geo) return null;

      let mat;
      if (tex) {
        mat = new THREE.MeshBasicMaterial({ map: tex, transparent: true, side: THREE.DoubleSide });
      } else if (type === G.mjGEOM_PLANE.value) {
        const pw = model.geom_size[g.objid * 3]     > 0 ? model.geom_size[g.objid * 3]     * 2 : 20;
        const ph = model.geom_size[g.objid * 3 + 1] > 0 ? model.geom_size[g.objid * 3 + 1] * 2 : 20;
        // 1 m per checker cell: texture has 2 cells (one light, one dark) per repeat
        checkerTex.repeat.set(pw / 2, ph / 2);
        checkerTex.needsUpdate = true;
        mat = new THREE.MeshPhongMaterial({ map: checkerTex });
      } else {
        mat = new THREE.MeshPhongMaterial({
          color: new THREE.Color(rgba[0], rgba[1], rgba[2]),
          opacity: rgba[3], transparent: rgba[3] < 0.99
        });
      }

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

    (function animate() {
      requestAnimationFrame(animate);

      const t0 = data.time;
      while (data.time - t0 < 1 / 60) mj.mj_step(model, data);

      mj.mjv_updateScene(
        model, data, option, perturb, camMj,
        mj.mjtCatBit.mjCAT_ALL.value, mjScene
      );

      const geoms = mjScene.geoms;
      const n = geoms.size();

      for (let i = n; i < meshPool.length; i++)
        if (meshPool[i]) meshPool[i].visible = false;

      for (let i = 0; i < n; i++) {
        const g    = geoms.get(i);
        const mesh = getMesh(i, g);
        if (mesh) {
          mesh.visible = true;
          applyPose(mesh, g);
          // Visual-only z offset for the floor plane (e.g. to sit below a surface mesh).
          // THREE.Matrix4 is column-major; elements[14] is the z translation.
          if (floorOffset !== 0 && g.type === G.mjGEOM_PLANE.value)
            mesh.matrix.elements[14] += floorOffset;
        }
        g.delete();
      }
      geoms.delete();

      if (onFrame) onFrame(mj, model, data, threeScene, THREE);
      controls.update();
      renderer.render(threeScene, cam3);

      if (firstFrame) {
        firstFrame = false;
        statusEl.style.display = 'none';
        resetBtn.disabled = false;
      }
    })();

  } catch (err) {
    statusEl.textContent = `Failed to load: ${err.message}`;
    statusEl.classList.add('mujoco-status--error');
    statusEl.style.display = 'block';
  }
}
