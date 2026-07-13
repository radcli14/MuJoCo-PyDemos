import { initMujocoViewer } from '/assets/js/mujoco-viewer.js';

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
});
