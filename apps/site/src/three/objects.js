/**
 * The small interaction each of the nine project objects has when it is the hero (on the home page and on its own
 * page), on top of drag-to-turn. Each is built from the nodes the model has and does nothing, quietly, when a node is
 * missing, so a model can be replaced by one that has more.
 *
 *   createBehaviour(name, model, ctx, { scale }) -> behaviour | null
 *
 * A behaviour offers: pick(ray) -> id|null (what the ray hits, by hit box), update(dt, { hero }) -> true while moving,
 * hover(id), down(id, e), move(e, id), up(id, e), click(id, e), activate() (Enter or Space on the focused stage),
 * drag(dx, dy, dt) (the object is being turned), nudge({ px, py }) (the pointer moving over the stage), reset() (the
 * object left the stage), extend(shader, material, mesh) (shader additions) and dispose(). Motion is damped and
 * settles; under reduced motion a change of state jumps to its end.
 */
import { AddEquation, Box3, CustomBlending, OneMinusSrcAlphaFactor, Quaternion, SrcAlphaFactor, Vector3 } from 'three';
import { advance, hold, pendulum, push, release } from './physics.js';
import { hitBox, pickId } from './common.js';
import { RATE, chase, clamp, jump, lerp, settled, smoothstep, spring } from './motion.js';

const qa = new Quaternion();
const qb = new Quaternion();
const v1 = new Vector3();
const X = new Vector3(1, 0, 0);
const Y = new Vector3(0, 1, 0);
const Z = new Vector3(0, 0, 1);

/** Rotate `node` by `q` about `pivot` (in the node's parent space), from its rest pose. */
function pivotRotate(node, rest, pivot, q) {
  node.quaternion.copy(q).multiply(rest.quat);
  node.position.copy(rest.pos).sub(pivot).applyQuaternion(q).add(pivot);
}

const restOf = (node) => ({ pos: node.position.clone(), quat: node.quaternion.clone(), scale: node.scale.clone() });
const putBack = (node, rest) => {
  node.position.copy(rest.pos);
  node.quaternion.copy(rest.quat);
  node.scale.copy(rest.scale);
};

/** The skeleton every behaviour shares: hit boxes, picking, cleanup, and a pointer-down point for drag gestures. */
function skeleton(model, ctx) {
  const boxes = [];
  const rests = [];
  const b = {
    boxes,
    box: (node, id, pad) => (boxes.push(hitBox(model, node, id, pad)), boxes[boxes.length - 1]),
    keep: (node) => (rests.push([node, restOf(node)]), rests[rests.length - 1][1]),
    pick: (ray) => pickId(ray, boxes),
    cursor: (id) => ctx.cursor(id !== null && id !== undefined),
    start: null,
    dispose() {
      for (const [node, rest] of rests) putBack(node, rest);
      for (const x of boxes) x.removeFromParent();
      boxes.length = 0;
    },
  };
  return b;
}

/** Wire up what every behaviour does the same way: remember where a press began. */
function pressable(b, { onDown, onMove, onUp } = {}) {
  b.down = (id, e) => {
    b.start = { x: e.clientX, y: e.clientY, id };
    onDown?.(id, e);
  };
  b.move = (e, id) => b.start && onMove?.(e, id, e.clientX - b.start.x, e.clientY - b.start.y);
  b.up = (id, e) => {
    onUp?.(id, e);
    b.start = null;
  };
}

