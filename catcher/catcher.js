import { initMujocoViewer } from '/assets/js/mujoco-viewer.js';

// Unit conversions
// 60 ft = 18.288 m  (pitcher distance)
//  6 ft =  1.829 m  (release height)
//  4 ft =  1.219 m  (catcher Y distance behind plate)
//  2 ft =  0.610 m  (glove height)
// 90 mph = 40.23 m/s
//
// Velocity to reach glove (0, -1.219, 0.610) from (0, 18.288, 1.829):
//   Total ΔY = 19.507 m. Solve z(t)=0.610, |v|=40.23 m/s.
//   Transit time t ≈ 0.484 s → vy ≈ -40.27 m/s, vz ≈ -0.14 m/s.

const XML = `\
<mujoco>
  <option timestep="0.0005"/>
  <!-- tau=0.5ms (matches timestep, max contact stiffness), zeta=1 (critically damped, no bounce) -->
  <default>
    <geom solref="0.0005 1"/>
  </default>
  <worldbody>
    <light pos="0 0 10" dir="0 0 -1" diffuse="1 1 1" specular="0.3 0.3 0.3"/>
    <geom name="floor" type="plane" size="20 20 .1" rgba=".5 .5 .5 1"/>
    <body name="ball" pos="0 18.288 1.829">
      <joint type="free"/>
      <geom type="sphere" size="0.037" rgba="0.95 0.95 0.95 1" mass="0.145"/>
    </body>
    <!-- Catcher arm: shoulder(-0.147,-0.708,0.820) → elbow(-0.138,-0.973,0.679) → wrist(-0.12,-1.219,0.610) -->
    <!-- Shoulder ball joint: k=75 N·m/rad, c=15 N·m·s/rad (tau≈0.1 s, I≈0.75 kg·m²) -->
    <body name="upper_arm" pos="-0.147 -0.708 0.820">
      <joint name="shoulder" type="ball" stiffness="75" damping="15"/>
      <geom type="capsule" fromto="0 0 0  0.009 -0.265 -0.141"
            size="0.038" rgba="0.85 0.72 0.60 1" mass="2.0"/>
      <body name="forearm" pos="0.009 -0.265 -0.141">
        <!-- Elbow ball joint: k=17 N·m/rad, c=3.4 N·m·s/rad (tau≈0.1 s, I≈0.17 kg·m²) -->
        <joint name="elbow" type="ball" stiffness="17" damping="3.4"/>
        <geom type="capsule" fromto="0 0 0  0.018 -0.246 -0.069"
              size="0.030" rgba="0.85 0.72 0.60 1" mass="1.2"/>
        <!-- Mitt: thin leather disc, wrist hinge at left (-X) edge -->
        <body name="glove" pos="0.018 -0.246 -0.069">
          <!-- Wrist hinge: k=1.8 N·m/rad, c=0.36 N·m·s/rad (tau=0.1 s, I≈0.018 kg·m²) -->
          <joint name="wrist" type="hinge" axis="0 0 1" stiffness="1.8" damping="0.36"/>
          <geom name="glove" type="cylinder" size="0.12 0.00625"
                pos="0.12 0 0" euler="-90 0 0"
                rgba="0.80 0.40 0.10 1" mass="1"/>
        </body>
      </body>
    </body>
  </worldbody>
</mujoco>`;

// Particle trail — initialized in onSceneReady, used in onFrame.
let pGeo, pMat;
const particles = [];   // { mesh, birthTime }

await initMujocoViewer({
  xml: XML,
  cameraPos:    [0, -6, 2],
  cameraTarget: [0, 9, 1],   // look up the middle of the pitch
  floorOffset:  -0.01,       // grid 1 cm below home plate surface

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
