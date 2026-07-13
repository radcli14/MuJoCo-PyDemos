import { describe, it, expect } from 'vitest';
import * as THREE from 'three';
import { createGeometry, prepareXmlForWasm, parseTextureMap } from './mujoco-viewer.js';

// Minimal mjtGeom enum matching MuJoCo's mjtGeom values.
const G = {
  mjGEOM_PLANE:     { value: 0 },
  mjGEOM_SPHERE:    { value: 2 },
  mjGEOM_CAPSULE:   { value: 3 },
  mjGEOM_ELLIPSOID: { value: 4 },
  mjGEOM_CYLINDER:  { value: 5 },
  mjGEOM_BOX:       { value: 6 },
};

function makeModel(sizes) {
  return { geom_size: sizes };
}

describe('createGeometry', () => {
  it('sphere — returns SphereGeometry with correct radius', () => {
    const model = makeModel([0.05]);
    const geo = createGeometry(G.mjGEOM_SPHERE.value, G, THREE, model, 0);
    expect(geo).toBeInstanceOf(THREE.SphereGeometry);
    expect(geo.parameters.radius).toBeCloseTo(0.05);
  });

  it('plane — returns PlaneGeometry with correct width and height', () => {
    const model = makeModel([10, 5, 0.1]);
    const geo = createGeometry(G.mjGEOM_PLANE.value, G, THREE, model, 0);
    expect(geo).toBeInstanceOf(THREE.PlaneGeometry);
    expect(geo.parameters.width).toBeCloseTo(20);   // size[0] * 2
    expect(geo.parameters.height).toBeCloseTo(10);  // size[1] * 2
  });

  it('plane — uses 20 m default when size is zero', () => {
    const model = makeModel([0, 0, 0]);
    const geo = createGeometry(G.mjGEOM_PLANE.value, G, THREE, model, 0);
    expect(geo.parameters.width).toBeCloseTo(20);
    expect(geo.parameters.height).toBeCloseTo(20);
  });

  it('box — returns BoxGeometry with sides = 2 × geom_size', () => {
    const model = makeModel([0.1, 0.2, 0.3]);
    const geo = createGeometry(G.mjGEOM_BOX.value, G, THREE, model, 0);
    expect(geo).toBeInstanceOf(THREE.BoxGeometry);
    expect(geo.parameters.width).toBeCloseTo(0.2);
    expect(geo.parameters.height).toBeCloseTo(0.4);
    expect(geo.parameters.depth).toBeCloseTo(0.6);
  });

  it('cylinder — returns CylinderGeometry and is pre-rotated to Z-axis', () => {
    const r = 0.02, hl = 0.15;
    const model = makeModel([r, hl, 0]);
    const geo = createGeometry(G.mjGEOM_CYLINDER.value, G, THREE, model, 0);
    expect(geo).toBeInstanceOf(THREE.CylinderGeometry);
    // After 90° X-rotation the long axis is Z; bounding box max.z ≈ hl.
    geo.computeBoundingBox();
    expect(geo.boundingBox.max.z).toBeCloseTo(hl, 2);
    expect(geo.boundingBox.max.x).toBeCloseTo(r, 2);
  });

  it('capsule — returns CapsuleGeometry and is pre-rotated to Z-axis', () => {
    const r = 0.038, hl = 0.12;
    const model = makeModel([r, hl, 0]);
    const geo = createGeometry(G.mjGEOM_CAPSULE.value, G, THREE, model, 0);
    expect(geo).toBeInstanceOf(THREE.CapsuleGeometry);
    // After 90° X-rotation max.z ≈ hl + r (cylindrical half + hemisphere).
    geo.computeBoundingBox();
    expect(geo.boundingBox.max.z).toBeCloseTo(hl + r, 2);
    expect(geo.boundingBox.max.x).toBeCloseTo(r, 2);
  });

  it('ellipsoid — returns SphereGeometry scaled to semi-axes', () => {
    const a = 0.12, b = 0.06, c = 0.03;
    const model = makeModel([a, b, c]);
    const geo = createGeometry(G.mjGEOM_ELLIPSOID.value, G, THREE, model, 0);
    expect(geo).toBeInstanceOf(THREE.SphereGeometry);
    geo.computeBoundingBox();
    expect(geo.boundingBox.max.x).toBeCloseTo(a, 4);
    expect(geo.boundingBox.max.y).toBeCloseTo(b, 4);
    expect(geo.boundingBox.max.z).toBeCloseTo(c, 4);
  });

  it('unknown type — returns null', () => {
    const model = makeModel([1, 1, 1]);
    const geo = createGeometry(99, G, THREE, model, 0);
    expect(geo).toBeNull();
  });

  it('objid offset — reads from correct position in geom_size array', () => {
    // geom 0: [0.1, 0.2, 0.3], geom 1: [0.4, 0.5, 0.6]
    const model = makeModel([0.1, 0.2, 0.3, 0.4, 0.5, 0.6]);
    const geo0 = createGeometry(G.mjGEOM_SPHERE.value, G, THREE, model, 0);
    const geo1 = createGeometry(G.mjGEOM_SPHERE.value, G, THREE, model, 1);
    expect(geo0.parameters.radius).toBeCloseTo(0.1);
    expect(geo1.parameters.radius).toBeCloseTo(0.4);
  });
});