// ── planner: the top page tears off, curling away; the next day shows ─────────
function planner(model, ctx) {
  const top = model.getObjectByName('sheet_top');
  if (!top?.isMesh) return null;
  const b = skeleton(model, ctx);
  const rest = b.keep(top);
  top.geometry.computeBoundingBox();
  const topY = top.geometry.boundingBox.max.y;
  const pivot = rest.pos.clone().add(new Vector3(0, topY * rest.scale.y, 0).applyQuaternion(rest.quat)); // the binding edge
  const uniforms = { uCurl: { value: 0 }, uTop: { value: topY } };
  const tear = spring(0);
  let torn = false;
  // Both sheets share one material (one printed atlas), so the top page gets its own to fade without fading the next.
  const shared = top.material;
  const material = shared.clone();
  // The fade the stage gives every material, then the curl, which only this page has.
  material.onBeforeCompile = (shader, renderer) => {
    shared.onBeforeCompile(shader, renderer);
    curl(shader);
  };
  material.customProgramCacheKey = () => 'extended:sheet_top';
  material.transparent = true;
  top.material = material;
  const sheetBox = b.box(top, 'sheet', 0.004);
  // The page's hit box flies away with it; a second one stays on the pad, so that a click there tears the page back on.
  top.updateMatrix();
  const padBox = sheetBox.clone();
  padBox.matrix.copy(top.matrix).multiply(sheetBox.matrix).decompose(padBox.position, padBox.quaternion, padBox.scale);
  top.parent.add(padBox);
  padBox.updateMatrixWorld(true);
  b.boxes.push(padBox);

  const curl = (shader) => {
    shader.uniforms.uCurl = uniforms.uCurl;
    shader.uniforms.uTop = uniforms.uTop;
    shader.vertexShader = shader.vertexShader
      .replace('#include <common>', '#include <common>\nuniform float uCurl;\nuniform float uTop;')
      .replace('#include <beginnormal_vertex>', `#include <beginnormal_vertex>
        if (abs(uCurl) > 1e-3) {
          float th0 = uCurl * (uTop - position.y);
          objectNormal = normalize(vec3(objectNormal.x, objectNormal.y * cos(th0) + objectNormal.z * sin(th0), -objectNormal.y * sin(th0) + objectNormal.z * cos(th0)));
        }`)
      .replace('#include <begin_vertex>', `#include <begin_vertex>
        if (abs(uCurl) > 1e-3) {
          float th = uCurl * (uTop - position.y);
          transformed.y = uTop - sin(th) / uCurl;
          transformed.z += (1.0 - cos(th)) / uCurl;
        }`);
  };

  const tearOff = () => {
    if (torn) return;
    torn = true;
    ctx.wake();
  };
  // A click (or Enter) tears the page off, and tears it back on: it flies back up and settles on the pad.
  const toggle = () => {
    torn = !torn;
    ctx.wake();
  };
  pressable(b, { onMove: (e, id, dx, dy) => dy < -26 && tearOff() });
  b.swipe = (id, dx, dy) => dy < -6 && tearOff(); // a swipe up on a touch screen is the page scrolling: it tears too
  b.hover = (id) => b.cursor(id);
  b.click = toggle;
  b.activate = toggle;
  b.reset = () => {
    torn = false;
    jump(tear, 0);
    apply(0);
  };

  const apply = (a) => {
    const peel = smoothstep(0, 0.5, a);
    const fall = smoothstep(0.4, 1, a);
    uniforms.uCurl.value = 1.35 * smoothstep(0, 0.6, a);
    qa.setFromAxisAngle(X, 0.25 * peel + 1.1 * fall);
    qb.setFromAxisAngle(Z, 0.5 * fall);
    qa.multiply(qb);
    pivotRotate(top, rest, pivot, qa);
    top.position.add(v1.set(0.012 * fall, -0.17 * fall * fall, 0.03 * peel + 0.16 * fall));
    material.opacity = 1 - smoothstep(0.62, 0.98, a);
    top.visible = a < 0.995;
  };
  b.update = (dt) => {
    const goal = torn ? 1 : 0;
    if (ctx.reduced()) jump(tear, goal);
    else chase(tear, goal, RATE.camera, dt);
    const moving = !settled(tear, goal, 1e-3);
    if (!moving) jump(tear, goal);
    apply(tear.x);
    return moving;
  };
  const dispose = b.dispose;
  b.dispose = () => {
    b.reset();
    top.material = shared;
    material.dispose();
    top.visible = true;
    dispose();
  };
  return b;
}

