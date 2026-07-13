import { initMujocoViewer } from '/assets/js/mujoco-viewer.js';

await initMujocoViewer({
  xmlUrl:      '/double_pendulum/double_pendulum.xml',
  cameraPos:    [-1.59, 0.90, 1.16],
  cameraTarget: [-0.025, 0, -0.1],

  onModelReady: (mj, model, data) => {
    data.qpos[0] = 0.001;   // theta1: barely off vertical unstable equilibrium
    mj.mj_forward(model, data);
  },
});
