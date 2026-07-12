import { initMujocoViewer } from '/assets/js/mujoco-viewer.js';

// Particle trail -- initialized in onSceneReady, used in onFrame.
let pGeo, pMat;
const particles = [];   // { mesh, birthTime }

await initMujocoViewer({
  xmlUrl: '/catcher/catcher.xml',
  cameraPos:       [4, -3, 2],
  cameraTarget:    [0, -1, 0.5],
  floorOffset:     -0.01,       // grid 1 cm below home plate surface
  autoRotate:      true,
  autoRotateSpeed: 2.0,

  onModelReady: (mj, model, data) => {
    // Free joint qvel: [vx, vy, vz, wx, wy, wz]
    data.qvel[1] = -40.27;   // vy: toward glove at ~90 mph
    data.qvel[2] =  -0.14;   // vz: slight downward to reach 2 ft glove height
    mj.mj_forward(model, data);
  },

  onSceneReady: async ({ threeScene, THREE, ESM }) => {
    const { GLTFLoader } = await import(`${ESM}/examples/jsm/loaders/GLTFLoader.js`);
    const gltf = await new Promise((resolve, reject) =>
      new GLTFLoader().load('/catcher/HomePlate.glb', resolve, undefined, reject)
    );
    threeScene.add(gltf.scene);

    // Particle geometry and material (shared across all particles for performance).
    pGeo = new THREE.SphereGeometry(0.02, 6, 4);
    pMat = new THREE.MeshBasicMaterial({ color: 0xcccccc });
  },

  onFrame: (mj, model, data, threeScene, THREE) => {
    if (!pGeo) return;
    const t = data.time;

    // Emit particle at ball world position (free joint: qpos[0..2] = xyz).
    const mesh = new THREE.Mesh(pGeo, pMat);
    mesh.position.set(data.qpos[0], data.qpos[1], data.qpos[2]);
    threeScene.add(mesh);
    particles.push({ mesh, birthTime: t });

    // Age particles: shrink linearly to zero over 1 s, then remove.
    for (let i = particles.length - 1; i >= 0; i--) {
      const age = t - particles[i].birthTime;
      if (age >= 1.0) {
        threeScene.remove(particles[i].mesh);
        particles.splice(i, 1);
      } else {
        particles[i].mesh.scale.setScalar(1.0 - age);
      }
    }
  },
});