// ── filebox: hover lifts a folder, a click pulls the document up ──────────────
function filebox(model, ctx) {
  const doc = model.getObjectByName('document');
  const folders = [];
  for (let i = 1; i <= 7; i++) {
    const node = model.getObjectByName(`folder_${i}`);
    if (node) folders.push({ id: `folder_${i}`, node, rest: null, lift: spring(0) });
  }
  if (!doc && !folders.length) return null;
  const b = skeleton(model, ctx);
  for (const f of folders) {
    f.rest = b.keep(f.node);
    // The tab is what is seen above the box; it is also what the pointer finds.
    const tab = model.getObjectByName(`${f.id}_glass`) ?? f.node;
    b.box(tab, f.id, 0.008);
  }
  const docRest = doc ? b.keep(doc) : null;
  if (doc) b.box(doc, 'document', 0.006);
  const out = spring(0);
  let up = false;
  let hover = null;

  b.hover = (id) => {
    hover = id;
    b.cursor(id);
    ctx.wake();
  };
  const toggle = () => {
    up = !up;
    ctx.wake();
  };
  b.click = (id) => (doc || folders.length) && toggle();
  b.activate = toggle;
  b.reset = () => {
    up = false;
    jump(out, 0);
    for (const f of folders) jump(f.lift, 0);
    pose();
  };
  const pose = () => {
    for (const f of folders) {
      // Lift first, then tip, so the folder never goes through the front wall of the box.
      const l = f.lift.x;
      f.node.position.copy(f.rest.pos).y += 0.024 * l;
      qa.setFromAxisAngle(X, 0.1 * smoothstep(0.35, 1, l));
      f.node.quaternion.copy(qa).multiply(f.rest.quat);
    }
    if (doc) {
      doc.position.copy(docRest.pos).y += 0.115 * out.x;
      doc.position.z += 0.012 * out.x;
      qa.setFromAxisAngle(X, -0.12 * Math.sin(Math.PI * Math.min(1, out.x)));
      doc.quaternion.copy(qa).multiply(docRest.quat);
    }
  };
  b.update = (dt) => {
    let moving = false;
    for (const f of folders) {
      const g = hover === f.id ? 1 : 0;
      if (ctx.reduced()) jump(f.lift, g);
      else chase(f.lift, g, RATE.part, dt);
      if (!settled(f.lift, g, 1e-3)) moving = true;
    }
    const g = up ? 1 : 0;
    if (ctx.reduced()) jump(out, g);
    else chase(out, g, RATE.ring, dt);
    if (!settled(out, g, 1e-3)) moving = true;
    pose();
    return moving;
  };
  return b;
}

// ── pricetag: the tag rocks in its holder from the pointer and from a drag ────
function pricetag(model, ctx) {
  const card = model.getObjectByName('card');
  const mesh = model.getObjectByName('card_paper');
  if (!card || !mesh) return null;
  const b = skeleton(model, ctx);
  const rest = b.keep(card);
  // The skin allows about 8 degrees either way before the card leaves its holder.
  const side = pendulum({ k: 46, c: 7, limit: 0.13 });
  const fore = pendulum({ k: 46, c: 7, limit: 0.14 });
  b.box(mesh, 'tag', 0.006);
  let held = null;

  pressable(b, {
    onDown: (id, e) => {
      held = { x: e.clientX, y: e.clientY, sideBase: side.x, foreBase: fore.x, t: e.timeStamp };
      side.held = fore.held = true;
    },
    onMove: (e, id, dx, dy) => {
      if (!held) return;
      const dt = Math.max(1, e.timeStamp - held.t) / 1000;
      held.t = e.timeStamp;
      hold(side, held.sideBase + dx * 0.0016, dt);
      hold(fore, held.foreBase + dy * 0.0012, dt);
      ctx.wake();
    },
    onUp: () => {
      release(side);
      release(fore);
      if (ctx.reduced()) (side.x = fore.x = 0), (side.v = fore.v = 0);
      held = null;
    },
  });
  b.hover = (id) => b.cursor(id);
  b.click = () => (push(side, 0.9), ctx.wake());
  b.activate = () => (push(side, 0.9), ctx.wake());
  b.nudge = ({ px = 0, py = 0 }) => {
    if (ctx.reduced()) return;
    push(side, px * 0.00018, 0.9);
    push(fore, py * 0.0001, 0.6);
    ctx.wake();
  };
  b.drag = (dx) => {
    if (!ctx.reduced()) push(side, dx * 0.008, 0.9);
  };
  b.reset = () => {
    for (const p of [side, fore]) (p.x = 0), (p.v = 0), (p.held = false);
    pose();
  };
  const pose = () => {
    qa.setFromAxisAngle(Z, side.x);
    qb.setFromAxisAngle(X, fore.x);
    card.quaternion.copy(qa).multiply(qb).multiply(rest.quat);
  };
  b.update = (dt) => {
    const moving = ctx.reduced() ? false : [advance(side, dt), advance(fore, dt)].some(Boolean);
    pose();
    return moving;
  };
  return b;
}

