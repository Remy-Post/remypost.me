/**
 * The education station: two felt school pennants on wooden sticks in a weighted desk stand (pennants.glb: nodes
 * `pennant_lakehead`, `pennant_georgian`, each pivoting at its stick, and `stand`; the cloth carries a second UV set
 * whose x runs 0 at the stick to 1 at the tip).
 *
 * Scrolling through Education brings first one pennant forward, then the other, as its paragraph is read. The cloth
 * flutters with a travelling wave (a vertex shader) whose amplitude comes from scroll speed, pointer speed and the swap
 * itself and decays to rest; each pennant is a damped pendulum on its stick that the pointer nudges and can drag.
 */
import { Group, Quaternion, Vector3 } from 'three';
import { advance, hold, pendulum, push, release } from '../physics.js';
import { hitBox, normalise, pickId, prepare } from '../common.js';
import { RATE, chase, jump, settled, spring } from '../motion.js';

const FORWARD = 0.07; // metres the front pennant stands toward the camera
const BACK = 0.015; // and the one behind stands back
const LIFT = 0.012;
const WAVE_DECAY = 2.4; // per second: the flutter dies away
const WAVE_MAX = 0.42; // in the cloth's own units (about 6 cm at the tip)
const NAMES = ['lakehead', 'georgian'];

/**
 * A dragged angle with a soft limit: it follows the pointer closely near rest and resists more and more toward `max`
 * (radians) without ever stopping dead, so the cloth's tip stays inside the stage however far the pointer goes.
 */
const soft = (angle, max) => max * Math.tanh(angle / max);

const axisX = new Vector3(1, 0, 0);
const axisZ = new Vector3(0, 0, 1);
const qa = new Quaternion();
const qb = new Quaternion();

