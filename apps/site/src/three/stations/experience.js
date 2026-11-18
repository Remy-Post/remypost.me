/**
 * The work-experience station: three ID badges fanned on one lanyard clip (badge.glb: `badge_dnd`, `badge_camp`,
 * `badge_food`, `clip`, `lanyard`) and a sash of embroidered merit patches beside them (patches.glb: `sash`, `patch_<id>`).
 *
 * Scrolling through the jobs brings that job's badge to the front: the fan re-shuffles on damped springs, the front badge
 * swings from the pointer and from scroll speed and can be dragged and released, and a click on a badge behind it
 * brings it forward. While a job is in front its patches fly in one after another along a short arc and pin onto the
 * sash; they leave when the job changes. Hovering a patch lifts it and lights its bullet in the text, and the reverse.
 * Positions come from the files; nothing about the layout is hard-coded except the offsets patches fly in from.
 */
import { Box3, Group, Quaternion, Vector3 } from 'three';
import { jobs } from '../../content/site.js';
import { clearHot, getHot, onHot, setHot } from '../../scene/hot.js';
import { advance, hold, pendulum, push, release } from '../physics.js';
import { hitBox, pickId, prepare } from '../common.js';
import { RATE, chase, jump, lerp, settled, smoothstep, spring } from '../motion.js';

const STAGGER = 0.075; // seconds between one patch and the next
const SASH_SCALE = 1.4;
const SASH_FRAME = 1.08;
const PATCH_BIG = 1.22; // on a wide stage the pinned patches are drawn a fifth larger than the grid they sit in, so their labels read (they stop just short of touching) // the sash's width as a share of the frame it is looked at in: about 6% of dark floor each side, room for the angle
const SASH_YAW = -12; // degrees, the camera swung to the left
const SASH_PITCH = 15; // and raised a little more than when both are shown
const GROUP_FILL = 0.93; // the badge group, bar to base, fills this much of the frame's height
const SASH_SHARE = 0.6; // and the sash about 55% of its width, on the right (its box over-reads: rails and feet)
const FRONT_Z = 0.006; // the front badge stands this far toward the camera
const axisZ = new Vector3(0, 0, 1);
const qa = new Quaternion();
const qb = new Quaternion();