// ── textbooks: the flask sloshes with drag speed, a click nudges the top book ─
function textbooks(model, ctx) {
  const top = model.getObjectByName('book_3') ?? model.getObjectByName('book_top');
  const flask = model.getObjectByName('flask');
  const liquid = model.getObjectByName('liquid');
  if (!top && !flask) return null;
  const b = skeleton(model, ctx);
  const topRest = top ? b.keep(top) : null;
  const slosh = { x: pendulum({ k: 38, c: 8.2, limit: 0.6 }), z: pendulum({ k: 38, c: 8.2, limit: 0.6 }) };
  const shove = pendulum({ k: 70, c: 6.5, limit: 0.5 }); // the top book's slide, as an angle-like coordinate
  const uniforms = { uTiltX: { value: 0 }, uTiltZ: { value: 0 } };
  if (flask) b.box(flask, 'flask', 0.006);
  if (top) b.box(top, 'book', 0.004);

  b.extend = (shader, x, m) => {
    if (m !== liquid) return;
    shader.uniforms.uTiltX = uniforms.uTiltX;
    shader.uniforms.uTiltZ = uniforms.uTiltZ;
    // The surface (the vertices above the middle) tilts: the liquid leans away from the push and swings back.
    shader.vertexShader = shader.vertexShader
      .replace('#include <common>', '#include <common>\nuniform float uTiltX;\nuniform float uTiltZ;')
      .replace('#include <begin_vertex>', '#include <begin_vertex>\ntransformed.y += step(0.0, position.y) * (uTiltX * position.x + uTiltZ * position.z);');
  };
  const kick = (vx, vz, max = 4) => {
    if (ctx.reduced()) return;
    push(slosh.x, vx, max);
    push(slosh.z, vz, max);
    ctx.wake();
  };
  b.hover = (id) => b.cursor(id);
  b.click = (id) => {
    if (id === 'flask') kick(2.4, -1.4);
    else if (top && !ctx.reduced()) {
      push(shove, 5.5);
      kick(-1.6, 0.8); // the flask rides on the book: it sloshes as the book is shoved
    }
  };
  b.activate = () => b.click('book');
  b.drag = (dx, dy) => kick(dx * 0.045, dy * 0.02);
  b.nudge = ({ px = 0 }) => kick(px * 0.0016, 0, 1.5);
  b.reset = () => {
    for (const p of [slosh.x, slosh.z, shove]) (p.x = 0), (p.v = 0);
    pose();
  };
  const pose = () => {
    uniforms.uTiltX.value = slosh.x.x * 0.55;
    uniforms.uTiltZ.value = slosh.z.x * 0.55;
    if (top) {
      top.position.copy(topRest.pos).x += 0.03 * shove.x;
      qa.setFromAxisAngle(Y, -0.5 * shove.x);
      top.quaternion.copy(qa).multiply(topRest.quat);
    }
  };
  b.update = (dt) => {
    // The book's own motion shakes the liquid a little too.
    const moving = ctx.reduced() ? false : [advance(slosh.x, dt), advance(slosh.z, dt), advance(shove, dt)].some(Boolean);
    pose();
    return moving;
  };
  return b;
}

