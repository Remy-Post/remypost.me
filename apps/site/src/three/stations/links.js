/**
 * The links station: a row of mechanical keycaps on an aluminium plate (keys.glb, nodes `key_<id>` and `plate`). Hover or
 * focus presses a key a little, a click or tap presses it fully and follows the link, and the key and the real link in the
 * text column light for each other (scene/hot.js). Each key travels 4 mm along its own local -Y.
 */
import { Group, Vector3 } from 'three';
import { links } from '../../content/site.js';
import { clearHot, getHot, onHot, setHot } from '../../scene/hot.js';
import { hitBox, normalise, pickId, prepare } from '../common.js';
import { RATE, chase, jump, settled, spring } from '../motion.js';

const TRAVEL = 0.004; // metres, full press
const HOVER = 0.38; // the share of it a hover presses

export function createLinksStation(ctx) {
  const group = new Group();
  const fit = new Group();
  group.add(fit);
  const fade = { value: 0 };
  const keys = []; // { id, node, rest, dir, press: spring, goal }
  const boxes = [];
  let hover = null;
  let pressed = null;
  let model = null;
  let body = null; // the model's root node: plate and keys together, which tips a little toward a key being pressed
  const tilt = { x: spring(0), z: spring(0), y: spring(0) };
  const station = { id: 'links', group, size: { w: 1, h: 0.4 }, ready: false, fade, boxes };

  const goalOf = (k) => (pressed === k.id ? 1 : hover === k.id || (getHot().kind === 'key' && getHot().ids.includes(k.id)) ? HOVER : 0);
  const off = onHot(() => ctx.wake());

  station.load = async (url) => {
    model = await ctx.loadModel(url);
    prepare(model, { fade, ...ctx.look });
    // The legends are extruded a fraction of a millimetre above the caps, finer than the shadow map can resolve: they
    // shadow themselves into speckle. They take no part in shadows (the caps and plate still do).
    model.traverse((m) => {
      if (m.isMesh && /^Legend/.test(m.material?.name ?? '')) m.castShadow = m.receiveShadow = false;
    });
    for (const l of links) {
      const node = model.getObjectByName(`key_${l.key}`);
      if (!node) continue;
      // Parent space, along the key's own tilted -Y: its scale (from quantization) must not enter the distance.
      keys.push({ id: l.key, node, rest: node.position.clone(), dir: new Vector3(0, -1, 0).applyQuaternion(node.quaternion), press: spring(0) });
    }
    body = model.children[0] ?? model;
    Object.assign(station.size, normalise(model, fit, 1));
    for (const k of keys) boxes.push(hitBox(model, k.node, k.id, 0.0015));
    fit.add(model);
    station.models = [model];
    return station;
  };

  /** The pointer is over key `id` (or nothing). */
  station.hover = (id) => {
    if (hover === id) return;
    hover = id;
    if (id) setHot('key', [id], 'stage');
    else clearHot('key', 'stage');
    ctx.wake();
  };
  station.down = (id) => {
    pressed = id;
    ctx.wake();
  };
  station.up = () => {
    pressed = null;
    ctx.wake();
  };
  /** Follow the real link of key `id`: the same anchor the text column has. */
  station.click = (id) => document.querySelector(`a[data-key="${id}"]`)?.click();
  station.pick = (ray) => pickId(ray, boxes);

  station.update = (dt) => {
    let moving = false;
    for (const k of keys) {
      const goal = goalOf(k);
      if (ctx.reduced()) jump(k.press, goal);
      else chase(k.press, goal, RATE.key, dt);
      if (!settled(k.press, goal, 1e-3)) moving = true;
      else jump(k.press, goal);
      k.node.position.copy(k.rest).addScaledVector(k.dir, TRAVEL * k.press.x);
    }
    // The plate answers: the side that is pressed dips, by well under a degree, and the whole plate sinks a hair.
    let tx = 0;
    let tz = 0;
    let ty = 0;
    for (const k of keys) {
      tx += k.press.x * (k.rest.z / 0.0123);
      tz -= k.press.x * (k.rest.x / 0.0286);
      ty += k.press.x;
    }
    const goals = [tx * 0.0035, tz * 0.0035, -ty * 0.00012];
    [tilt.x, tilt.z, tilt.y].forEach((s, i) => {
      if (ctx.reduced()) jump(s, goals[i]);
      else chase(s, goals[i], RATE.part, dt);
      if (!settled(s, goals[i], 1e-5)) moving = true;
    });
    if (body) {
      body.rotation.x = tilt.x.x;
      body.rotation.z = tilt.z.x;
      body.position.y = tilt.y.x;
    }
    return moving;
  };

  const cleanup = () => {
    for (const k of keys) k.node.position.copy(k.rest);
    if (body) body.rotation.set(0, 0, 0), (body.position.y = 0);
    for (const b of boxes) b.removeFromParent();
    boxes.length = 0;
  };
  station.dispose = () => {
    off();
    cleanup();
  };
  /** Let go of the model (the stage frees it): the station can be loaded again later, as new. */
  station.unload = () => {
    cleanup();
    keys.length = 0;
    body = null;
    hover = pressed = null;
    model?.removeFromParent();
    model = null;
    station.models = [];
    station.ready = false;
  };
  station.reset = () => {
    hover = pressed = null;
    for (const k of keys) jump(k.press, 0);
    for (const s of [tilt.x, tilt.z, tilt.y]) jump(s, 0);
  };
  return station;
}