export function createExperienceStation(ctx) {
  const group = new Group();
  const fit = new Group();
  group.add(fit);
  const fade = { value: 0 };
  const patchFade = { value: 0 }; // the sash's own fade: on a small stage it is out of the picture while the badges are looked at, and dissolves in as the camera goes to it
  const boxes = []; // badges' boxes then patches'
  const badges = []; // { node, rest, restQ, swing: pendulum, z: spring, index, job }
  const patches = new Map(); // id -> { node, rest, restQ, scale, a: pendulum, delay, lift: spring, jobIndex, order, start, startQ }
  const station = { id: 'experience', group, size: { w: 1, h: 1 }, ready: false, fade, boxes };
  let badgeBoxes = [];
  let patchBoxes = new Map();
  let job = 0;
  let shown = -1; // the job whose patches are pinned
  let clock = 0;
  let hover = null; // a badge index or a patch id
  let drag = null;
  let amp = 0.28;

  const upQ = new Quaternion();
  const off = onHot(() => ctx.wake());
  const litIds = () => (getHot().kind === 'patch' ? getHot().ids : []);

  // The lanyard hangs from its bar and follows the badge on it: its second UV set runs 0 at the bar to 1 at the clip (the
  // strap's length), so the far end swings the most and a small wave runs down it as it settles.
  const sway = { uSway: { value: 0 }, uWave: { value: 0 }, uPhase: { value: 0 } };
  const swing = spring(0); // the lanyard's own lag behind the front badge's swing
  let wavePhase = 0;
  let waveAmp = 0;
  const lanyard = (shader, material, mesh) => {
    if (mesh.name !== 'lanyard_0') return;
    Object.assign(shader.uniforms, sway);
    shader.vertexShader = shader.vertexShader
      .replace(
        '#include <common>',
        `#include <common>
        uniform float uSway;
        uniform float uWave;
        uniform float uPhase;
        #ifndef USE_UV1
        attribute vec2 uv1;
        #endif`,
      )
      .replace(
        '#include <begin_vertex>',
        `#include <begin_vertex>
        float along = uv1.x;
        transformed.x += (uSway * along * along + uWave * sin(along * 7.0 - uPhase) * along * (1.0 - 0.35 * along)) * 0.5;`,
      );
  };

  let frames = null; // { wide, badge, sash }: where the camera looks, in the station's own normalised units
  const view = spring(0); // narrow stages: 0 looking at the badge, 1 at the sash
  const near = { cx: spring(0), ty: spring(0), w: spring(1), h: spring(1), set: false }; // the sash frame, sliding from one job's patches to the next

  /**
   * Lay the two models out: the sash is left at its own size, on the right; the badge group is scaled so the whole of it,
   * brass bar to stand base, fills GROUP_FILL of the frame's height, at the left with nothing clipped. A narrow stage
   * cannot hold both legibly, so it alternates: the badge while the job's title is read, the sash while its points are.
   */
  function compose(badgeModel, patchModel, inner) {
    const hero = badges[0]?.node ?? badgeModel;
    const box = (o) => new Box3().setFromObject(o, true);
    badgeModel.updateMatrixWorld(true);
    const g0 = box(badgeModel); // the whole group: brass cross bar to stand base, fanned cards included
    const groupH0 = g0.max.y - g0.min.y;
    const groupW0 = g0.max.x - g0.min.x;
    if (patchModel) {
      patchModel.scale.setScalar(SASH_SCALE); // beside the badges the sash is drawn larger than life, so it reads
      patchModel.updateMatrixWorld(true);
    }
    const sb = patchModel ? box(patchModel) : null;
    const sashW = sb ? sb.max.x - sb.min.x : 0.3;
    // The whole badge group stands inside the frame, GROUP_FILL of its height (the margins are what is left), and the frame is
    // wide enough for it and the sash side by side with a margin at the left.
    const W = Math.max(sashW / SASH_SHARE, sashW / (0.93 - (GROUP_FILL * groupW0) / groupH0)); // the frame's width, metres of the sash's scale
    const V = W; // and its height: the stage is close to square
    const kB = (GROUP_FILL * V) / groupH0;
    badgeModel.scale.setScalar(kB);
    badgeModel.updateMatrixWorld(true);
    const g1 = box(badgeModel);
    badgeModel.position.x += 0.04 * W - g1.min.x; // nothing clipped at the left
    if (patchModel && sb) patchModel.position.x += W * 0.985 - sb.max.x; // the sash against the right
    inner.updateMatrixWorld(true);
    const hb3 = box(hero);
    const hc = hb3.getCenter(new Vector3());
    const gb = box(badgeModel);
    const gc = gb.getCenter(new Vector3());
    const sb2 = sb ? box(patchModel) : hb3;
    const sc = sb2.getCenter(new Vector3());
    const yc = gc.y - 0.022 * V; // the group is centred in the frame, top and bottom (the stand base is nearer the camera, so a touch high)
    const k = 1 / W;
    fit.scale.setScalar(k);
    fit.position.set(-0.5 * W * k, 0, 0); // the frame's middle on the station's axis
    const norm = (cx, cy, w, h) => ({ cx: (cx - 0.5 * W) * k, ty: cy * k, w: w * k, h: h * k });
    // Close on the sash, the camera frames the patches of the job being read, not the whole strip: the four columns of a
    // row fill the stage's width, so every label is as large as the stage can make it (a job with fewer is centred, at
    // the same size). The size of the full grid is the least that is ever framed.
    const grid = new Box3();
    const perJob = jobs.map((j) => {
      const b = new Box3();
      for (const id of j.points.flatMap((pt) => pt.patches)) {
        const node = patches.get(id)?.node;
        if (node) b.union(box(node));
      }
      grid.union(b);
      return b;
    });
    const gw = grid.isEmpty() ? sashW : (grid.max.x - grid.min.x) * 1.14;
    const patchFrames = perJob.map((b) => {
      if (b.isEmpty()) return norm(sc.x, sc.y, sashW * 1.08, sashW * 1.08);
      const c = b.getCenter(new Vector3());
      return norm(c.x, c.y, Math.max(gw, (b.max.x - b.min.x) * 1.14), Math.max(gw, (b.max.y - b.min.y) * 1.14));
    });
    // The close-up of the sash on a wide stage keeps the whole of it in frame, rail to bottom hem and both posts, with dark
    // floor round it, seen a little from the side and above so the folds and the rail catch the light.
    const ss = sb2.getSize(new Vector3());
    const sashAll = norm(sc.x, sc.y, ss.x * SASH_FRAME, ss.y * SASH_FRAME);
    frames = {
      sashAll,
      wide: norm(0.5 * W, yc, W, V),
      // On a narrow stage (a phone, a window about 1024 wide) the badges are looked at closer: the clip, the front card and the stand, the
      // lanyard's top and the fan's outer edges left to run out of frame, so the card's name and employer read.
      badge: norm(gc.x, gb.min.y + 0.36 * (gb.max.y - gb.min.y), (gb.max.x - gb.min.x) * 0.66, (gb.max.y - gb.min.y) * 0.7),
      sash: patchFrames[0],
      patch: patchFrames,
    };
    Object.assign(station.size, frames.wide, { d: 0.2, radius: 0.5, k });
  }

  station.load = async (badgeUrl, patchesUrl) => {
    const inner = new Group();
    const [badgeModel, patchModel] = await Promise.all([ctx.loadModel(badgeUrl), patchesUrl ? ctx.loadModel(patchesUrl) : null]);
    prepare(badgeModel, { fade, ...ctx.look, extend: lanyard });
    if (patchModel) prepare(patchModel, { fade: patchFade, ...ctx.look });

    jobs.forEach((j, index) => {
      const node = badgeModel.getObjectByName(`badge_${j.badge}`);
      if (!node) return;
      badges.push({ node, index, rest: node.position.clone(), restQ: node.quaternion.clone(), swing: pendulum({ k: 55, c: 8, limit: 1.0 }), z: spring(0) });
    });
    // The fan's spread comes from the file: the rear badges' own tilt about Z.
    const tilt = Math.max(0, ...badges.map((b) => Math.abs(2 * Math.asin(Math.min(1, Math.abs(b.restQ.z))))));
    if (tilt > 0.05) amp = tilt * 0.7; // the rear cards peek out; they do not cover the sash
    inner.add(badgeModel);

    if (patchModel) {
      inner.add(patchModel);
      patchModel.updateMatrixWorld(true);
      jobs.forEach((j, jobIndex) =>
        j.points
          .flatMap((p) => p.patches)
          .forEach((id, order) => {
            const node = patchModel.getObjectByName(`patch_${id}`);
            if (!node) return;
            const k = patches.size;
            const rest = node.position.clone();
            const jitter = ((k * 37) % 11) / 11 - 0.5;
            const start = rest.clone().add(new Vector3(0.28 + jitter * 0.06, 0.18 - jitter * 0.05, 0.22));
            const startQ = node.quaternion.clone().multiply(qa.setFromAxisAngle(axisZ, 0.9 + jitter));
            patches.set(id, { node, id, rest, restQ: node.quaternion.clone(), scale: node.scale.clone(), a: pendulum({ k: 130, c: 15, limit: 1.6 }), delay: 0, lift: spring(0), tick: spring(0), landed: false, jobIndex, order, start, startQ: startQ.clone() });
          }),
      );
    }

    compose(badgeModel, patchModel, inner);
    inner.updateMatrixWorld(true);
    badges.forEach((b) => badgeBoxes.push(hitBox(inner, b.node, b.index, 0.004)));
    for (const [id, p] of patches) patchBoxes.set(id, hitBox(inner, p.node, id, 0.002));
    boxes.push(...badgeBoxes, ...patchBoxes.values());
    fit.add(inner);
    station.models = [badgeModel, patchModel].filter(Boolean);
    for (const p of patches.values()) p.node.visible = false;
    return station;
  };

  /** The job in front: continuous while scrolling; the patches follow the whole number it settles on. */
  station.setJob = (j, w = 0.5) => {
    job = j;
    within = w;
    const n = Math.min(jobs.length - 1, Math.max(0, Math.round(j)));
    if (n !== shown && Math.abs(j - n) < 0.38) {
      shown = n;
      armed = false; // the new job's patches wait for the camera to be on the sash (at once, on a wide stage)
    }
    if (!ctx.reduced()) ctx.wake(); // under reduced motion the stage draws once, when the scrolling has stopped
  };
  let armed = true;
  /**
   * Where in the job's own text the visitor is, 0 at its start and 1 at its end. The badge and the sash cannot both be
   * legible at once on a narrow stage, so there the badge is shown while the title is read and the sash while the points
   * are; on a wide one both are shown, and the camera comes in on the sash for the second part of the text so every patch's
   * label can be read.
   */
  let within = 0.5;
  /** A phone, or a stage too narrow for both (about 1024 px of window): the badge and the sash take turns. */
  const compact = () => !ctx.wide() || ctx.width() < 700;
  const sashTime = () => within > (compact() ? 0.4 : 0.68);
  station.nudge = ({ scroll = 0, px = 0, py = 0 }) => {
    if (ctx.reduced()) return;
    for (const b of badges) {
      const w = 1 - Math.min(1, Math.abs(b.index - job));
      if (w <= 0) continue;
      push(b.swing, (-px * 0.0011 + scroll * 0.00007) * w, 3);
    }
    waveAmp = Math.min(1, waveAmp + Math.min(0.5, Math.abs(px) * 0.0002 + Math.abs(scroll) * 0.00012));
    ctx.wake();
  };

  const frontBadge = () => Math.min(badges.length - 1, Math.max(0, Math.round(job)));
  station.currentJob = () => Math.min(jobs.length - 1, Math.max(0, Math.round(job)));
  station.pickables = () => [...badgeBoxes, ...[...patchBoxes].filter(([id]) => patches.get(id)?.a.x > 0.6 && patches.get(id).jobIndex === shown).map(([, box]) => box)];
  station.pick = (ray) => pickId(ray, station.pickables());

  station.hover = (id) => {
    if (hover === id) return;
    hover = id;
    if (typeof id === 'string') setHot('patch', [id], 'stage');
    else clearHot('patch', 'stage');
    ctx.cursor(id !== null);
    ctx.wake();
  };
  station.down = (id, e) => {
    if (typeof id !== 'number') return;
    const b = badges[id];
    if (!b) return;
    if (id !== frontBadge()) return;
    drag = { b, x: e.clientX, t: e.timeStamp, base: b.swing.x };
    b.swing.held = true;
    ctx.wake();
  };
  station.move = (e) => {
    if (!drag) return;
    const dt = Math.max(1, e.timeStamp - drag.t) / 1000;
    drag.t = e.timeStamp;
    hold(drag.b.swing, drag.base - (e.clientX - drag.x) * 0.006, dt);
    ctx.wake();
  };
  station.up = () => {
    if (!drag) return;
    release(drag.b.swing);
    if (ctx.reduced()) (drag.b.swing.x = 0), (drag.b.swing.v = 0);
    drag = null;
    ctx.wake();
  };
  /** A click on a badge behind the front one brings its job forward (the stage scrolls the text to it). */
  station.click = (id) => typeof id === 'number' && id !== frontBadge() && ctx.stepJob?.(id);

  station.update = (dt) => {
    let moving = false;
    clock += dt;
    const reduced = ctx.reduced();
    patchFade.value = fade.value * (compact() ? smoothstep(0.04, 0.5, view.x) : 1);
    const lit = litIds();
    // Where the camera looks: both together on a wide stage, the badge and then the sash on a narrow one.
    const toSash = sashTime();
    const open = !compact() || toSash;
    if (frames) {
      if (reduced) jump(view, toSash ? 1 : 0);
      else chase(view, toSash ? 1 : 0, RATE.camera, dt);
      if (!settled(view, toSash ? 1 : 0, 1e-3)) moving = true;
      const from = compact() ? frames.badge : frames.wide;
      const goal = frames.sashAll; // the whole sash, rail, posts and hems, on every stage
      for (const key of ['cx', 'ty', 'w', 'h']) {
        const s = near[key];
        if (reduced || !near.set) jump(s, goal[key]);
        else chase(s, goal[key], RATE.camera, dt);
        if (!settled(s, goal[key], 1e-4)) moving = true;
        else jump(s, goal[key]);
      }
      near.set = true;
      for (const key of ['cx', 'ty', 'w', 'h']) station.size[key] = lerp(from[key], near[key].x, view.x);
      station.size.pitch = lerp(9, SASH_PITCH, view.x);
      station.size.yaw = lerp(0, SASH_YAW, view.x);
    }
    if (open && !armed) {
      armed = true;
      let order = 0;
      for (const p of patches.values()) p.delay = p.jobIndex === shown ? (reduced ? 0 : order++ * STAGGER) : 0;
    }
    for (const b of badges) {
      // The fan: the badge in front hangs straight, the two behind lean away to opposite sides. As the front changes a
      // badge swings through the middle: 0 at d = 0, to one side at 1, back through the middle at 1.5, the other side at 2.
      const d = b.index - job;
      const a = Math.abs(d);
      b.swing.rest = amp * Math.sign(d) * (a <= 1 ? -a : -1 + 2 * Math.min(1, a - 1));
      if (reduced) {
        if (!b.swing.held) (b.swing.x = b.swing.rest), (b.swing.v = 0);
      } else if (advance(b.swing, dt)) moving = true;
      const front = 1 - Math.min(1, Math.abs(b.index - job));
      jump(b.z, front);
      b.node.position.copy(b.rest);
      b.node.position.z += FRONT_Z * front;
      qa.setFromAxisAngle(axisZ, b.swing.x);
      b.node.quaternion.copy(qa).multiply(upQ.identity());
    }
    // The lanyard follows the front badge's swing a little behind it, and a wave runs down it while anything has pushed it.
    let front = 0;
    for (const b of badges) front += b.swing.x * (1 - Math.min(1, Math.abs(b.index - job)));
    if (reduced) jump(swing, 0);
    else chase(swing, front, RATE.part, dt);
    sway.uSway.value = reduced ? 0 : swing.x * 0.9;
    waveAmp *= Math.exp(-2.2 * dt);
    if (waveAmp < 0.004) waveAmp = 0;
    else (wavePhase += dt * 8), (moving = true);
    sway.uWave.value = reduced ? 0 : waveAmp * 0.1;
    sway.uPhase.value = wavePhase;
    if (!settled(swing, front, 1e-3)) moving = true;
    for (const p of patches.values()) {
      const active = p.jobIndex === shown && armed;
      if (active && p.delay > 0) {
        p.delay -= dt;
        moving = true;
        continue; // not yet its turn
      }
      p.a.rest = active ? 1 : 0;
      if (reduced) (p.a.x = p.a.rest), (p.a.v = 0);
      else if (advance(p.a, dt)) moving = true;
      const a = p.a.x;
      // The pin goes in: as the patch first reaches the cloth it presses a hair into it and comes back (a "tick").
      if (active && !p.landed && a >= 1 && !reduced) {
        p.landed = true;
        p.tick.v = 55;
      } else if (!active && a < 0.5) p.landed = false;
      if (reduced) jump(p.tick, 0);
      else chase(p.tick, 0, RATE.quick, dt);
      if (!settled(p.tick, 0, 1e-3)) moving = true;
      const l = lit.includes(p.id) || hover === p.id ? 1 : active ? 0.5 : 0; // the job's patches stand a little proud of the cloth, lit
      if (reduced) jump(p.lift, l);
      else chase(p.lift, l, RATE.quick, dt);
      if (!settled(p.lift, l, 1e-3)) moving = true;
      p.node.visible = a > 0.01 || (!active && a > 0.01);
      const c = Math.min(1, Math.max(0, a));
      p.node.position.lerpVectors(p.start, p.rest, a);
      p.node.position.y += 0.07 * Math.sin(Math.PI * c) * (1 - c * 0.2);
      p.node.position.z += 0.012 * p.lift.x - 0.0016 * p.tick.x;
      p.node.quaternion.slerpQuaternions(p.startQ, p.restQ, Math.min(1.1, Math.max(0, a)));
      const s = (0.45 + 0.55 * Math.min(1.08, a)) * (1 + 0.08 * p.lift.x) * (compact() ? 1 : PATCH_BIG);
      p.node.scale.copy(p.scale).multiplyScalar(s);
    }
    return moving;
  };

  /** The station has left the stage: it will arrive again as it first was, composed (both in view), whatever it was left looking at. */
  station.reset = () => {
    if (!frames) return;
    jump(view, 0);
    near.set = false;
    delete station.size.pitch;
    delete station.size.yaw;
    Object.assign(station.size, frames.wide);
  };

  const cleanup = () => {
    for (const b of badges) {
      b.node.position.copy(b.rest);
      b.node.quaternion.copy(b.restQ);
    }
    for (const p of patches.values()) {
      p.node.position.copy(p.rest);
      p.node.quaternion.copy(p.restQ);
      p.node.scale.copy(p.scale);
      p.node.visible = true;
    }
    for (const b of boxes) b.removeFromParent();
    boxes.length = 0;
  };
  station.dispose = () => {
    off();
    cleanup();
  };
  /** Let go of the models (the stage frees them): the station can be loaded again later, as new. */
  station.unload = () => {
    cleanup();
    badges.length = 0;
    patches.clear();
    badgeBoxes = [];
    patchBoxes = new Map();
    shown = -1;
    armed = true;
    frames = null;
    near.set = false;
    for (const m of station.models ?? []) m.removeFromParent();
    station.models = [];
    station.ready = false;
  };
  return station;
}