// ── yardsign: the grass ruffles under the pointer, the sign wobbles on its stake ──
function yardsign(model, ctx) {
  const sign = model.getObjectByName('Sign');
  const grass = model.getObjectByName('Grass');
  if (!sign && !grass) return null;
  const b = skeleton(model, ctx);
  const uniforms = { uPoint: { value: new Vector3() }, uInf: { value: 0 }, uTime: { value: 0 }, uBase: { value: 0 }, uHeight: { value: 1 } };
  let signRest = null;
  let pivot = null;
  const side = pendulum({ k: 150, c: 8.5, limit: 0.35 });
  const fore = pendulum({ k: 150, c: 8.5, limit: 0.25 });
  const target = { x: 0, z: 0, on: false };
  const point = new Vector3();
  const ground = new Vector3();
  let held = null;

  if (sign) {
    signRest = b.keep(sign);
    // The stake's foot: the lowest point of the sign, at its own middle, a little under the turf.
    const box = new Box3().setFromObject(sign, true);
    const into = sign.parent.matrixWorld.clone().invert();
    box.applyMatrix4(into);
    pivot = new Vector3(signRest.pos.x, box.min.y + 0.018, signRest.pos.z);
    b.box(sign, 'sign', 0.004);
  }
  if (grass) {
    grass.geometry.computeBoundingBox();
    const bb = grass.geometry.boundingBox;
    uniforms.uBase.value = bb.min.y;
    uniforms.uHeight.value = bb.max.y - bb.min.y;
    b.box(grass, 'grass', 0);
  }

  b.extend = (shader, x, m) => {
    if (m !== grass) return;
    Object.assign(shader.uniforms, uniforms);
    // Blades lean away from the pointer and shiver, more toward their tips; the pointer's pool is where it touches the turf.
    shader.vertexShader = shader.vertexShader
      .replace('#include <common>', '#include <common>\nuniform vec3 uPoint;\nuniform float uInf;\nuniform float uTime;\nuniform float uBase;\nuniform float uHeight;')
      .replace(
        '#include <begin_vertex>',
        `#include <begin_vertex>
        float hgt = clamp((position.y - uBase) / uHeight, 0.0, 1.0);
        vec2 away = position.xz - uPoint.xz;
        float reach = exp(-dot(away, away) / 0.16) * uInf;
        vec2 dir = normalize(away + 1e-4);
        float shiver = sin(uTime * 9.0 + position.x * 31.0 + position.z * 23.0);
        transformed.xz += (dir * 0.22 + vec2(shiver, cos(uTime * 8.0 + position.z * 29.0)) * 0.05) * reach * hgt * hgt;
        transformed.y -= reach * hgt * hgt * 0.06;`,
      );
  };

  /** Where the ray meets the turf, in the grass's own space. */
  const turf = (ray) => {
    if (!grass) return false;
    grass.updateWorldMatrix(true, false);
    const inv = grass.matrixWorld.clone().invert();
    const o = ray.ray.origin.clone().applyMatrix4(inv);
    const d = ray.ray.direction.clone().transformDirection(inv);
    const yTop = uniforms.uBase.value + uniforms.uHeight.value * 0.5;
    if (Math.abs(d.y) < 1e-4) return false;
    const t = (yTop - o.y) / d.y;
    if (t < 0) return false;
    ground.copy(o).addScaledVector(d, t);
    return true;
  };
  b.pick = (ray) => {
    const id = pickId(ray, b.boxes);
    if (id === 'grass' && turf(ray)) {
      target.x = ground.x;
      target.z = ground.z;
      target.on = true;
    } else target.on = false;
    return id;
  };
  b.hover = (id) => {
    if (id !== 'grass') target.on = false;
    b.cursor(id);
    ctx.wake();
  };
  const flick = (dv) => {
    if (ctx.reduced()) return;
    push(side, dv, 5);
    push(fore, dv * 0.35, 4);
    ctx.wake();
  };
  pressable(b, {
    onDown: (id, e) => {
      if (id === 'sign') held = { x: e.clientX, base: side.x, t: e.timeStamp };
      if (id === 'sign') side.held = true;
    },
    onMove: (e, id, dx) => {
      if (!held) return;
      const dt = Math.max(1, e.timeStamp - held.t) / 1000;
      held.t = e.timeStamp;
      hold(side, held.base + dx * 0.006, dt);
      ctx.wake();
    },
    onUp: () => {
      if (held) {
        release(side);
        if (ctx.reduced()) (side.x = 0), (side.v = 0);
      }
      held = null;
    },
  });
  b.click = (id) => id === 'sign' && flick(4.2);
  b.activate = () => flick(4.2);
  b.nudge = ({ px = 0 }) => flick(Math.sign(px) * Math.min(1.2, Math.abs(px) * 0.0008));
  b.reset = () => {
    for (const p of [side, fore]) (p.x = 0), (p.v = 0), (p.held = false);
    uniforms.uInf.value = 0;
    target.on = false;
    pose();
  };
  const pose = () => {
    if (!sign) return;
    qa.setFromAxisAngle(Z, side.x);
    qb.setFromAxisAngle(X, fore.x);
    qa.multiply(qb);
    pivotRotate(sign, signRest, pivot, qa);
  };
  let time = 0;
  b.update = (dt) => {
    let moving = false;
    if (!ctx.reduced()) {
      if (advance(side, dt)) moving = true;
      if (advance(fore, dt)) moving = true;
    }
    // The pool of influence follows the pointer while it is over the turf and drains away when it leaves.
    const goal = target.on && !ctx.reduced() ? 1 : 0;
    if (target.on) {
      uniforms.uPoint.value.set(lerp(uniforms.uPoint.value.x, target.x, 1 - Math.exp(-18 * dt)), 0, lerp(uniforms.uPoint.value.z, target.z, 1 - Math.exp(-18 * dt)));
    }
    const k = 1 - Math.exp(-(goal ? 14 : 3.2) * dt);
    uniforms.uInf.value += (goal - uniforms.uInf.value) * k;
    if (uniforms.uInf.value < 0.004 && !goal) uniforms.uInf.value = 0;
    else {
      moving = true;
      time += dt;
      uniforms.uTime.value = time;
    }
    pose();
    return moving;
  };
  return b;
}

