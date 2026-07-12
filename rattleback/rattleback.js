import { initMujocoViewer } from '/assets/js/mujoco-viewer.js';

await initMujocoViewer({
  xmlUrl:      '/rattleback/rattleback.xml',
  cameraPos:    [0.35, -0.35, 0.26],
  cameraTarget: [0, 0, 0.03],

  onModelReady: (mj, model, data) => {
    data.qvel[5] = 5.0;   // wz: initial CCW spin
    data.qvel[3] = 2.0;   // wx: seed rock to trigger reversal
    mj.mj_forward(model, data);
  },
});