describe('prepareXmlForWasm', () => {
  const SAMPLE = `<mujoco>
  <asset>
    <texture name="t" type="2d" file="../images/logo.png"/>
    <material name="mat" texture="t"/>
  </asset>
  <worldbody>
    <geom type="sphere" size="0.1" material="mat" rgba="1 0 0 1"/>
  </worldbody>
</mujoco>`;

  it('strips the <asset> block entirely', () => {
    const out = prepareXmlForWasm(SAMPLE);
    expect(out).not.toContain('<asset');
    expect(out).not.toContain('</asset>');
    expect(out).not.toContain('logo.png');
  });

  it('removes material="..." attributes', () => {
    const out = prepareXmlForWasm(SAMPLE);
    expect(out).not.toContain('material=');
  });

  it('preserves rgba and other geom attributes', () => {
    const out = prepareXmlForWasm(SAMPLE);
    expect(out).toContain('rgba="1 0 0 1"');
    expect(out).toContain('type="sphere"');
  });

  it('handles XML with no asset block unchanged', () => {
    const plain = '<mujoco><worldbody><geom type="plane"/></worldbody></mujoco>';
    const out = prepareXmlForWasm(plain);
    expect(out).toContain('<geom type="plane"');
  });
});

describe('parseTextureMap', () => {
  const BASE = 'https://example.com/mymodel/mymodel.xml';

  const SAMPLE = `<mujoco>
  <asset>
    <texture name="shield_tex" type="2d" file="../images/logo.png"/>
    <material name="logo_mat" texture="shield_tex"/>
    <material name="other_mat" rgba="0.5 0.5 0.5 1"/>
  </asset>
  <worldbody>
    <geom name="backdrop" type="plane" material="logo_mat"/>
    <geom name="floor"    type="plane"/>
    <geom name="ball"     type="sphere" material="other_mat"/>
  </worldbody>
</mujoco>`;

  it('resolves the texture URL relative to the base URL', () => {
    const map = parseTextureMap(SAMPLE, BASE);
    expect(map['backdrop']).toBe('https://example.com/images/logo.png');
  });

  it('maps only geoms whose material references a texture with a file', () => {
    const map = parseTextureMap(SAMPLE, BASE);
    expect(Object.keys(map)).toEqual(['backdrop']);
  });

  it('ignores geoms with no material attribute', () => {
    const map = parseTextureMap(SAMPLE, BASE);
    expect(map['floor']).toBeUndefined();
  });

  it('ignores materials that have no texture attribute', () => {
    const map = parseTextureMap(SAMPLE, BASE);
    expect(map['ball']).toBeUndefined();
  });

  it('returns an empty object when there is no asset block', () => {
    const plain = '<mujoco><worldbody><geom name="g" type="plane"/></worldbody></mujoco>';
    expect(parseTextureMap(plain, BASE)).toEqual({});
  });
});