// ── window: a click sends the next chat message ──────────────────────────────
function windowObj(model, ctx) {
  const names = ['screen_base', 'bubble_user', 'bubble_agent_1', 'tool_card', 'bubble_agent_2', 'bubble_user_2', 'bubble_agent_3', 'caret'];
  const nodes = Object.fromEntries(names.map((n) => [n, model.getObjectByName(n)]));
  if (!nodes.bubble_user_2 || !nodes.bubble_agent_3 || !nodes.caret) return null;
  const b = skeleton(model, ctx);
  const rests = Object.fromEntries(Object.entries(nodes).filter(([, n]) => n).map(([k, n]) => [k, b.keep(n)]));
  const scroll = ['bubble_user', 'bubble_agent_1', 'tool_card', 'bubble_agent_2'];
  const SCROLL = 0.0085;
  const CARET = new Vector3(-0.024342877274751665, -0.06960399755239487, 0);
  const slab = nodes.screen_base.parent;
  const up = spring(0); // the first four bubbles move up
  const first = spring(0); // the follow-ups scale in, in turn
  const second = spring(0);
  const move = spring(0); // the caret moves to the new line
  let sent = false;
  let clock = 0; // seconds since the send
  let blink = 0; // seconds the caret has been blinking
  const caretMesh = nodes.caret.children[0];
  // The layers are alpha-blended, and the glass in front of them is seen through, not drawn over: it samples what was
  // drawn before it, and transparent things are drawn after it, behind its depth. So the layers are drawn with the
  // opaque ones (before the glass, and into what the glass sees) but with real blending, in a fixed order, writing no
  // depth of their own: the base first, then the bubbles, then the caret.
  const ORDER = { screen_base: 0, caret: 2 };
  for (const [name, n] of Object.entries(nodes)) {
    n?.traverse((m) => {
      if (!m.isMesh) return;
      const x = m.material;
      x.transparent = false;
      x.blending = CustomBlending;
      x.blendEquation = AddEquation;
      x.blendSrc = SrcAlphaFactor;
      x.blendDst = OneMinusSrcAlphaFactor;
      x.alphaTest = 0;
      x.depthWrite = name === 'screen_base';
      m.renderOrder = 10 + (ORDER[name] ?? 1); // after the rest of the opaque queue, in this order among themselves
      x.needsUpdate = true;
    });
  }
  b.box(slab.getObjectByName('Mask') ?? nodes.screen_base, 'screen', 0.003);

  const send = () => {
    sent = !sent;
    clock = 0;
    blink = 0;
    ctx.wake();
  };
  b.hover = (id) => b.cursor(id);
  b.click = send;
  b.activate = send;
  b.reset = () => {
    sent = false;
    for (const s of [up, first, second, move]) jump(s, 0);
    pose();
  };
  const pose = () => {
    for (const n of scroll) {
      const r = rests[n];
      if (r) nodes[n].position.copy(r.pos).y += SCROLL * up.x;
    }
    // Scale in from the bottom-left corner (the layers' origin), with a little overshoot from the spring's follow.
    nodes.bubble_user_2.scale.setScalar(Math.max(1e-4, first.x));
    nodes.bubble_agent_3.scale.setScalar(Math.max(1e-4, second.x));
    nodes.bubble_user_2.visible = first.x > 0.002;
    nodes.bubble_agent_3.visible = second.x > 0.002;
    nodes.caret.position.copy(rests.caret.pos);
    nodes.caret.position.x = lerp(rests.caret.pos.x, CARET.x, move.x);
    nodes.caret.position.y = lerp(rests.caret.pos.y, CARET.y, move.x);
  };
  nodes.bubble_user_2.visible = false;
  nodes.bubble_agent_3.visible = false;
  b.update = (dt) => {
    clock += dt;
    const reduced = ctx.reduced();
    const goal = (v) => (sent ? v : 0);
    const gUp = goal(1);
    const gFirst = sent && clock > 0.25 ? 1 : 0;
    const gSecond = sent && clock > 0.75 ? 1 : 0;
    const gMove = sent && clock > 1.05 ? 1 : 0;
    const rate = (s, g, r) => (reduced ? jump(s, g) : chase(s, g, r, dt));
    rate(up, gUp, RATE.object);
    rate(first, gFirst, RATE.part);
    rate(second, gSecond, RATE.part);
    rate(move, gMove, RATE.object);
    let moving = [[up, gUp], [first, gFirst], [second, gSecond], [move, gMove]].some(([s, g]) => !settled(s, g, 1e-3));
    // The caret blinks while the reply streams in: from the send until a moment after it has arrived.
    const streaming = sent && !reduced && clock < 2.6;
    if (streaming) {
      blink += dt;
      moving = true;
    }
    if (caretMesh) caretMesh.visible = !streaming || Math.floor(blink / 0.35) % 2 === 0;
    if (!streaming && caretMesh) caretMesh.visible = true;
    if (sent && clock < 1.2) moving = true; // the timer for the next step has not run out
    pose();
    return moving;
  };
  return b;
}

