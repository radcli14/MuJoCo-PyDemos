import { initMujocoViewer } from '/assets/js/mujoco-viewer.js';

// Unit conversions
// 60 ft = 18.288 m  (pitcher distance)
//  6 ft =  1.829 m  (release height)
//  3 ft =  0.914 m  (strike zone height above plate)
//  4 ft =  1.219 m  (catcher distance behind plate)
//  2 ft =  0.610 m  (glove height)
// 90 mph = 40.23 m/s
//
// Initial velocity to reach the strike zone despite gravity:
//   Solve y(t)=0 and z(t)=0.914 m with |v|=40.23 m/s.
//   Transit time t ≈ 0.455 s → vy ≈ -40.22 m/s, vz ≈ +0.22 m/s.

const XML = `\
<mujoco>
  <option timestep="0.002"/>
  <worldbody>
    <light pos="0 0 10" dir="0 0 -1" diffuse="1 1 1" specular="0.3 0.3 0.3"/>
    <geom name="floor" type="plane" size="20 20 .1" rgba=".5 .5 .5 1"/>
    <body name="ball" pos="0 18.288 1.829">
      <joint type="free"/>
      <!-- solref: tau=timestep (max stiffness), zeta=0.01 (nearly elastic) -->
      <geom type="sphere" size="0.037" rgba="0.95 0.95 0.95 1" mass="0.145" solref="0.002 0.01"/>
    </body>
    <!-- Catcher glove target: 4 ft behind plate, 2 ft up. No collision. -->
    <geom name="glove" type="sphere" size="0.12"
          pos="0 -1.219 0.610" rgba="0.2 0.8 0.3 1"
          contype="0" conaffinity="0"/>
  </worldbody>
</mujoco>`;

await initMujocoViewer({
  xml: XML,
  cameraPos:    [0, -6, 2],
  cameraTarget: [0, 9, 1],   // look up the middle of the pitch
  floorOffset:  -0.01,       // grid 1 cm below home plate surface

  onModelReady: (mj, model, data) => {
    // Free joint qvel: [vx, vy, vz, wx, wy, wz]
    data.qvel[1] = -40.22;   // vy: toward plate at ~90 mph
    data.qvel[2] =   0.22;   // vz: slight upward to arrive at 3 ft strike zone
    mj.mj_forward(model, data);
  },

  onSceneReady: async ({ threeScene, ESM }) => {
    const { GLTFLoader } = await import(`${ESM}/examples/jsm/loaders/GLTFLoader.js`);
    const gltf = await new Promise((resolve, reject) =>
      new GLTFLoader().load('/catcher/HomePlate.glb', resolve, undefined, reject)
    );
    threeScene.add(gltf.scene);
  },
});
