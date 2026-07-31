import { initMujocoViewer } from '/assets/js/mujoco-viewer.js';

await initMujocoViewer({
  xmlUrl:      '/four_bar_linkage/four_bar_linkage.xml',
  cameraPos:    [2.0, -6.6, 3.4],
  cameraTarget: [2.0, 0.0, 1.0],

  onModelReady: (mj, model, data) => {
    const deg = Math.PI / 180;
    data.qpos[0] =  85.00 * deg;   // q0 = θ₀ (crank world angle)
    data.qpos[1] = -53.70 * deg;   // q1 = θ₁ − θ₀ (coupler relative to crank)
    data.qpos[2] =  42.72 * deg;   // q2 = −θ₂ (follower sign flip)
    mj.mj_forward(model, data);
  },
});