// ── watch: the crystal plays and pauses, the ring advances while it plays ────
function watch(model, ctx) {
  const play = model.getObjectByName('icon_play');
  const pause = model.getObjectByName('icon_pause');
  const ring = model.getObjectByName('ring_progress');
  const crystal = model.getObjectByName('Crystal');
  const button = model.getObjectByName('Button0');
  if (!crystal) return null;
  const b = skeleton(model, ctx);
  const buttonRest = button ? b.keep(button) : null;
  b.box(crystal, 'crystal', 0.004);
  const uniforms = { uProgress: { value: 0.62 }, uKnob: { value: 1 } };
  const press = spring(0);
  let playing = false;
  let progress = 0.62;
  let since = 0; // performance.now() when it last started playing, and the progress it started from
  let from = progress;
  const SPEED = 1 / 90000; // the track is 90 s long

  const show = () => {
    if (play) play.visible = !playing;
    if (pause) pause.visible = playing;
  };
  show();
  b.extend = (shader, x, m) => {
    if (m !== ring && m.parent !== ring) return;
    shader.uniforms.uProgress = uniforms.uProgress;
    shader.vertexShader = shader.vertexShader.replace('#include <common>', '#include <common>\nvarying vec2 vRing;').replace('#include <begin_vertex>', '#include <begin_vertex>\nvRing = uv;');
    shader.fragmentShader = shader.fragmentShader
      .replace('#include <common>', '#include <common>\nvarying vec2 vRing;\nuniform float uProgress;')
      // The leading edge is one pixel wide and anti-aliased (alpha to coverage, over the multisampled buffer), so as the ring
      // grows by a fraction of a pixel a frame it sweeps smoothly instead of stepping a whole pixel at a time.
      .replace('#include <opaque_fragment>', 'diffuseColor.a *= clamp((uProgress - vRing.x) / max(fwidth(vRing.x), 1e-5) + 0.5, 0.0, 1.0);\n#include <opaque_fragment>');
  };
  ring?.traverse((m) => m.isMesh && (m.material.alphaToCoverage = true));
  const toggle = () => {
    if (!playing && progress >= 0.999) progress = 0;
    playing = !playing;
    if (playing) (since = performance.now()), (from = progress);
    show();
    press.x = 1;
    ctx.wake();
  };
  b.hover = (id) => b.cursor(id);
  b.click = toggle;
  b.activate = toggle;
  b.reset = () => {
    playing = false;
    show();
    jump(press, 0);
  };
  b.update = (dt, { hero } = {}) => {
    let moving = false;
    if (ctx.reduced()) jump(press, 0);
    else chase(press, 0, RATE.quick, dt);
    if (!settled(press, 0, 1e-3)) moving = true;
    if (button) button.position.copy(buttonRest.pos).addScaledVector(Z, -0.0005 * press.x);
    if (playing && hero === false) b.reset();
    if (playing) {
      // By the clock, so it keeps time however often it is drawn: every frame while it plays and is on the stage.
      progress = Math.min(1, from + (performance.now() - since) * SPEED);
      uniforms.uProgress.value = progress;
      if (progress >= 1) (playing = false), show();
      moving = true;
    }
    return moving;
  };
  return b;
}

