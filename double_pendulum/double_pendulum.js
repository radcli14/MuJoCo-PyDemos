import { initMujocoViewer } from '/assets/js/mujoco-viewer.js';

const deg = Math.PI / 180;

await initMujocoViewer({
  xmlUrl:      '/double_pendulum/double_pendulum.xml',
  cameraPos:    [-1.59, 0.90, 1.16],
  cameraTarget: [-0.025, 0, -0.1],

  onModelReady: (mj, model, data) => {
    data.qpos[0] = 0.001;   // theta1: barely off vertical unstable equilibrium
    mj.mj_forward(model, data);
  },

  onSceneReady: async ({ threeScene, THREE }) => {
    // Load DC Engineer logo and place it at the XML backdrop body position.
    // MuJoCo WASM cannot read the texture file, so we load it separately here.
    // Body pos="0 0 0.157", geom euler="90 180 0", size="0.628 0.628"
    const texture = await new Promise(resolve =>
      new THREE.TextureLoader().load('/images/dc-engineer-logo-transparent.png', resolve)
    );
    const geo = new THREE.PlaneGeometry(1.256, 1.256);
    const mat = new THREE.MeshBasicMaterial({ map: texture, transparent: true, side: THREE.DoubleSide });
    const mesh = new THREE.Mesh(geo, mat);
    mesh.position.set(0, 0, 0.157);
    mesh.rotation.set(90 * deg, 180 * deg, 0, 'XYZ');
    threeScene.add(mesh);
  },
});