export function createEducationStation(ctx) {
  const group = new Group();
  const fit = new Group();
  group.add(fit);
  const fade = { value: 0 };
  const boxes = [];
  const pennants = {}; // name -> { node, rest, restQ, swing: { z, x }, front: spring, amp, uniforms }
  const station = { id: 'education', group, size: { w: 1, h: 1 }, ready: false, fade, boxes };
  let model = null;
  let phase = 0;
  let drag = null; // { name, x, y, zBase, xBase }
  let lastFront = [0, 0];

  const uniformsFor = (name) => (pennants[name] ??= {}).uniforms ?? (pennants[name].uniforms = { uAmp: { value: 0 }, uPhase: { value: 0 } });

  /** The cloth's vertex shader: a wave travelling from the stick to the tip, growing along the length. */
  const wave = (shader, material, mesh) => {
    const name = mesh.name.replace('_cloth', '');
    if (!mesh.name.endsWith('_cloth')) return;
    const u = uniformsFor(name);
    shader.uniforms.uAmp = u.uAmp;
    shader.uniforms.uPhase = u.uPhase;
    const fn = `
      uniform float uAmp;
      uniform float uPhase;
      #ifndef USE_UV1
      attribute vec2 uv1;
      #endif
      float clothWave(float s, float t) {
        float w = s * s * (0.35 + 0.65 * s);
        return uAmp * w * (sin(7.0 * s - uPhase) * 0.8 + sin(13.0 * s - uPhase * 1.7 + 1.3) * 0.2);
      }
      float clothSlope(float s, float t) {
        float e = 0.01;
        return (clothWave(s + e, t) - clothWave(s - e, t)) / (2.0 * e);
      }`;
    shader.vertexShader = shader.vertexShader
      .replace('#include <common>', `#include <common>\n${fn}`)
      // The normal leans with the slope of the wave along the length (cloth x), so the light moves over the folds.
      .replace('#include <beginnormal_vertex>', '#include <beginnormal_vertex>\nobjectNormal = normalize(objectNormal - vec3(clothSlope(uv1.x, 0.0) * 0.12, 0.0, 0.0));')
      .replace('#include <begin_vertex>', '#include <begin_vertex>\ntransformed.z += clothWave(uv1.x, 0.0);\ntransformed.y -= abs(clothWave(uv1.x, 0.0)) * 0.08;');
  };

  station.load = async (url) => {
    model = await ctx.loadModel(url);
    prepare(model, { fade, ...ctx.look, extend: wave });
    for (const name of NAMES) {
      const node = model.getObjectByName(`pennant_${name}`);
      if (!node) continue;
      const p = (pennants[name] ??= {});
      uniformsFor(name);
      Object.assign(p, {
        node,
        rest: node.position.clone(),
        restQ: node.quaternion.clone(),
        swing: { z: pendulum({ k: 70, c: 8.5, limit: 0.36 }), x: pendulum({ k: 70, c: 8.5, limit: 0.26 }) },
        front: spring(0),
        amp: 0,
      });
    }
    Object.assign(station.size, normalise(model, fit, 1));
    for (const name of NAMES) if (pennants[name]?.node) boxes.push(hitBox(model, pennants[name].node, name, 0.004));
    fit.add(model);
    station.models = [model];
    return station;
  };

  /** How far forward each pennant stands for step `s` (0 Lakehead, 1 Georgian, 2 neither). */
  const frontOf = (s) => ({ lakehead: 1 - smooth(s), georgian: 1 - smooth(Math.abs(s - 1)) });
  const smooth = (x) => {
    const k = Math.min(1, Math.max(0, x));
    return k * k * (3 - 2 * k);
  };

  let step = 0;
  let impulse = 0; // scroll and pointer speed since the last frame, folded into the flutter
  /** Called by the stage on every progress update and every pointer move. */
  station.setStep = (s) => {
    step = s;
    if (!ctx.reduced()) ctx.wake(); // under reduced motion the stage draws once, when the scrolling has stopped
  };
  /** A kick from the world: scroll speed (px/s) and pointer speed (px/s), both signed. */
  station.nudge = ({ scroll = 0, px = 0, py = 0 }) => {
    if (ctx.reduced()) return;
    const speed = Math.min(1, (Math.abs(scroll) * 0.00045 + Math.hypot(px, py) * 0.0003));
    impulse = Math.min(1.2, impulse + speed);
    for (const name of NAMES) {
      const p = pennants[name];
      if (!p?.node) continue;
      push(p.swing.z, -px * 0.0016 + scroll * 0.00012, 4);
      push(p.swing.x, py * 0.0012, 3);
    }
    ctx.wake();
  };

  station.hover = (name) => {
    ctx.cursor(!!name);
  };
  station.down = (name, e) => {
    const p = pennants[name];
    if (!p) return;
    drag = { name, x: e.clientX, y: e.clientY, zBase: p.swing.z.x, xBase: p.swing.x.x, t: e.timeStamp };
    p.swing.z.held = p.swing.x.held = true;
    impulse = Math.min(1.2, impulse + 0.35);
    ctx.wake();
  };
  station.move = (e) => {
    if (!drag) return;
    const p = pennants[drag.name];
    const dt = Math.max(1, e.timeStamp - drag.t) / 1000;
    drag.t = e.timeStamp;
    hold(p.swing.z, soft(drag.zBase - (e.clientX - drag.x) * 0.0042, 0.3), dt);
    hold(p.swing.x, soft(drag.xBase + (e.clientY - drag.y) * 0.0028, 0.2), dt);
    impulse = Math.min(1.2, impulse + 0.04);
    ctx.wake();
  };
  station.up = () => {
    if (!drag) return;
    const p = pennants[drag.name];
    release(p.swing.z);
    release(p.swing.x);
    if (ctx.reduced()) (p.swing.z.x = p.swing.x.x = 0), (p.swing.z.v = p.swing.x.v = 0);
    drag = null;
    ctx.wake();
  };
  station.pick = (ray) => pickId(ray, boxes);

  station.update = (dt) => {
    let moving = false;
    const goal = frontOf(step);
    for (const name of NAMES) {
      const p = pennants[name];
      if (!p?.node) continue;
      const g = goal[name];
      if (ctx.reduced()) jump(p.front, g);
      else chase(p.front, g, RATE.object, dt);
      if (!settled(p.front, g, 1e-3)) moving = true;
      else jump(p.front, g);
      // The swap itself sets the cloth fluttering a little.
      if (Math.abs(p.front.v) > 0.02) impulse = Math.min(1.2, impulse + Math.abs(p.front.v) * dt * 0.8);
      const sz = ctx.reduced() ? (jump(p.swing.z, 0), false) : advance(p.swing.z, dt);
      const sx = ctx.reduced() ? (jump(p.swing.x, 0), false) : advance(p.swing.x, dt);
      if (sz || sx) moving = true;
      const f = p.front.x;
      const other = 1 - Math.min(1, f);
      p.node.position.set(p.rest.x, p.rest.y + LIFT * f, p.rest.z + FORWARD * f - BACK * other * (step > 1.5 ? 0 : 1));
      qa.setFromAxisAngle(axisZ, p.swing.z.x);
      qb.setFromAxisAngle(axisX, p.swing.x.x);
      p.node.quaternion.copy(qa).multiply(qb).multiply(p.restQ);
    }
    // The flutter: the amplitude follows what has pushed it and falls away to nothing.
    const target = Math.min(1, impulse);
    impulse = 0;
    const total = NAMES.reduce((a, n) => a + (pennants[n]?.amp ?? 0), 0);
    for (const name of NAMES) {
      const p = pennants[name];
      if (!p?.node) continue;
      p.amp = Math.max(p.amp * Math.exp(-WAVE_DECAY * dt), target * (0.4 + 0.6 * Math.min(1, p.front.x + 0.4)));
      if (p.amp < 0.004) p.amp = 0;
      const u = p.uniforms;
      u.uAmp.value = ctx.reduced() ? 0 : Math.min(WAVE_MAX, p.amp * WAVE_MAX);
      if (p.amp > 0) moving = true;
    }
    if (total > 0) phase += dt * 9;
    for (const name of NAMES) if (pennants[name]?.uniforms) pennants[name].uniforms.uPhase.value = phase;
    return moving;
  };

  const cleanup = () => {
    for (const name of NAMES) {
      const p = pennants[name];
      if (!p?.node) continue;
      p.node.position.copy(p.rest);
      p.node.quaternion.copy(p.restQ);
    }
    for (const b of boxes) b.removeFromParent();
    boxes.length = 0;
  };
  station.dispose = cleanup;
  /** Let go of the model (the stage frees it): the station can be loaded again later, as new. */
  station.unload = () => {
    cleanup();
    for (const name of NAMES) if (pennants[name]) pennants[name].node = null;
    model?.removeFromParent();
    model = null;
    station.models = [];
    station.ready = false;
  };
  return station;
}