// ── cloche: the dome lifts to show the stars ─────────────────────────────────
function cloche(model, ctx) {
  const dome = model.getObjectByName('DomePivot');
  if (!dome) return null;
  const b = skeleton(model, ctx);
  const rest = b.keep(dome);
  b.box(dome, 'dome', 0.006);
  const open = spring(0);
  let goal = 0;
  let held = null;

  const toggle = () => {
    goal = goal ? 0 : 1;
    ctx.wake();
  };
  pressable(b, {
    onDown: (id, e) => (held = { y: e.clientY, from: open.x, moved: false }),
    onMove: (e, id, dx, dy) => {
      if (!held) return;
      if (Math.abs(dy) > 8) held.moved = true;
      if (held.moved) {
        goal = clamp(held.from - dy / 140, 0, 1);
        open.x = goal;
        open.v = 0;
        ctx.wake();
      }
    },
    onUp: () => {
      if (held?.moved) goal = goal > 0.5 ? 1 : 0; // a drag lets go to the nearer end
      if (held?.moved) b.dragged = true;
      held = null;
    },
  });
  b.hover = (id) => b.cursor(id);
  b.click = () => {
    if (b.dragged) return void (b.dragged = false);
    toggle();
  };
  b.activate = toggle;
  b.reset = () => {
    goal = 0;
    jump(open, 0);
    pose();
  };
  const pose = () => {
    const o = open.x;
    qa.setFromAxisAngle(X, -0.7 * o);
    dome.quaternion.copy(qa).multiply(rest.quat);
    dome.position.copy(rest.pos);
    dome.position.y += 0.075 * o;
    dome.position.z += -0.06 * o;
  };
  b.update = (dt) => {
    if (ctx.reduced()) jump(open, goal);
    else if (!held?.moved) chase(open, goal, RATE.ring, dt);
    const moving = held?.moved || !settled(open, goal, 1e-3);
    if (!moving) jump(open, goal);
    pose();
    return !!moving;
  };
  return b;
}

// ── takeout: the chopsticks lift with a few noodles ──────────────────────────
function takeout(model, ctx) {
  const sticks = model.getObjectByName('Chopsticks');
  if (!sticks) return null;
  const b = skeleton(model, ctx);
  const rest = b.keep(sticks);
  const strands = [];
  model.traverse((n) => n.isMesh && n.morphTargetDictionary && 'lifted' in n.morphTargetDictionary && strands.push(n));
  b.box(sticks, 'sticks', 0.01);
  const lift = spring(0);
  let goal = 0;
  let hover = false;

  const toggle = () => {
    goal = goal ? 0 : 1;
    ctx.wake();
  };
  b.hover = (id) => {
    hover = !!id;
    b.cursor(id);
    ctx.wake();
  };
  b.click = toggle;
  b.activate = toggle;
  b.reset = () => {
    goal = 0;
    jump(lift, 0);
    pose();
  };
  const pose = () => {
    const l = lift.x;
    sticks.position.copy(rest.pos);
    sticks.position.y += 0.06 * l;
    qa.setFromAxisAngle(Z, -0.06 * l);
    sticks.quaternion.copy(qa).multiply(rest.quat);
    for (const s of strands) s.morphTargetInfluences[s.morphTargetDictionary.lifted] = clamp(l, 0, 1);
  };
  b.update = (dt) => {
    const g = goal + (hover && !goal ? 0.06 : 0);
    if (ctx.reduced()) jump(lift, g);
    else chase(lift, g, RATE.camera, dt);
    const moving = !settled(lift, g, 1e-3);
    if (!moving) jump(lift, g);
    pose();
    return moving;
  };
  const dispose = b.dispose;
  b.dispose = () => {
    for (const s of strands) s.morphTargetInfluences[s.morphTargetDictionary.lifted] = 0;
    dispose();
  };
  return b;
}

const makers = { planner, filebox, pricetag, textbooks, yardsign, window: windowObj, watch, cloche, takeout };

/** The interaction for project object `name`, or null when its model has none of the nodes it needs. */
export function createBehaviour(name, model, ctx) {
  try {
    const b = makers[name]?.(model, ctx);
    if (b) {
      b.hover ??= () => {};
      b.update ??= () => false;
    }
    return b ?? null;
  } catch (err) {
    console.warn(`stage: ${name} interaction not built`, err);
    return null;
  }
}
