import { initMujocoViewer } from '/assets/js/mujoco-viewer.js';

// Ball drops from 2 m onto a home-plate floor.
const XML = `\
<mujoco>
  <option timestep="0.002"/>
  <worldbody>
    <light pos="0 0 5" dir="0 0 -1" diffuse="1 1 1" specular="0.3 0.3 0.3"/>
    <geom name="floor" type="plane" size="5 5 .1" rgba=".5 .5 .5 1"/>
    <body name="ball" pos="0 0 2">
      <joint type="free"/>
      <!-- solref: tau=timestep (max stiffness), zeta=0.01 (nearly elastic, e~0.95) -->
      <geom type="sphere" size="0.15" rgba="0.9 0.2 0.2 1" mass="0.5" solref="0.002 0.01"/>
    </body>
  </worldbody>
</mujoco>`;

await initMujocoViewer({
  xml: XML,
  floorOffset: -0.01,  // grid sits 1 cm below the home plate surface
  onSceneReady: async ({ threeScene, ESM }) => {
    const { GLTFLoader } = await import(`${ESM}/examples/jsm/loaders/GLTFLoader.js`);
    const gltf = await new Promise((resolve, reject) =>
      new GLTFLoader().load('/catcher/HomePlate.glb', resolve, undefined, reject)
    );
    threeScene.add(gltf.scene);
  },
});
