/**
 * The live stage: one WebGL canvas in the stage's mount, one scene, for the whole site. Reach it only through dynamic
 * import() (it pulls in three); live.js's startLive() does, once the page has painted.
 *
 *   const stage = await createStage(mount, { onLost })
 *   stage.dispose()
 *
 * The page has four stations, one per section, and the camera travels between them along one eased path as the page
 * scrolls (scene/progress.js `p`): the intro shows the whole turntable from above, then education (two school
 * pennants), work experience (badges and merit patches), the nine projects on the turntable, and the links (keycaps).
 * Every motion chases a target with damped springs and a frame is drawn only while something moves.
 * Models, the studio map and the disc are made elsewhere; this file moves, lights, frames and picks them.
 */
import {
  CircleGeometry,
  Color,
  DirectionalLight,
  EquirectangularReflectionMapping,
  Group,
  Mesh,
  MeshStandardMaterial,
  PCFShadowMap,
  PMREMGenerator,
  PerspectiveCamera,
  Raycaster,
  RGBAFormat,
  SRGBColorSpace,
  Scene,
  SpotLight,
  UnsignedByteType,
  Vector2,
  Vector3,
  Vector4,
  WebGLRenderer,
  NoToneMapping,
} from 'three';
import { HDRLoader } from 'three/addons/loaders/HDRLoader.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { projects } from '../content/site.js';
import { getProgress, onProgress, scrollYFor } from '../scene/progress.js';
import { scrollToTarget } from '../scene/smooth.js';
import { clearHot } from '../scene/hot.js';
import { countFrame, framesDrawn, markReady, clearReady, clearBuffers } from './live.js';
import { disposeModel, loadModel } from './models.js';
import * as pixels from './pixels.js';
import { RATE, chase, clamp, jump, lerp, settled, smoothstep, spring } from './motion.js';
import { prepare, normalise } from './common.js';
import { createBehaviour } from './objects.js';
import { createPost } from './post.js';
import { startSmooth } from './smooth.js';
import { COUNT, FOV, SIZE, STATION_X, STEP, TABLE_SCALE, frontIndex, path, radius, ringAngle, tableX, tableness, visibility, weight } from './rig.js';
import { isHidden, onPointer, onReducedMotion, onVisibility, pointer, reducedMotion } from './services.js';
import { createEducationStation } from './stations/education.js';
import { createExperienceStation } from './stations/experience.js';
import { createLinksStation } from './stations/links.js';

// Everything the stage needs from the asset folders, found by name so a file that has not arrived yet is just missing.
const files = import.meta.glob('../assets/models/*.glb', { eager: true, query: '?url', import: 'default' });
const modelUrl = (name) => files[`../assets/models/${name}.glb`];
const urls = projects.map((p) => modelUrl(p.object));
const env = Object.values(import.meta.glob('../assets/env/studio.hdr', { eager: true, query: '?url', import: 'default' }))[0];

const TAU = Math.PI * 2;
const rad = (deg) => (deg * Math.PI) / 180;
const WIDE = '(min-width: 960px)';
const LEAN = rad(6); // the front object leans at most this far toward the pointer
const DRAG = 0.006; // radians of turn per pixel dragged
const PRESENT = rad(24); // every object stands turned a little from the camera, as in the stills
const KEY = rad(15); // an arrow key turns the object this far
const FRICTION = 4; // per second, the inertia of a released drag
const RING_RATE = RATE.ring; // natural frequencies (rad/s) of the springs: see RATE in motion.js
const PATH_RATE = RATE.camera;
const FOCUS_RATE = RATE.camera;
const LEAN_RATE = RATE.object;
const SPIN_RATE = RATE.object;
const APPEAR_RATE = RATE.object;
const POOL_ALONE = Math.tan(0.5) * 6 / 2.2; // the pool of a lone object at a project (angle 0.5, light 6 away), metres
const POOL_OFFSET = [0.55, -0.25]; // where that pool sits against the object: the key's offset at a project
const STATION_POOL = 0.8; // how much of a project's pool a station has under it
const POOL = [0.5, 0.85]; // half-angle (rad) of the key light's pool: tight on one object, wide over the table
const KEY_LIGHT = new Vector3(-0.7, 1.55, 1).normalize(); // from upper left, in front
/**
 * The image's levels: Neutral tone mapping at exposure 1.1 (what the stage has always had), applied once in the image
 * pipeline, and gains on the studio's lights. They are an object so a development build can tune them live.
 */
const tuning = { exposure: 1.1, key: 0.32, env: 2.4, rim: 0.3, top: 0.8, metal: 0.28 };
const TAP = 7; // px: a press that moves less than this and ends within TAP_TIME is a tap
const TAP_TIME = 700;
const STATIONS = ['education', 'experience', 'links']; // the three that are not the table; place = index + 1 (links is 4)
const PLACE = { education: 1, experience: 2, links: 4 };

/**
 * The floor and the disc fade to nothing, in a round vignette, toward every edge of the picture, so the stage can never
 * show a rectangle: what is left at the edge is the clear colour, which is the page's own ground.
 */
const EDGE = `uniform vec2 uFadeAt;
uniform float uFadeScale;
float edgeFade(vec2 p) {
  float r = length((p - uFadeAt) * vec2(1.0, 0.92));
  return 1.0 - smoothstep(0.14 * uFadeScale, 0.39 * uFadeScale, r);
}`;

/** Run `fn` when the browser is idle, so loading the next model does not compete with scrolling. */
const idle = () => new Promise((resolve) => ('requestIdleCallback' in window ? requestIdleCallback(resolve, { timeout: 600 }) : setTimeout(resolve, 60)));

/** Free everything on the GPU that a tree owns. The parsed models keep their CPU data, so this is safe to repeat. */
function disposeTree(root) {
  root.traverse((o) => {
    o.geometry?.dispose();
    for (const m of [o.material].flat()) {
      if (!m) continue;
      for (const v of Object.values(m)) if (v?.isTexture) v.dispose();
      m.dispose();
    }
  });
}

/** The studio's light as a PMREM environment: studio.hdr when it exists, three's room, darkened, until then. */
async function makeEnvironment(renderer, scene) {
  const pmrem = new PMREMGenerator(renderer);
  let target;
  if (env) {
    const source = await new HDRLoader().loadAsync(env);
    source.mapping = EquirectangularReflectionMapping;
    target = pmrem.fromEquirectangular(source);
    source.dispose();
    scene.userData.envBase = 0.3;
  } else {
    const room = new RoomEnvironment();
    target = pmrem.fromScene(room, 0.04);
    room.dispose();
    scene.userData.envBase = 0.45;
  }
  pmrem.dispose();
  scene.environment = target.texture;
  return target;
}

