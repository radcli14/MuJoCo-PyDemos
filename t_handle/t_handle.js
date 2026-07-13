import { initMujocoViewer } from '/assets/js/mujoco-viewer.js';

const deg = Math.PI / 180;

await initMujocoViewer({
  xmlUrl:          '/t_handle/t_handle.xml',
  cameraPos:        [0.19, -0.17, 0.16],
  cameraTarget:     [0, 0.02, 0],
  autoRotate:       true,
  autoRotateSpeed:  2.0,

  onModelReady: (mj, model, data) => {
    data.qvel[3] = 0.05;   // wx: small perturbation to seed the instability
    data.qvel[4] = 5.0;    // wy: spin about intermediate axis
    mj.mj_forward(model, data);
  },

  onSceneReady: async ({ threeScene, THREE }) => {
    // Load DC Engineer logo and place it at the XML backdrop body position.
    // MuJoCo WASM cannot read the texture file, so we load it separately here.
    // Body pos="-0.21 0.21 -0.15", geom euler="90 45 0", size="0.42 0.42"
    const texture = await new Promise(resolve =>
      new THREE.TextureLoader().load('/images/dc-engineer-logo-transparent.png', resolve)
    );
    const geo = new THREE.PlaneGeometry(0.84, 0.84);
    const mat = new THREE.MeshBasicMaterial({ map: texture, transparent: true, side: THREE.DoubleSide });
    const mesh = new THREE.Mesh(geo, mat);
    mesh.position.set(-0.21, 0.21, -0.15);
    mesh.rotation.set(90 * deg, 45 * deg, 0, 'XYZ');
    threeScene.add(mesh);
  },
});