export async function createStage(mount, { onLost, signal } = {}) {
  const canvas = document.createElement('canvas');
  // A software rasteriser is refused, as in canGoLive(): those visitors keep the stills.
  const renderer = new WebGLRenderer({ canvas, antialias: false, alpha: false, depth: false, stencil: false, powerPreference: 'high-performance', failIfMajorPerformanceCaveat: true });
  renderer.outputColorSpace = SRGBColorSpace;
  renderer.toneMapping = NoToneMapping; // the image pipeline tone maps (post.js)
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = PCFShadowMap;
  // The page's --ground, #0b0c0e, as the image pipeline will have turned it into. Neutral tone mapping takes the darkest
  // channel x of a dark colour to 6.25 x squared and moves the others with it, so this is that mapping run backwards. The
  // renderer encodes a clear colour set outside a render target as sRGB, and the pipeline's buffers hold it as linear
  // light: so the linear numbers go in as if they were sRGB ones, and come out unchanged.
  const GROUND = [0.00335, 0.00368, 0.00439]; // #0b0c0e in linear light
  // Measured on a screenshot, the picture came out two 8-bit steps above #0b0c0e (13,14,16, a faint lighter rectangle on the
  // dark): the encoding of the clear colour is a little off the model above, so the target is trimmed by that much.
  const TRIM = 0.0007;
  const lift = Math.sqrt((GROUND[0] - TRIM) / 6.25);
  renderer.setClearColor(new Color().setRGB(lift, GROUND[1] - GROUND[0] + lift, GROUND[2] - GROUND[0] + lift, SRGBColorSpace), 1);

  const ac = new AbortController();
  const scene = new Scene();
  const camera = new PerspectiveCamera(FOV, 1, 0.5, 80);
  const post = createPost(renderer, scene, camera);
  const overviewCamera = camera.clone();
  const OVERVIEW_SCALE = 0.8;
  let overviewPrimed = false;
  const ring = new Group();
  scene.add(ring);

  const mq = matchMedia(WIDE);
  let wide = mq.matches;
  let dead = false;
  let lost = false;
  let started = false; // nothing draws before the environment is ready
  let envTarget = null;
  const cleanups = [];
  const on = (target, type, fn, opts) => {
    target.addEventListener(type, fn, opts);
    cleanups.push(() => target.removeEventListener(type, fn, opts));
  };

  // ── the studio: a dark floor under the camera, one shadow-casting key light, a cool rim, a little fill ──
  // Soft contact shadows: one dark blob under each table object's footprint (x, z, radius, strength), no extra pass.
  const blobs = Array.from({ length: COUNT }, () => new Vector4());
  const floorCentre = { value: new Vector2() };
  const resolution = { value: new Vector2(1, 1) }; // the drawing buffer's size, for the screen-space edge fade
  // The round fade of the floor and the disc is as big as the picture's centre at a project (scale 1, centred): when what stands in it
  // is small in the frame (a lone object while the camera is pulled back) it shrinks to it and follows it, so the pool is never a
  // grey disc with a speck in it.
  const fadeAt = { value: new Vector2(0.5, 0.5) };
  const fadeScale = { value: 1 };
  const poolAt = { value: new Vector2() }; // where the key light's pool is centred (its target), not where the camera looks
  const poolR = { value: 3 }; // metres: the floor's light is a gaussian this wide round where the camera looks, so the pool has no traceable edge
  const floorMaterial = new MeshStandardMaterial({ color: '#1d1f24', roughness: 0.5, metalness: 0, transparent: true });
  // The floor thins out to nothing with distance from where the camera looks, so it has no far edge and no horizon.
  floorMaterial.onBeforeCompile = (shader) => {
    shader.uniforms.uBlob = { value: blobs };
    shader.uniforms.uCentre = floorCentre;
    shader.uniforms.uRes = resolution;
    shader.uniforms.uFadeAt = fadeAt;
    shader.uniforms.uFadeScale = fadeScale;
    shader.uniforms.uPool = poolR;
    shader.uniforms.uPoolAt = poolAt;
    shader.vertexShader = shader.vertexShader
      .replace('#include <common>', '#include <common>\nvarying vec2 vFloor;')
      .replace('#include <begin_vertex>', '#include <begin_vertex>\nvFloor = (modelMatrix * vec4(transformed, 1.0)).xz;');
    shader.fragmentShader = shader.fragmentShader
      .replace('#include <common>', `#include <common>\nvarying vec2 vFloor;\nuniform vec2 uCentre;\nuniform vec2 uRes;\nuniform float uPool;\nuniform vec2 uPoolAt;\n${EDGE}\nuniform vec4 uBlob[${COUNT}];`)
      .replace(
        '#include <opaque_fragment>',
        `float contact = 0.0;
        for (int i = 0; i < ${COUNT}; i++) {
          vec2 d = vFloor - uBlob[i].xy;
          contact += uBlob[i].w * exp(-dot(d, d) / (uBlob[i].z * uBlob[i].z));
        }
        outgoingLight *= 1.0 - 0.75 * clamp(contact, 0.0, 1.0);
        float away = length(vFloor - uCentre);
        vec2 pd = vFloor - uPoolAt;
        diffuseColor.a *= exp(-0.5 * dot(pd, pd) / (uPool * uPool)); // the pool fades into the ground itself, never to black
        diffuseColor.a *= 1.0 - smoothstep(2.5, 9.0, away);
        diffuseColor.a *= edgeFade(gl_FragCoord.xy / uRes);
        #include <opaque_fragment>`,
      );
  };
  const floor = new Mesh(new CircleGeometry(30, 96), floorMaterial);
  floor.rotation.x = -Math.PI / 2;
  floor.position.y = -0.006;
  floor.receiveShadow = true;
  const discMaterial = new MeshStandardMaterial({ color: '#555a63', roughness: 0.42, metalness: 0, transparent: true });
  // The disc has no edge either: it dissolves outward into the floor.
  discMaterial.onBeforeCompile = (shader) => {
    shader.vertexShader = shader.vertexShader.replace('#include <common>', '#include <common>\nvarying vec2 vDisc;').replace('#include <begin_vertex>', '#include <begin_vertex>\nvDisc = uv;');
    shader.fragmentShader = shader.fragmentShader
      .replace('#include <common>', '#include <common>\nvarying vec2 vDisc;')
      .replace('#include <common>', `#include <common>\nuniform vec2 uRes;\n${EDGE}`)
      .replace('#include <opaque_fragment>', 'diffuseColor.a *= 1.0 - smoothstep(0.55, 1.0, length(vDisc - 0.5) * 2.0);\ndiffuseColor.a *= edgeFade(gl_FragCoord.xy / uRes);\n#include <opaque_fragment>');
    shader.uniforms.uRes = resolution;
    shader.uniforms.uFadeAt = fadeAt;
    shader.uniforms.uFadeScale = fadeScale;
  };
  const disc = new Mesh(new CircleGeometry(1, 128), discMaterial);
  disc.rotation.x = -Math.PI / 2;
  disc.receiveShadow = true;
  scene.add(floor);
  ring.add(disc);

  // One key light: a soft-edged spot from the upper left that makes a pool of light around what the camera looks at.
  const key = new SpotLight(0xfffaf4, 10, 0, 0.3, 1, 0);
  key.castShadow = true;
  key.shadow.mapSize.setScalar(wide ? 2048 : 1024);
  key.shadow.bias = -0.0003;
  key.shadow.normalBias = 0.012;
  key.shadow.radius = 3;
  key.shadow.camera.near = 1;
  key.shadow.camera.far = 24;
  scene.add(key, key.target);
  // A cooler rim from behind on the right that outlines every silhouette, and an overhead fill for the table view.
  const rim = new DirectionalLight(0xd2ddff, 3.0);
  rim.position.set(4, 0.7, -3.4);
  const top = new DirectionalLight(0xffffff, 0);
  top.position.set(0, 8, 2.5);
  scene.add(rim, top);

  // ── the nine objects on the turntable ───────────────────────────────────
  // ring > slot (position on the ring, facing out) > lean (pointer) > turn (drag) > fit (scale to SIZE) > model
  const objects = projects.map((p, i) => {
    const slot = new Group();
    slot.rotation.y = i * STEP;
    const lean = new Group();
    const turn = new Group();
    const fit = new Group();
    ring.add(slot);
    slot.add(lean);
    lean.add(turn);
    turn.add(fit);
    return {
      name: p.object,
      slot,
      lean,
      turn,
      fit,
      loaded: false,
      model: null,
      beh: null, // this object's own small interaction (objects.js)
      fade: { value: 1 }, // 0 to 1, the shader uniform that darkens the object as it leaves the hero's side
      radius: SIZE / 2, // footprint radius, for the contact shadow
      size: { w: SIZE, h: SIZE }, // normalised size, once known
      appear: spring(1),
      spin: { ...spring(0), mode: 'idle', goal: 0 }, // mode: idle | drag | inertia | goal
    };
  });
  const fits = objects.map((o) => o.size);

  // ── the other three stations ────────────────────────────────────────────
  let wake = () => {};
  let warmed = false;
  const aniso = renderer.capabilities.getMaxAnisotropy();
  // What prepare() (common.js) needs of the studio: texture sharpness, and the metals, whose reflections are scaled apart.
  const look = { aniso, metals: new Set(), env: null };
  const ctx = {
    loadModel: (url) => loadModel(url, ac.signal, small() ? 1024 : 2048),
    wake: () => wake(),
    look,
    reduced: reducedMotion,
    wide: () => wide,
    width: () => mount.clientWidth,
    cursor: (on) => mount.toggleAttribute('data-hit', !!on),
    stepJob: (index) => stepTo('experience', index),
  };
  const stations = {
    education: createEducationStation(ctx),
    experience: createExperienceStation(ctx),
    links: createLinksStation(ctx),
  };
  const stationUrls = { education: [modelUrl('pennants')], experience: [modelUrl('badge'), modelUrl('patches')], links: [modelUrl('keys')] };
  const stationFits = { education: stations.education.size, experience: stations.experience.size, links: stations.links.size };
  // The same soft pool under what a station shows as under a project's object (the disc, dissolving outward into the floor), a little
  // dimmer, so that the five places read as one studio.
  const stationDiscs = {};
  for (const s of Object.values(stations)) {
    s.group.position.x = STATION_X[PLACE[s.id]];
    s.group.visible = false;
    scene.add(s.group);
    const material = discMaterial.clone();
    material.onBeforeCompile = discMaterial.onBeforeCompile;
    material.opacity = 0;
    const pool = new Mesh(disc.geometry, material);
    pool.rotation.x = -Math.PI / 2;
    pool.position.x = s.group.position.x;
    pool.scale.setScalar(SIZE * (s.id === 'experience' ? 2.4 : 1.3)); // the experience camera is close and low: it sees only the far part of a pool
    pool.receiveShadow = true;
    pool.visible = false;
    scene.add(pool);
    stationDiscs[s.id] = pool;
  }

  // ── state the loop chases ───────────────────────────────────────────────
  let route = 'other';
  let section = 'top';
  let tTarget = 0;
  let pTarget = 0;
  let first = true; // the first target is taken as it is, with no travel
  const ringT = spring(0);
  const pathP = spring(0);
  const focus = spring(0); // 1 on a project page: the camera comes closer
  const lead = spring(0); // -1 while the camera travels back toward an earlier place, 1 toward a later one: which end it arrives at first
  const lean = { x: spring(0), y: spring(0) };
  const ready = new Set(); // table objects that have drawn at least one frame
  const fresh = new Set(); // table objects added since the last frame
  const stationReady = new Set();
  const stationFresh = new Set();
  let aspect = 1;
  let raf = 0;
  let inMotion = false; // the camera or the ring is moving: setting up and freeing models waits for it to stop (an object fading in does not count)
  let cameraRest = true;
  let last = 0;
  let scrollY = window.scrollY;
  let scrollAt = performance.now();

  const turning = () => route === 'project';
  const active = () => (turning() ? frontIndex(tTarget) : -1);
  const leanOn = () => wide && !reducedMotion(); // the pointer service only ever reports fine pointers
  const place = () => Math.round(pTarget);
  const heroIndex = () => {
    if (place() !== 3) return -1;
    const i = frontIndex(ringT.x);
    return Math.abs(ringT.x - 1 - i) < 0.3 ? i : -1;
  };
  const heroStation = () => stations[{ 1: 'education', 2: 'experience', 4: 'links' }[place()]];

  /** The turntable's own framing numbers for the current scroll. */
  const camPose = () => path(pathP.x, ringT.x, focus.x, fits, stationFits, aspect, wide, lead.x);

  /** Move every spring on by `dt`. True while anything is still moving. */
  function step(dt) {
    const still = reducedMotion() || first;
    // A spring comes to rest exactly on its target, so the picture at rest is the same however the visitor got there.
    const go = (s, to, rate) => {
      if (still) return jump(s, to), true;
      chase(s, to, rate, dt);
      if (!settled(s, to, 1e-4)) return false;
      jump(s, to);
      return true;
    };
    let rest = true;
    const ringRest = go(ringT, tTarget, RING_RATE);
    const pathRest = go(pathP, pTarget, PATH_RATE);
    const focusRest = go(focus, turning() ? 1 : 0, FOCUS_RATE);
    const leadRest = go(lead, Math.sign(pTarget - pathP.x), RATE.key);
    cameraRest = ringRest && pathRest && focusRest;
    rest = ringRest && pathRest && focusRest && leadRest && rest;
    const l = leanOn() ? Math.min(1, 1 / Math.max(1e-6, Math.hypot(pointer.nx, pointer.ny))) : 0; // at most LEAN in all
    rest = go(lean.x, pointer.nx * LEAN * l, LEAN_RATE) && rest;
    rest = go(lean.y, pointer.ny * LEAN * l, LEAN_RATE) && rest;
    const a = active();
    objects.forEach((o, i) => {
      const s = o.spin;
      if (s.mode === 'drag') rest = false;
      else if (s.mode === 'inertia') {
        s.x += s.v * dt;
        s.v *= Math.exp(-FRICTION * dt);
        if (Math.abs(s.v) < 0.02) (s.v = 0), (s.mode = 'idle');
        rest = false;
      } else {
        // Anything not being turned goes home by the shortest way round.
        if (i !== a && s.mode === 'idle' && s.x !== 0) (s.mode = 'goal'), (s.goal = Math.round(s.x / TAU) * TAU);
        if (s.mode === 'goal') {
          if (still) jump(s, s.goal);
          else chase(s, s.goal, SPIN_RATE, dt);
          if (settled(s, s.goal)) {
            jump(s, i === a ? s.goal : 0);
            s.mode = 'idle';
          } else rest = false;
        }
      }
      rest = go(o.appear, o.loaded ? 1 : 0, APPEAR_RATE) && rest;
      // An object that has left the stage goes back to how it began (a torn page is whole again before it is seen).
      if (!o.slot.visible && o.wasVisible) o.beh?.reset?.();
      o.wasVisible = o.slot.visible;
      if (o.beh && o.slot.visible && o.beh.update(dt, { hero: i === heroIndex() || i === a })) rest = false;
    });
    for (const s of Object.values(stations)) if (s.ready && s.group.visible && s.update(dt)) rest = false;
    first = false;
    return !rest;
  }

  /** Is the table view on screen, which the twin camera draws (see draw())? */
  const atTable = () => tableness(ringT.x) > 0.5 && tableX(pathP.x) === 0;

  const target = new Vector3();
  /** Put the scene into the state the springs describe and draw it. */
  function draw() {
    const P = pathP.x;
    const u = tableness(ringT.x);
    const R = radius(ringT.x);
    const ringY = ringAngle(ringT.x);
    const px = tableX(P);
    const tw = weight(px === STATION_X[0] ? 0 : 3, P); // how present the table is
    ring.position.x = px;
    ring.rotation.y = ringY;
    ring.visible = tw > 0.004;
    // The disc is a plate with a rim to its fade: it dissolves early when the camera leaves it, while the objects stay to slide out of frame.
    discMaterial.opacity = tw * (px === STATION_X[0] ? 1 - smoothstep(0.05, 0.5, P) : P > 3 ? 1 - smoothstep(3, 3.5, P) : 1);
    disc.scale.setScalar(R + SIZE * 1.3);
    // A transparent surface at zero opacity is still drawn: its depth is written, and where it overlaps the floor (a few millimetres under it) that left
    // broken patches of floor missing round the keyboard while the camera was near the Links station. Off when it is not there.
    disc.visible = discMaterial.opacity > 0.004;
    const front = ringT.x - 1; // the ring position as an object index
    for (let i = 0; i < COUNT; i++) {
      const o = objects[i];
      const angle = i * STEP;
      const v = visibility(i, ringT.x) * tw;
      const grow = lerp(1, TABLE_SCALE, u) * lerp(0.9, 1, clamp(o.appear.x, 0, 1));
      const w = 1 - smoothstep(0, 0.6, Math.abs(i - front));
      o.slot.position.set(Math.sin(angle) * R, 0, Math.cos(angle) * R);
      o.slot.scale.setScalar(grow);
      o.lean.rotation.set(lean.y.x * w, lean.x.x * w, 0);
      o.fade.value = v;
      o.slot.visible = o.loaded && v > 0.03; // out of sight is out of the shadow too (below this it is a black silhouette on the lit floor, not a fade)
      const world = angle + ringY;
      // Round the table every object faces the camera, so none shows its back; at a project the ring's own facing returns.
      const facing = ((((world + Math.PI) % TAU) + TAU) % TAU) - Math.PI; // the way it faces, -pi to pi, 0 = at the camera
      o.turn.rotation.y = o.spin.x + PRESENT - facing * u;
      blobs[i].set(px + Math.sin(world) * R, Math.cos(world) * R, o.radius * grow * 1.1, o.loaded ? v : 0);
    }
    for (const s of Object.values(stations)) {
      const wgt = weight(PLACE[s.id], P);
      s.fade.value = wgt;
      const was = s.group.visible;
      s.group.visible = s.ready && wgt > 0.004;
      stationDiscs[s.id].visible = s.group.visible;
      stationDiscs[s.id].material.opacity = wgt * STATION_POOL;
      if (was && !s.group.visible) s.reset?.(); // out of sight, it goes back to how it first looked
    }

    // The camera: a point on a line rising at `pitch` from the target, looking at it.
    const c = camPose();
    const d = c.dist;
    camera.position.set(c.x + Math.sin(c.yaw) * Math.cos(c.pitch) * d, c.ty + Math.sin(c.pitch) * d, c.tz + Math.cos(c.yaw) * Math.cos(c.pitch) * d);
    camera.lookAt(c.x, c.ty, c.tz);
    // Tight clip planes keep depth precision high for the printed text standing a few hundredths of a millimetre proud.
    camera.near = d * 0.35;
    camera.far = d + 70;
    camera.updateProjectionMatrix();
    // Shift the picture (the table sits left and down, clear of the project index): a skew of the projection.
    const m = camera.projectionMatrix.elements;
    m[8] = -c.ox;
    m[9] = -c.oy;
    camera.projectionMatrixInverse.copy(camera.projectionMatrix).invert();
    floor.position.x = c.x;
    floorCentre.value.set(c.x, c.tz);

    // The lights: a tight pool on whatever the camera looks at; wide and even over the whole table when it is pulled back.
    const q = clamp(P, 0, 4);
    const i0 = Math.min(3, Math.floor(q));
    const k0 = q - i0;
    const light = (n) => {
      if (n === 0 || n === 3) {
        const uu = n === 0 ? 1 : u;
        const RR = n === 0 ? radius(0) : R;
        const seen = n === 3 ? Math.max(...objects.map((o, i) => (o.loaded ? visibility(i, ringT.x) : 0))) : 1;
        return { x: STATION_X[n] + lerp(0.55, 0, uu), z: lerp(RR - 0.25, 0, uu), dist: lerp(6, 9.5, uu), angle: lerp(POOL[0], POOL[1], uu), power: lerp(9, 4.2, uu) * lerp(0.3, 1, seen), top: uu * 0.9 };
      }
      return { x: STATION_X[n] + 0.4, z: 0, dist: 6.5, angle: 0.4, power: 9, top: 0 };
    };
    const A = light(i0);
    const B = light(i0 + 1);
    const mix = (k) => lerp(A[k], B[k], k0);
    key.target.position.set(mix('x'), 0, mix('z'));
    key.position.copy(key.target.position).addScaledVector(KEY_LIGHT, mix('dist'));
    key.angle = mix('angle');
    poolR.value = Math.tan(key.angle) * mix('dist') / 2.2;
    poolAt.value.set(key.target.position.x, key.target.position.z);
    // The pool of light on the floor is sized by what stands in it. Wide over the whole table when the ring is all there, but a
    // lone object, small in the picture while the camera is pulled back, stands in a pool that is small too and under it: not a
    // grey disc with a speck in it. At a project (u = 0, one object) this is exactly the designed pool.
    fadeScale.value = 1;
    fadeAt.value.set(0.5, 0.5);
    let reach = 0;
    if (tw > 0.004) {
      let sum = 0;
      let vmax = 0;
      let cx = 0;
      let cz = 0;
      for (let i = 0; i < COUNT; i++) {
        const v = objects[i].loaded ? visibility(i, ringT.x) * tw : 0;
        if (v < 0.03) continue; // what is drawn (o.slot.visible, above)
        const world = i * STEP + ringY;
        sum += v;
        vmax = Math.max(vmax, v);
        cx += v * (px + Math.sin(world) * R);
        cz += v * Math.cos(world) * R;
      }
      if (sum > 0) {
        // How much of the picture what is standing there takes: its reach on the floor, over the camera's reach at that distance,
        // against the same at a project. Less than that and the fade round it closes in on it.
        reach = 0;
        for (let i = 0; i < COUNT; i++) {
          const v = objects[i].loaded ? visibility(i, ringT.x) * tw : 0;
          if (v < 0.03) continue; // what is drawn (o.slot.visible, above)
          const world = i * STEP + ringY;
          const dx = px + Math.sin(world) * R - cx / sum;
          const dz = Math.cos(world) * R - cz / sum;
          reach = Math.max(reach, Math.hypot(dx, dz) + objects[i].radius * lerp(1, TABLE_SCALE, u));
        }
        // The same for the object that stands there most, framed as it is at its own project: so at a project this is exactly 1.
        let best = 0;
        for (let i = 1; i < COUNT; i++) if ((objects[i].loaded ? visibility(i, ringT.x) : 0) > (objects[best].loaded ? visibility(best, ringT.x) : 0)) best = i;
        const rest = path(3, best + 1, 0, fits, stationFits, aspect, wide, 0).dist;
        const half = Math.tan((FOV * Math.PI) / 360);
        const frac = reach / (c.dist * half);
        const fracRest = objects[best].radius / (rest * half);
        const s = clamp(frac / fracRest, 0.25, 1);
        fadeScale.value = lerp(1, s, tw);
        camera.updateMatrixWorld();
        camera.matrixWorldInverse.copy(camera.matrixWorld).invert();
        const here = new Vector3(cx / sum, SIZE * 0.25, cz / sum).project(camera);
        const follow = (1 - fadeScale.value) / 0.75;
        fadeAt.value.set(lerp(0.5, here.x * 0.5 + 0.5, follow), lerp(0.5, here.y * 0.5 + 0.5, follow));
        const crowd = smoothstep(0, 3, sum - vmax); // 0 for one object, 1 when the ring is there
        const alone = POOL_ALONE * lerp(1, TABLE_SCALE, u);
        const sigma = lerp(alone, poolR.value, crowd);
        const shift = (1 - crowd) * u * tw;
        poolR.value = lerp(poolR.value, sigma, tw);
        poolAt.value.x = lerp(poolAt.value.x, cx / sum + POOL_OFFSET[0], shift);
        poolAt.value.y = lerp(poolAt.value.y, cz / sum + POOL_OFFSET[1], shift);
      }
    }
    key.intensity = mix('power') * tuning.key;
    rim.intensity = 3 * tuning.rim;
    scene.environmentIntensity = scene.userData.envBase * tuning.env;
    for (const m of look.metals) m.envMapIntensity = scene.environmentIntensity * tuning.metal;
    renderer.toneMappingExposure = tuning.exposure;
    key.target.updateMatrixWorld();
    top.intensity = mix('top') * tuning.top * (0.4 + 0.6 * fadeScale.value); // a lone object far away gets less of the fill

    // Depth of field, only while the camera travels between stations: focused on what it looks at.
    target.set(c.x, c.ty, c.tz);
    post.setFocus(target, Math.max(0.8, d * 0.3));
    post.setBlur(Math.min(1, Math.abs(P - Math.round(P)) * 2.4));

    // What is seen through glass (the screens) is drawn at more than the picture's resolution so it stays as sharp as the
    // screen itself; at the table view, with nine objects and nothing to read, it drops to save the fill (2560 px at DPR 2:
    // 24 ms a frame at the full scale, 17 ms at the small one). Resizing the transmission buffer is an 80 to 130 ms stall, and
    // each camera has a buffer of its own: so the table view is drawn from a twin camera that always keeps the small one.
    const overview = atTable();
    if (overview) {
      overviewCamera.copy(camera, false);
      overviewCamera.updateMatrixWorld();
    }
    post.setSceneCamera(overview ? overviewCamera : camera);
    renderer.transmissionResolutionScale = overview ? OVERVIEW_SCALE : wide ? 1.75 : 1.25;

    if (!warmed) {
      // The depth of field is only on mid-travel: draw it once, unseen, so its shaders are compiled before they are needed.
      warmed = true;
      post.setBlur(1);
      post.render(0);
    }
    post.render(1 / 60);
    countFrame();
    for (const i of fresh) ready.add(i);
    fresh.clear();
    for (const s of stationFresh) stationReady.add(s);
    stationFresh.clear();
    showWhenReady();
  }

  /** The canvas fades in over the still only once what the visitor is looking at has drawn. */
  function showWhenReady() {
    const p = place();
    const there = p === 0 ? ready.size > 0 : p === 3 ? ready.has(frontIndex(tTarget)) : stationReady.has({ 1: 'education', 2: 'experience', 4: 'links' }[p]);
    canvas.toggleAttribute('data-ready', !!there);
  }

  function frame(now) {
    raf = 0;
    if (dead || lost || isHidden()) return;
    const dt = last ? Math.min(Math.max((now - last) / 1000, 0), 1 / 20) : 1 / 60;
    last = now;
    const moving = step(dt);
    inMotion = !cameraRest;
    draw();
    if (moving) raf = requestAnimationFrame(frame);
    else last = 0;
  }
  wake = () => {
    if (started && !raf && !dead && !lost) raf = requestAnimationFrame(frame);
  };

  // ── size ────────────────────────────────────────────────────────────────
  function resize() {
    const w = mount.clientWidth;
    const h = mount.clientHeight;
    if (!w || !h) return;
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, wide ? 2 : 1.5));
    renderer.setSize(w, h, false);
    post.setSize(w, h);
    renderer.getDrawingBufferSize(resolution.value);
    aspect = w / h;
    camera.aspect = aspect;
    first = true; // a new frame size is a new composition: no travel
    wake();
  }
  const ro = new ResizeObserver(resize);
  ro.observe(mount);
  try {
    ro.observe(mount, { box: 'device-pixel-content-box' }); // also fires when only the pixel ratio changes (the same window on another display, the browser zoomed)
  } catch {
    /* not in every browser: the resolution query below covers most of it */
  }
  cleanups.push(() => ro.disconnect());
  const onWide = () => {
    wide = mq.matches;
    key.shadow.mapSize.setScalar(wide ? 2048 : 1024);
    key.shadow.map?.dispose();
    key.shadow.map = null;
    resize();
  };
  mq.addEventListener('change', onWide);
  cleanups.push(() => mq.removeEventListener('change', onWide));
  // The pixel ratio can change with the size unchanged (a window dragged to another display, the browser zoomed): the buffer
  // is then the wrong size for the screen, and blurry or wasteful, so it is made again.
  let dprWatch = null;
  const watchDpr = () => {
    dprWatch?.mq.removeEventListener('change', dprWatch.fn);
    const mqd = matchMedia(`(resolution: ${window.devicePixelRatio}dppx)`);
    const fn = () => {
      resize();
      watchDpr();
    };
    mqd.addEventListener('change', fn);
    dprWatch = { mq: mqd, fn };
  };
  watchDpr();
  cleanups.push(() => dprWatch?.mq.removeEventListener('change', dprWatch.fn));
  // Some browsers say nothing when a window moves to another display: so the ratio is also looked at whenever the visitor does
  // anything (scrolls, moves the pointer, comes back to the tab), and the buffer made again if it no longer matches.
  const ensureRatio = () => {
    const want = Math.min(window.devicePixelRatio || 1, wide ? 2 : 1.5);
    if (started && Math.abs(renderer.getPixelRatio() - want) > 0.01) resize();
  };
  on(window, 'focus', ensureRatio);

  // ── the scroll target ───────────────────────────────────────────────────
  let settle = 0;
  function apply(p, frameTime) {
    ensureRatio();
    const now = performance.now();
    const y = window.scrollY;
    const speed = ((y - scrollY) / Math.max(8, now - scrollAt)) * 1000; // px per second
    scrollY = y;
    scrollAt = now;
    route = p.route;
    section = p.section;
    tTarget = Math.min(p.t, COUNT); // past the last project the ring stays put: nothing of it is wanted at the links, and turning it would swing the last object off the front as it leaves
    pTarget = p.p;
    mount.toggleAttribute('data-turn', turning());
    stations.education.setStep?.(p.step);
    stations.experience.setJob?.(p.job, p.within, p.point, p.pointFrac);
    if (Math.abs(speed) > 30) {
      stations.education.nudge?.({ scroll: speed });
      stations.experience.nudge?.({ scroll: speed });
    }
    showWhenReady();
    if (reducedMotion()) {
      // No travel: the scene jumps to the target once scrolling has stopped, and draws once.
      clearTimeout(settle);
      settle = setTimeout(wake, 140);
    } else if (frameTime !== undefined && started && !raf && !dead && !lost && !isHidden()) {
      // Called from the same animation frame the scroll was read in: draw now, so the picture moves in the very frame the
      // text does. (Waking would draw one frame later, and the text would be a frame ahead of the stage.)
      frame(frameTime);
    } else wake();
    reconcile();
  }
  cleanups.push(() => clearTimeout(settle));

  /** Scroll the text so step `index` of `id`'s section is on the focus line (the arrow keys and badge clicks). */
  function stepTo(id, index) {
    const el = document.getElementById(id)?.querySelectorAll('[data-step]')[index];
    if (!el) return;
    scrollToTarget(scrollYFor(el), { smooth: !reducedMotion() });
  }

  // ── picking: a ray from the pointer, tested against the active station's hit boxes ──
  const ray = new Raycaster();
  const ndc = new Vector2();
  const aim = (e) => {
    const r = canvas.getBoundingClientRect();
    ndc.set(((e.clientX - r.left) / r.width) * 2 - 1, -(((e.clientY - r.top) / r.height) * 2 - 1));
    ray.setFromCamera(ndc, camera);
  };
  /** What the pointer is over: { kind: 'station' | 'object', who, id } or null. */
  function pickAt(e) {
    aim(e);
    const s = heroStation();
    if (s) {
      const id = s.pick(ray);
      return id === null || id === undefined ? null : { who: s, id };
    }
    const i = heroIndex();
    const o = objects[i];
    if (o?.beh && o.slot.visible) {
      const id = o.beh.pick(ray);
      return id === null || id === undefined ? null : { who: o.beh, id, object: o };
    }
    return null;
  }

  // ── pointer: hover, press, drag, tap ────────────────────────────────────
  let hovered = null; // { who, id }
  let press = null; // { who, id, x, y, t, moved, pointerId, turn }
  const setHover = (hit) => {
    if (hovered?.who === hit?.who && hovered?.id === hit?.id) return;
    hovered?.who.hover?.(null);
    hovered = hit;
    hit?.who.hover?.(hit.id);
    mount.toggleAttribute('data-hit', !!hit);
    wake();
  };
  let drag = null; // turning the object on a project page
  on(mount, 'pointermove', (e) => {
    if (e.pointerType === 'mouse' && !press) setHover(pickAt(e));
    if (press && e.pointerId === press.pointerId) {
      if (Math.hypot(e.clientX - press.x, e.clientY - press.y) > TAP) press.moved = true;
      press.who.move?.(e, press.id);
    }
    if (drag && e.pointerId === drag.id) {
      const o = objects[active()];
      if (!o) return;
      const dx = e.clientX - drag.x;
      const dt = Math.max(1, e.timeStamp - drag.time) / 1000;
      o.spin.x += dx * DRAG;
      drag.v = lerp(drag.v, (dx * DRAG) / dt, 0.5); // smoothed angular velocity, rad/s
      drag.x = e.clientX;
      drag.time = e.timeStamp;
      o.beh?.drag?.(dx, e.clientY - drag.y, dt);
      wake();
    }
  });
  on(mount, 'pointerleave', (e) => e.pointerType === 'mouse' && !press && setHover(null));
  on(mount, 'pointerdown', (e) => {
    if (!e.isPrimary || (e.pointerType === 'mouse' && e.button !== 0)) return;
    const hit = pickAt(e);
    const o = objects[active()];
    if (hit || o) mount.setPointerCapture(e.pointerId);
    if (hit) {
      press = { ...hit, x: e.clientX, y: e.clientY, t: e.timeStamp, moved: false, pointerId: e.pointerId };
      hit.who.down?.(hit.id, e);
    }
    if (o && !drag) {
      drag = { id: e.pointerId, x: e.clientX, y: e.clientY, time: e.timeStamp, v: 0 };
      o.spin.mode = 'drag';
      o.spin.v = 0;
    }
    wake();
  });
  const release = (e) => {
    if (press && e.pointerId === press.pointerId) {
      const tap = !press.moved && e.timeStamp - press.t < TAP_TIME && e.type === 'pointerup';
      press.who.up?.(press.id, e);
      if (tap) press.who.click?.(press.id, e);
      // A touch that starts to scroll the page is cancelled by the browser: what it did before that still counts as a swipe.
      if (e.type === 'pointercancel') press.who.swipe?.(press.id, e.clientX - press.x, e.clientY - press.y);
      press = null;
      if (e.pointerType !== 'mouse') setHover(null);
    }
    if (drag && e.pointerId === drag.id) {
      const o = objects[active()] ?? objects.find((x) => x.spin.mode === 'drag');
      if (o) {
        const recent = e.timeStamp - drag.time < 80; // a drag that stopped before the release carries no momentum
        o.spin.v = recent && !reducedMotion() ? clamp(drag.v, -8, 8) : 0;
        o.spin.mode = o.spin.v ? 'inertia' : 'idle';
      }
      drag = null;
    }
    wake();
  };
  on(mount, 'pointerup', release);
  on(mount, 'pointercancel', release);
  on(mount, 'keydown', (e) => {
    if (e.altKey || e.ctrlKey || e.metaKey) return;
    const i = turning() ? active() : heroIndex();
    const o = objects[i];
    if ((e.key === 'Enter' || e.key === ' ') && o?.beh) {
      e.preventDefault();
      o.beh.activate?.();
      wake();
      return;
    }
    const dir = { ArrowLeft: -1, ArrowRight: 1 }[e.key];
    const t = objects[active()];
    if (!t || !dir) return;
    e.preventDefault();
    t.spin.goal = (t.spin.mode === 'goal' ? t.spin.goal : t.spin.x) + dir * KEY;
    t.spin.v = 0;
    t.spin.mode = 'goal';
    wake();
  });
  // Arrow keys step the jobs while the work experience is on the stage (the text scrolls to the job).
  on(window, 'keydown', (e) => {
    if (section !== 'experience' || route !== 'home' || e.altKey || e.ctrlKey || e.metaKey || e.shiftKey) return;
    if (/^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement?.tagName ?? '') || document.activeElement?.isContentEditable) return;
    const dir = { ArrowLeft: -1, ArrowRight: 1 }[e.key];
    if (!dir) return;
    const job = stations.experience.currentJob?.() ?? 0;
    const next = clamp(job + dir, 0, 2);
    if (next === job) return;
    e.preventDefault();
    stepTo('experience', next);
  });

  // Pointer speed over the stage nudges the pennants and the badges.
  let lastPointer = null;
  cleanups.push(
    onPointer((e) => {
      if (e.type !== 'pointermove') return void (lastPointer = null);
      const r = mount.getBoundingClientRect();
      const inside = e.clientX >= r.left && e.clientX <= r.right && e.clientY >= r.top && e.clientY <= r.bottom;
      if (inside && lastPointer && !press) {
        const dt = Math.max(8, e.timeStamp - lastPointer.t) / 1000;
        const v = { px: (e.clientX - lastPointer.x) / dt, py: (e.clientY - lastPointer.y) / dt };
        if (section === 'education') stations.education.nudge({ ...v });
        else if (section === 'experience') stations.experience.nudge({ ...v });
        else if (section === 'projects') objects[heroIndex()]?.beh?.nudge?.(v);
      }
      lastPointer = inside ? { x: e.clientX, y: e.clientY, t: e.timeStamp } : null;
      ensureRatio();
      if (leanOn()) wake();
    }),
  );

  // ── residency: what is in memory ────────────────────────────────────────
  // A model is loaded only when the visitor is within a step of it, and let go of when they are more than two steps away.
  // The steps, in the order the page goes: 0 the intro, 1 education, 2 experience, 3 to 11 the nine projects, 12 the links.
  // The turntable shows all nine at once at the intro (and while it comes round at the first project), so then each is held
  // small ("low": textures at most LOW px); an object is held at full detail ("high") only while it is the front one or a
  // neighbour of it. A small stage or a small device holds both at smaller sizes. A load is finished (compiled, textures
  // uploaded) before the object can be seen: nothing pops in; until then the still stays.
  const STOP = { education: 1, experience: 2, links: 12 };
  const small = () => !wide || mount.clientWidth < 700 || (navigator.deviceMemory ?? 8) <= 4;
  const capHigh = () => (small() ? 1024 : 2048);
  const capLow = () => (small() ? 384 : 512);
  const stepNow = () => {
    const pl = place();
    return pl === 0 ? 0 : pl === 1 ? 1 : pl === 2 ? 2 : pl === 4 ? 12 : 2 + clamp(Math.round(tTarget), 1, 9);
  };
  const dHigh = (i, cur) => Math.abs(3 + i - cur);
  /** Should what is held for `key` at `level` still be held at step `cur`? */
  function keeps(key, level, cur) {
    if (typeof key !== 'number') return Math.abs(STOP[key] - cur) <= 2;
    return level === 'high' ? dHigh(key, cur) <= 2 || cur <= 4 : cur <= 4;
  }
  /** What should be held at step `cur`, nearest first: { key, level, d }. */
  function wanted(cur) {
    const out = [];
    for (const id of STATIONS) if (stationUrls[id][0] && Math.abs(STOP[id] - cur) <= 1) out.push({ key: id, level: 'high', d: Math.abs(STOP[id] - cur) });
    for (let i = 0; i < COUNT; i++) {
      if (!urls[i]) continue;
      if (dHigh(i, cur) <= 1) out.push({ key: i, level: 'high', d: dHigh(i, cur) });
      else if (cur <= 3) out.push({ key: i, level: 'low', d: (cur === 0 ? 0.2 : 1 + cur * 0.1) + i * 0.01 }); // at the intro they are what is on screen: no waiting for a quiet moment
    }
    return out.sort((x, y) => x.d - y.d);
  }
  const sizeDefaults = Object.fromEntries(Object.entries(stations).map(([id, s]) => [id, { ...s.size }]));
  const held = new Map(); // key -> 'low' | 'high' | 'station': what is loaded and ready
  const failedAt = new Map(); // `key:level` -> when it last failed to load: not tried again for a while (a blocked file must not be fetched in a loop)
  const RETRY = 30000;
  const TRIES = 3; // a file that keeps failing is asked for this many times in all, then left alone
  const failures = new Map(); // `key:level` -> how many times it has failed
  /** How long a file is left alone after its last failure: a few seconds after the first (a dropped request), RETRY after that. */
  const pause = (id) => ((failures.get(id) ?? 0) <= 1 ? 3000 : RETRY);
  const busy = new Set(); // keys being loaded
  let inflight = 0;
  let evictTimer = 0;
  const retryTimers = new Set(); // one per failure: each wakes reconcile() when that file's pause is over
  cleanups.push(() => clearTimeout(evictTimer), () => retryTimers.forEach(clearTimeout));

  function unloadObject(i) {
    const o = objects[i];
    o.loaded = false;
    ready.delete(i);
    fresh.delete(i);
    o.beh?.dispose?.();
    o.beh = null;
    if (o.model) {
      o.model.traverse((m) => {
        for (const x of [m.material].flat()) x && look.metals.delete(x);
      });
      disposeModel(o.model);
      o.model = null;
    }
    // As if it had never been loaded: its place in the ring is its own, its size is the default until it is loaded again.
    o.fit.scale.setScalar(1);
    o.fit.position.set(0, 0, 0);
    o.size.w = o.size.h = SIZE;
    o.radius = SIZE / 2;
    held.delete(i);
    markReady(o.name, false);
  }

  function unloadStation(id) {
    const s = stations[id];
    const models = s.models ?? [];
    s.unload?.();
    s.group.visible = false;
    for (const m of models) {
      m.traverse((n) => {
        for (const x of [n.material].flat()) x && look.metals.delete(x);
      });
      disposeModel(m);
    }
    for (const k of Object.keys(s.size)) delete s.size[k]; // back to what the camera assumes of a station that is not there
    Object.assign(s.size, sizeDefaults[id]);
    stationReady.delete(id);
    stationFresh.delete(id);
    held.delete(id);
    markReady(id, false);
  }

  /** Resolve once nothing on screen is moving (or the stage is over). */
  const quiet = async () => {
    while (inMotion && !dead && !lost) await new Promise((resolve) => setTimeout(resolve, 100));
  };

  /**
   * The visitor is looking at something that is not at full detail yet (a jump straight to a project, an index click, a link):
   * with the camera at rest nothing moves that a long frame could spoil, so its set-up takes bigger bites and does not wait for
   * the GPU between textures. Anything that is not on screen keeps the gentle budget.
   */
  function urgent() {
    if (inMotion) return false;
    const s = stepNow();
    const key = s === 1 ? 'education' : s === 2 ? 'experience' : s === 12 ? 'links' : s - 3;
    return s !== 0 && held.get(key) !== (typeof key === 'number' ? 'high' : 'station');
  }
  const bite = (calm) => (urgent() ? 12 : calm);

  /** Resolve once the GPU has executed everything issued so far (a fence polled once a frame, at most 30 frames). */
  async function drained() {
    const gl = renderer.getContext();
    if (typeof gl.fenceSync !== 'function') return new Promise((resolve) => requestAnimationFrame(resolve));
    const fence = gl.fenceSync(gl.SYNC_GPU_COMMANDS_COMPLETE, 0);
    gl.flush();
    for (let i = 0; i < 30 && !dead && !lost; i++) {
      await new Promise((resolve) => requestAnimationFrame(resolve));
      if (gl.getSyncParameter(fence, gl.SYNC_STATUS) === gl.SIGNALED) break;
    }
    gl.deleteSync(fence);
  }

  /**
   * Upload a big texture (1024 px and over) in stripes of about 1 MB, a frame at a time, instead of one call: a single 2048 px
   * texSubImage2D from a bitmap was measured at 30 to 70 ms on a cold page, and still 20 to 40 ms for a first stripe of one;
   * from pixel bytes a stripe is 1 to 2 ms. The memory is allocated by three.js with its data held back (`dataReady`). Resolves true when it did the upload, false (nothing done) for a texture it does not handle.
   */
  async function uploadTiled(v) {
    const img = v.image;
    const W = img?.width;
    const H = img?.height;
    const gl = renderer.getContext();
    const plain = v.isTexture && !v.isDataTexture && !v.isCompressedTexture && !v.isCubeTexture && !v.isVideoTexture && !v.isCanvasTexture;
    if (!plain || typeof ImageBitmap === 'undefined' || !(img instanceof ImageBitmap) || Math.max(W, H) < 1024) return false;
    if (v.flipY || v.mipmaps.length || v.format !== RGBAFormat || v.type !== UnsignedByteType || typeof createImageBitmap !== 'function') return false;
    if (typeof OffscreenCanvas !== 'function') return false;
    const rows = Math.max(64, Math.floor(1048576 / (W * 4)));
    // The storage first, while the image still has its size (three.js reads it here); it is moved to the worker after.
    const source = v.source;
    source.dataReady = false;
    try {
      renderer.initTexture(v); // storage only
    } finally {
      source.dataReady = true;
    }
    const tex = renderer.properties.get(v).__webglTexture;
    // The bytes of each stripe are read in the pixel worker; without one, on this thread.
    const id = pixels.newId();
    let remote = await pixels.ready();
    if (remote) {
      try {
        // The bitmap moves to the worker for the length of the upload (cloning it costs the main thread tens of ms) and comes back.
        await pixels.send({ op: 'open', bitmap: img, rows }, id, [img]);
      } catch (error) {
        remote = false;
        if (error.bitmap) v.source.data = error.bitmap;
      }
    }
    let local = null;
    if (!remote) {
      local = new OffscreenCanvas(W, rows).getContext('2d', { willReadFrequently: true });
      if (!local) {
        v.needsUpdate = true; // no way to read it in stripes: let three.js upload it whole
        return false;
      }
      local.globalCompositeOperation = 'copy';
    }
    const stripeOf = async (y, hh) => {
      if (remote) {
        const { px, opaque, stripe } = await pixels.send({ op: 'stripe', y, height: hh }, id);
        return { px, opaque, stripe };
      }
      local.drawImage(img, 0, y, W, hh, 0, 0, W, hh);
      const px = local.getImageData(0, 0, W, hh).data;
      const words = new Uint32Array(px.buffer, px.byteOffset, px.length >> 2);
      let opaque = true;
      for (let i = 0; i < words.length; i++) {
        if (words[i] >>> 24 !== 255) {
          opaque = false;
          break;
        }
      }
      return { px, opaque, stripe: null };
    };
    try {
      let t0 = performance.now();
      for (let y = 0; y < H; y += rows) {
        await quiet();
        if (dead || lost || renderer.properties.get(v).__webglTexture !== tex) return true;
        const hh = Math.min(rows, H - y);
        const { px, opaque, stripe } = await stripeOf(y, hh);
        renderer.state.bindTexture(gl.TEXTURE_2D, tex);
        // These are GL-wide settings that other uploads leave as they like, and they apply to bytes: flipped or premultiplied
        // stripes (orange screws, a lighter block on the plate, after the 3D switch had been used) were what a stale value did.
        renderer.state.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false);
        renderer.state.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, false);
        renderer.state.pixelStorei(gl.UNPACK_COLORSPACE_CONVERSION_WEBGL, gl.NONE);
        renderer.state.pixelStorei(gl.UNPACK_ALIGNMENT, 4);
        if (opaque) {
          gl.texSubImage2D(gl.TEXTURE_2D, 0, 0, y, W, hh, gl.RGBA, gl.UNSIGNED_BYTE, px);
        } else {
          // Pixels that are not opaque cannot make the round trip through a canvas unchanged (it keeps them premultiplied): such
          // a stripe goes up from a cropped bitmap instead, which is exact.
          const crop = stripe ?? (await createImageBitmap(img, 0, y, W, hh, { premultiplyAlpha: 'none', colorSpaceConversion: 'none' }));
          gl.texSubImage2D(gl.TEXTURE_2D, 0, 0, y, gl.RGBA, gl.UNSIGNED_BYTE, crop);
          crop.close();
        }
        if (performance.now() - t0 > bite(4)) {
          await new Promise((resolve) => requestAnimationFrame(resolve));
          t0 = performance.now();
        }
      }
    } catch {
      // The bitmap was freed under us (the model was let go): nothing left to upload.
      return true;
    } finally {
      if (remote) {
        try {
          const { bitmap } = await pixels.send({ op: 'close' }, id);
          // Back from the worker: it is the texture's image again, unless the texture has been let go meanwhile. (Waited for, so
          // that warm() can free the images of everything it has uploaded.)
          if (bitmap) {
            if (renderer.properties.get(v).__webglTexture === tex) v.source.data = bitmap;
            else bitmap.close();
          }
        } catch {
          /* the worker is gone: the bitmap with it */
        }
      }
    }
    if (v.generateMipmaps) {
      renderer.state.bindTexture(gl.TEXTURE_2D, tex);
      gl.generateMipmap(gl.TEXTURE_2D);
    }
    return true;
  }

  /** Compile a model's shaders and upload its textures now, off screen, so that showing it later costs nothing. */
  async function warm(root) {
    // Programs are keyed by the target they draw into (its colour space), and the scene is drawn into the composer's buffer, not the
    // canvas: compiling for the canvas built the wrong variants, which were then built again, blocking, on the first real draw.
    // The compile requests are issued synchronously by this call, so the target only needs to be set for its duration.
    // One mesh at a time, a frame let through whenever 3 ms have gone: assembling a program's source is main-thread work, and a
    // whole station at once was a 50 ms task (200 ms with the CPU slowed 4x).
    const target = renderer.getRenderTarget();
    const meshes = [];
    root.traverse((m) => {
      if (m.isMesh || m.isPoints || m.isLine || m.isSprite) meshes.push(m);
    });
    letGoOfGeometry(meshes);
    const compiling = [];
    let c0 = performance.now();
    for (const m of meshes) {
      if (dead || lost) return;
      renderer.setRenderTarget(post.composer.inputBuffer);
      try {
        compiling.push(renderer.compileAsync(m, camera, scene));
      } finally {
        renderer.setRenderTarget(target);
      }
      if (performance.now() - c0 > bite(3)) {
        await new Promise((resolve) => requestAnimationFrame(resolve));
        c0 = performance.now();
      }
    }
    await Promise.all(compiling);
    const textures = new Set();
    const programs = new Set();
    root.traverse((m) => {
      for (const x of [m.material].flat()) {
        if (!x) continue;
        const program = renderer.properties.get(x).currentProgram;
        if (program) programs.add(program);
        for (const v of Object.values(x)) if (v?.isTexture && v !== look.env) textures.add(v);
      }
    });
    // A linked program still has to be read back (its uniforms and attributes, 5 ms each) the first time it is drawn: done here,
    // one or two at a time, instead of all at once inside the first frame it is seen in.
    let t0 = performance.now();
    for (const program of programs) {
      await quiet();
      if (dead || lost) return;
      program.getUniforms();
      program.getAttributes();
      if (performance.now() - t0 > 3) {
        await new Promise((resolve) => requestAnimationFrame(resolve));
        t0 = performance.now();
      }
    }
    // Uploading a texture is a stall: a few at a time, and then a frame is let through, so that nothing on screen stutters.
    t0 = performance.now();
    for (const v of textures) {
      await quiet(); // an upload is a stall: never while the camera is moving
      if (dead || lost) return;
      if (await uploadTiled(v)) {
        // The next big upload waits until the GPU has finished this one (and the mipmaps made from it).
        if (!urgent()) await drained();
        t0 = performance.now();
      } else {
        renderer.initTexture(v);
        if (performance.now() - t0 > bite(3)) {
          await new Promise((resolve) => requestAnimationFrame(resolve));
          t0 = performance.now();
        }
      }
    }
    await quiet();
    if (dead || lost) return;
    freeImages(textures);
    prime(root);
  }

  /**
   * Once a mesh's buffers are on the GPU nothing reads them here again (the hit volumes are boxes of their own, sizes and bounds
   * are taken at load, and the depth and shadow passes draw from the GPU's copy), so each buffer lets go of its array right
   * after its upload. The bounds that culling would otherwise make from the array, later, are made first.
   */
  function letGoOfGeometry(meshes) {
    const free = function () {
      this.array = null; // `this` is the buffer: three calls onUploadCallback on the attribute (or the interleaved buffer) it has just uploaded
    };
    for (const m of meshes) {
      const g = m.geometry;
      if (!g?.attributes || g.userData.letGo) continue;
      g.userData.letGo = true;
      if (!g.boundingSphere) g.computeBoundingSphere();
      if (!g.boundingBox) g.computeBoundingBox();
      // A skinned mesh has bounds of its own (it is sorted by them in its first draw, right after its buffers go up).
      if (m.boundingSphere === null) m.computeBoundingSphere();
      if (m.boundingBox === null) m.computeBoundingBox();
      for (const a of [g.index, ...Object.values(g.attributes)]) (a?.isInterleavedBufferAttribute ? a.data : a)?.onUpload(free);
    }
  }

  /**
   * The textures are on the GPU: the decoded bitmaps behind them (16 MB each at 2048 px) are not needed again, so they are freed
   * now instead of with the model. A bitmap is shared by every texture made from it, so it goes only when all of those are up.
   */
  function freeImages(textures) {
    const up = (v) => renderer.properties.get(v).__webglTexture !== undefined;
    const sources = new Map();
    for (const v of textures) sources.set(v.source, (sources.get(v.source) ?? true) && up(v));
    for (const [source, done] of sources) if (done && typeof ImageBitmap !== 'undefined' && source.data instanceof ImageBitmap) source.data.close();
  }

  /**
   * Draw `root` once, in the real scene's lights, into the composer's own input buffer (so that no render target is resized and
   * nothing reaches the screen): this is what uploads its geometry and binds everything the first time, which would otherwise be
   * a stall of tens of milliseconds the first time it is on screen. The next real frame overwrites the buffer.
   */
  function prime(root) {
    const inScene = root.parent === scene;
    const meshes = [];
    root.traverse((m) => {
      if (m.isMesh) meshes.push([m, m.frustumCulled]);
    });
    for (const [m] of meshes) m.frustumCulled = false;
    const was = root.visible;
    root.visible = true;
    if (!inScene) scene.add(root);
    const target = renderer.getRenderTarget();
    renderer.setRenderTarget(post.composer.inputBuffer);
    const scale = renderer.transmissionResolutionScale;
    const glass = meshes.some(([m]) => m.material?.transmission > 0);
    try {
      // The transmission buffer of each camera is sized by the scale in force when it is drawn: this draw must use the scale the
      // camera will have when it is seen, or the first real frame resizes (reallocates) it, which was a 80 to 110 ms frame of GPU
      // time on the way into the first project.
      if (atTable()) {
        // The table view is drawn by the twin camera, so that is the one primed, and its buffer is the only one made: the main
        // camera's is 1.75 times the picture on each side (some 490 MB at a retina stage) and nothing at the table ever uses it.
        overviewPrimed ||= glass;
        overviewCamera.copy(camera, false);
        overviewCamera.updateMatrixWorld();
        renderer.transmissionResolutionScale = OVERVIEW_SCALE;
        renderer.render(scene, overviewCamera);
      } else {
        renderer.transmissionResolutionScale = wide ? 1.75 : 1.25;
        renderer.render(scene, camera);
        if (!overviewPrimed && glass) {
          // The table view's twin camera has a transmission buffer of its own: made now, drawn once, not on the way into the first
          // project (a 30 to 120 ms frame).
          overviewPrimed = true;
          overviewCamera.copy(camera, false);
          overviewCamera.updateMatrixWorld();
          renderer.transmissionResolutionScale = OVERVIEW_SCALE;
          renderer.render(scene, overviewCamera);
        }
      }
    } finally {
      renderer.transmissionResolutionScale = scale;
      renderer.setRenderTarget(target);
      if (!inScene) scene.remove(root);
      root.visible = was;
      for (const [m, c] of meshes) m.frustumCulled = c;
    }
    // In WebKit the first frame the composer draws after this comes out black outside the objects (the second is right), and with
    // the stage at rest that frame is the one left on screen: a black box. Two frames in this one task, of which only the last is
    // ever presented, take that frame here.
    post.render(0);
    post.render(0);
  }

  async function loadObject(i, level) {
    const o = objects[i];
    const model = await loadModel(urls[i], ac.signal, level === 'high' ? capHigh() : capLow());
    if (level === 'low' || stepNow() !== 3 + i) await quiet(); // what is not on screen yet is set up while everything is still
    if (dead || lost || !keeps(i, level, stepNow())) return disposeModel(model);
    // Normalise by bounding box: the largest dimension becomes SIZE, the footprint is centred, the base sits on the disc.
    const n = normalise(model, o.fit, SIZE);
    let beh = null;
    prepare(model, {
      fade: o.fade,
      ...look,
      // Glass drawn over glass cannot show what is inside it (a transmissive surface does not see another one), so the
      // flask's blue liquid would vanish: it is drawn as a glossy opaque blue instead, which is how it reads in the still.
      // Clear glass is sampled from the sharpest level of the transmission buffer: even 0.03 roughness blurs what is
      // behind it (the screens under their cover glass) by half a mip.
      tweak: (x) => {
        if (x.name === 'Liquid') x.transmission = 0;
        if (x.transmission > 0 && !x.roughnessMap && x.roughness < 0.06) x.roughness = 0;
      },
      extend: (shader, x, m) => beh?.extend?.(shader, x, m),
    });
    beh = createBehaviour(o.name, model, ctx, { scale: n.k });
    // Off screen first: shaders compiled, textures uploaded, and only then does it replace what was there.
    const staging = new Group();
    staging.add(model);
    await warm(staging);
    if (dead || lost || !keeps(i, level, stepNow())) {
      beh?.dispose?.();
      return disposeModel(model);
    }
    const isNew = !o.model;
    if (!isNew) {
      // A full-detail copy replaces the small one. Letting the small one go puts the object's place back to "never loaded" (its
      // scale and its footing, which normalise() has just set for the new model): so they are set again, or the object stays at the
      // size the file came in, a speck in the pool of light, until it is next loaded.
      const scale = o.fit.scale.clone();
      const position = o.fit.position.clone();
      unloadObject(i);
      o.fit.scale.copy(scale);
      o.fit.position.copy(position);
    }
    o.size.w = n.w;
    o.size.h = n.h;
    o.radius = n.radius;
    o.model = model;
    o.beh = beh;
    o.fit.add(model);
    o.fit.visible = true;
    // An object that arrives while the canvas is still hidden is simply there; one that arrives after it grows in a little.
    if (!isNew || !canvas.hasAttribute('data-ready')) jump(o.appear, 1);
    else o.appear.x = 0;
    o.loaded = true;
    held.set(i, level);
    fresh.add(i);
    markReady(o.name, true);
    if (i === frontIndex(tTarget) && !canvas.hasAttribute('data-ready')) first = true; // its real size reframes the camera unseen
    wake();
  }

  async function loadStation(id) {
    const s = stations[id];
    await s.load(...stationUrls[id]);
    await quiet();
    if (dead || lost || !keeps(id, 'high', stepNow())) {
      // Gone out of range while it loaded: give it straight back.
      for (const m of s.models ?? []) disposeModel(m);
      s.unload?.();
      return;
    }
    // Everything the station will draw is compiled and uploaded before it can be seen: no hitch, no texture pop-in. (Its group
    // stays hidden: shaders are compiled from the tree, shown or not.)
    await warm(s.group);
    if (dead || lost || !keeps(id, 'high', stepNow())) {
      const models = s.models ?? [];
      s.unload?.();
      for (const m of models) disposeModel(m);
      return;
    }
    s.ready = true;
    held.set(id, 'station');
    stationFresh.add(id);
    markReady(id, true);
    if (PLACE[id] === place() && !canvas.hasAttribute('data-ready')) first = true;
    wake();
  }

  /** Bring what is held into line with where the visitor is: let go of what is too far, start what is near and missing. */
  function reconcile() {
    if (dead || lost) return;
    const cur = stepNow();
    // Freeing textures stalls the GPU for a moment (150 ms was measured), so it waits until nothing is moving.
    if (inMotion) {
      clearTimeout(evictTimer);
      evictTimer = setTimeout(reconcile, 500);
    } else {
      for (const [key, level] of [...held]) {
        if (!busy.has(key) && !keeps(key, level === 'station' ? 'high' : level, cur)) (typeof key === 'number' ? unloadObject : unloadStation)(key);
      }
    }
    for (const w of wanted(cur)) {
      if (inflight >= 3) break;
      const have = held.get(w.key);
      if (busy.has(w.key) || have === 'station' || have === 'high' || (have === 'low' && w.level === 'low')) continue;
      const id = `${w.key}:${w.level}`;
      if (performance.now() - (failedAt.get(id) ?? -Infinity) < pause(id)) continue;
      run(w);
    }
  }

  /** Is this still among what is wanted now? */
  const wantedNow = (w) => wanted(stepNow()).some((x) => x.key === w.key && x.level === w.level);

  async function run(w) {
    busy.add(w.key);
    inflight++;
    try {
      if (w.d > 0.5) {
        // What is not yet needed waits for a quiet moment, and for the picture to be still: parsing and uploading take tens of
        // milliseconds, which would show as a stutter in a camera move.
        await idle();
        while (inMotion && !dead && !lost && stepNow() !== undefined && wantedNow(w)) await new Promise((resolve) => setTimeout(resolve, 150));
      }
      if (dead || lost) return;
      await (typeof w.key === 'number' ? loadObject(w.key, w.level) : loadStation(w.key));
    } catch (err) {
      const id = `${w.key}:${w.level}`;
      failedAt.set(id, performance.now());
      if (!dead && !ac.signal.aborted) {
        console.warn(`stage: ${typeof w.key === 'number' ? objects[w.key].name : w.key} not loaded`, err);
        // Nothing else wakes the stage while the visitor is at rest, so without this a file that failed once (a dropped request
        // while the page was still settling) was never asked for again until the next scroll, and the canvas stayed away.
        const n = (failures.get(id) ?? 0) + 1;
        failures.set(id, n);
        if (n < TRIES) {
          const timer = setTimeout(() => (retryTimers.delete(timer), reconcile()), pause(id) + 50);
          retryTimers.add(timer);
        }
      }
    } finally {
      busy.delete(w.key);
      inflight--;
      reconcile();
    }
  }

  // ── context loss, and teardown ──────────────────────────────────────────
  on(canvas, 'webglcontextlost', (e) => {
    e.preventDefault(); // allows the context to come back
    if (lost || dead) return;
    lost = true;
    const restored = new Promise((resolve) => canvas.addEventListener('webglcontextrestored', resolve, { once: true }));
    dispose(true);
    onLost?.(restored.then(() => canvas.getContext('webgl2')?.getExtension('WEBGL_lose_context')?.loseContext()));
  });

  function dispose(isLost = false) {
    if (dead) return;
    dead = true;
    cancelAnimationFrame(raf);
    ac.abort();
    for (const fn of cleanups.splice(0)) fn();
    try {
      // Everything the stage loaded is given back: the models' textures (GPU and decoded images), the downloaded files.
      objects.forEach((o, i) => o.model && unloadObject(i));
      for (const [id, s] of Object.entries(stations)) {
        if (s.models?.length) unloadStation(id);
        s.dispose?.();
      }
      clearReady();
      clearBuffers();
      clearHot('key', 'stage');
      clearHot('patch', 'stage');
      disposeTree(scene);
      look.metals.clear();
      envTarget?.dispose();
      post.dispose();
      key.shadow.map?.dispose();
    } finally {
      // Whatever above failed, the canvas goes and the context is handed back: a stage that is off must not draw.
      renderer.dispose();
      if (!isLost) renderer.forceContextLoss();
      canvas.remove();
      mount.removeAttribute('data-turn');
      mount.removeAttribute('data-hit');
    }
  }

  try {
    envTarget = await makeEnvironment(renderer, scene);
    look.env = envTarget.texture;
    // The floor reflects the studio only faintly (a material's own envMap is what envMapIntensity scales).
    for (const m of [floor.material, disc.material, ...Object.values(stationDiscs).map((d) => d.material)]) {
      m.envMap = envTarget.texture;
      m.envMapIntensity = 0.2;
    }
  } catch (err) {
    dispose();
    throw err;
  }
  // Stopped while the studio's light was being made: nothing was shown, so nothing is left behind.
  if (dead || signal?.aborted) {
    dispose();
    return { dispose };
  }
  if (import.meta.env.DEV || import.meta.env.VITE_DBG) window.__dbg = { fadeScale, fadeAt, poolR, poolAt, lead, frames: framesDrawn, progress: getProgress, ringT, pathP, focus, objects, stations, camera, scene, key, rim, top, post, renderer, floorMaterial, discMaterial, tuning, get tTarget() { return tTarget; }, get pTarget() { return pTarget; }, draw: () => (wake(), draw()), pickAt: (x, y) => pickAt({ clientX: x, clientY: y })?.id ?? null }; // development only
  canvas.setAttribute('aria-hidden', 'true');
  mount.append(canvas);
  started = true;
  cleanups.push(startSmooth(), onProgress(apply), onReducedMotion(() => wake()), onVisibility((hidden) => !hidden && wake()));
  resize();
  apply(getProgress());
  return { dispose: () => dispose(false) };
}
