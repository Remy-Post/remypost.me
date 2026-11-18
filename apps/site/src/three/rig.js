/**
 * Where the camera and the stations are for a given scroll position, three-free. The stage chases these numbers; nothing
 * here moves anything. Units are metres; the camera looks down -z at the front of the ring, which is at (0, 0, radius).
 *
 * The page has five camera places (scene/progress.js `p`): 0 the intro (the whole table from above), 1 education,
 * 2 work experience, 3 the turntable up close, 4 the links. They sit STATION_SPACING apart along x, and the camera
 * travels along that line, so a move between two is one continuous slide in which the object being left slips out of
 * the light and out of frame while the next one slides in. The table is one object that waits at place 0 and
 * is moved to place 3 while nothing of it can be seen.
 *
 * Between two places the camera also rises and draws back (ARC), so that for the middle of the move both places are in
 * frame, small, and the stage is never empty: it is a crane move, not a pan across bare floor.
 */
import { lerp, smoothstep } from './motion.js';

export const COUNT = 9; // objects on the ring
export const STEP = (40 * Math.PI) / 180; // the ring turns this far per project
export const SIZE = 1; // an object's largest dimension once normalised
export const FOV = 26; // vertical, degrees
const TAN = Math.tan((FOV * Math.PI) / 360);
const rad = (deg) => (deg * Math.PI) / 180;

/** The ring is wide while one object is in focus (its neighbours are far away) and closes up for the table view. */
const RING_FAR = 3.1;
const RING_NEAR = 2;
/** At the table view the objects are drawn a little larger, so nine of them still read. */
export const TABLE_SCALE = 1.15;

/** How much of the stage's height the front object fills, and the most of its width it may take. */
const FILL_H = 0.56;
const FILL_W = 0.6;
/** The crane between two places: extra distance as a multiple of the gap crossed, and extra pitch in degrees. */
const ARC = 1.35;
const ARC_PITCH = 8;
/** How strongly the camera's x runs ahead toward where it is going (1 is not at all). */
const LEAD = 3.2;
/** On a project page the camera comes closer. */
const CLOSER = 0.9;

/**
 * Where the camera looks along x at each of the five places. Education and work are a frame's width apart and the
 * links a frame's width from the table; education stands clear of the ring the intro's table makes (a few metres across),
 * so it never appears among the objects.
 */
export const STATION_X = [0, 4.2, 5.6, 11.4, 12.8];
/** Where the table stands: at the intro's place, then at the turntable's. */
export const tableX = (p) => (p < 1.5 ? STATION_X[0] : STATION_X[3]);

/**
 * How present place `i` is at path position `p`, 0 to 1. The small stations stay nearly whole until the camera is
 * half way to the next place and are gone as it arrives there; they are close enough that each is mostly out of frame by
 * then, so across a move one slides out as the next slides in and the stage is never empty. The table is large and
 * fills the frame, so it gives way quickly when the camera leaves it (it would otherwise loom over the next station),
 * and arrives gradually from far away when the camera comes to it.
 */
export const weight = (i, p) => {
  const d = Math.abs(p - i);
  if (i === 0 || i === 3) return 1 - (i === 3 && p < 3 ? smoothstep(0.3, 1, d) : smoothstep(0.55, 1, d));
  return 1 - smoothstep(0.35, 1, d);
};

/** The ring's rotation (radians about y) for ring position `t`: at t = n, object n stands at the front. */
export const ringAngle = (t) => -(t - 1) * STEP;

/** Index (0-8) of the object at the front for `t`, however far past the ends t has gone. */
export const frontIndex = (t) => Math.min(COUNT, Math.max(1, Math.round(t))) - 1;

/** 0 while the camera is in close on the objects, 1 when it is pulled back to show the whole table (t = 0 and 10). */
export const tableness = (t) => (t < 1 ? 1 - smoothstep(0, 1, t) : 0);

/** The radius of the ring at `t`. */
export const radius = (t) => lerp(RING_FAR, RING_NEAR, tableness(t));

/**
 * How visible object `i` is at ring position `t`, 0 to 1: the object at the front is fully there, its neighbours are dissolving
 * out as it goes and in as they come, and every object is back at the table view.
 */
export function visibility(i, t) {
  let d = Math.abs(i - (Math.min(t, COUNT) - 1)) % COUNT; // past the last project the ring keeps turning but nothing new comes round to the front
  d = Math.min(d, COUNT - d); // distance round the ring, in objects
  // Two objects dissolve into one another about the middle between them, so that at rest the nearer is always shown (half
  // and half at the exact middle) and the stage is never empty; the one after next is gone before it reaches the hero.
  return Math.max(1 - smoothstep(0.3, 0.7, d), tableness(t));
}

/** The distance at which an object of normalised size `{ w, h }` fills the stage as intended. */
function fitDistance({ w, h }, aspect) {
  return Math.max(h / (FILL_H * 2 * TAN), w / (FILL_W * aspect * 2 * TAN));
}

/**
 * The camera's pose as numbers it can be damped on: `dist` from the target along a line rising at `pitch` (radians),
 * the target's height `ty` and depth `tz`, and `ox`, `oy`, a shift of the picture in half-frames (the table is moved
 * left and down so the project index at the stage's top right stays clear of it). `fits[i]` is object i's normalised
 * size; `focus` is 1 on a project page; `beside` is true when the stage is beside the text, where the index is.
 */
export function pose(t, focus, fits, aspect, beside) {
  const a = Math.min(COUNT - 1, Math.max(0, t - 1));
  const i = Math.min(COUNT - 2, Math.floor(a));
  const k = smoothstep(0, 1, a - i); // an object's framing holds while it is at the front and moves between
  const dist = lerp(fitDistance(fits[i], aspect), fitDistance(fits[i + 1], aspect), k) * lerp(1, CLOSER, focus);
  const ty = lerp(fits[i].h, fits[i + 1].h, k) * 0.46;
  const closeNarrow = Math.min(0.4, Math.max(0, 1 - aspect)); // a stage narrower than tall (a window about 1024 wide) has less room left of the index
  const close = { dist, pitch: lerp(rad(14), rad(11), focus), ty, tz: radius(t), ox: beside ? -0.1 - 1.4 * closeNarrow : 0, oy: 0 }; // a little left of centre where the project index sits at the right
  // The whole table: the ring and the objects on it inside the frame, seen from above, nine objects across the stage.
  const pitch = rad(44);
  const reach = RING_NEAR + SIZE * TABLE_SCALE * 0.7;
  const width = (2 * reach) / (0.86 * aspect);
  const depth = (2 * reach * Math.sin(pitch) + SIZE * TABLE_SCALE * Math.cos(pitch)) / 0.84;
  // A narrower stage gives the project index (top right) a larger share of it, so the table moves further left and down.
  const narrow = Math.min(0.4, Math.max(0, 1 - aspect));
  const table = { dist: (Math.max(width, depth) / (2 * TAN)) * (1 + 0.5 * narrow), pitch, ty: 0.2, tz: 0, ox: beside ? -0.04 - 0.55 * narrow : 0, oy: beside ? -0.12 - 0.95 * narrow : 0 };
  const u = tableness(t);
  return {
    dist: lerp(close.dist, table.dist, u),
    pitch: lerp(close.pitch, table.pitch, u),
    ty: lerp(close.ty, table.ty, u),
    tz: lerp(close.tz, table.tz, u),
    ox: lerp(close.ox, table.ox, u),
    oy: lerp(close.oy, table.oy, u),
  };
}

/**
 * A close view of a station's object, `fit` its normalised size: the distance that fills the stage as intended, and the
 * pitch and the share of the stage's height and width it may take.
 */
function stationView(fit, aspect, { pitch, fillH = 0.56, fillW = 0.6, mid = 0.46 }) {
  const dist = Math.max(fit.h / (fillH * 2 * TAN), fit.w / (fillW * aspect * 2 * TAN));
  // A station that frames part of itself says where (`cx` across, `ty` up); otherwise it is looked at in the middle.
  // A station that wants another angle says so (`pitch` in degrees, `yaw` in degrees, the camera swung to the side).
  return { dist, pitch: rad(fit.pitch ?? pitch), yaw: rad(fit.yaw ?? 0), ty: fit.ty ?? fit.h * mid, tz: 0, ox: 0, oy: 0, cx: fit.cx ?? 0 };
}

/** How each station is looked at. */
export const VIEW = {
  education: { pitch: 12, fillH: 0.62, fillW: 0.6 },
  experience: { pitch: 9, fillH: 0.94, fillW: 0.94 },
  links: { pitch: 38, fillH: 0.5, fillW: 0.74, mid: 0.5 },
};

/**
 * The camera's pose at path position `p` (0 to 4) for turntable position `t`: the five places' poses, blended by
 * the fraction of the way between two. `fits` are the table's objects' sizes, `stations` the other three's
 * ({ education, experience, links }). The result also carries `x`, where the camera looks along the path.
 */
export function path(p, t, focus, fits, stations, aspect, beside, lead = 0) {
  const q = Math.min(4, Math.max(0, p));
  const i = Math.min(3, Math.floor(q));
  const k = q - i; // p is already eased: a straight blend here, no second easing
  const place = (n) => {
    switch (n) {
      case 0:
        return pose(0, 0, fits, aspect, beside);
      case 1:
        return stationView(stations.education, aspect, VIEW.education);
      case 2:
        return stationView(stations.experience, aspect, VIEW.experience);
      case 3:
        return pose(t, focus, fits, aspect, beside);
      default:
        return stationView(stations.links, aspect, VIEW.links);
    }
  };
  const a = place(i);
  const b = place(i + 1);
  // The camera's x runs ahead toward wherever it is going (`lead`, -1 going back to 1 going forward, damped by the stage),
  // so the place it arrives at is centred while the crane is still drawn back: it arrives composed, never off to one side.
  const ahead = lerp(k ** LEAD, 1 - (1 - k) ** LEAD, (Math.max(-1, Math.min(1, lead)) + 1) / 2);
  const out = { x: lerp(STATION_X[i], STATION_X[i + 1], ahead) + lerp(a.cx ?? 0, b.cx ?? 0, k) };
  out.yaw = lerp(a.yaw ?? 0, b.yaw ?? 0, k);
  for (const key of ['dist', 'pitch']) out[key] = lerp(a[key], b[key], k);
  // Where it looks (height, depth, the picture's shift) runs ahead with x, so the place it comes to is centred, not up in a corner.
  for (const key of ['ty', 'tz', 'ox', 'oy']) out[key] = lerp(a[key], b[key], ahead);
  // The crane: back and up by a share of the gap being crossed, none at either end (zero slope there too).
  // The crane peaks a quarter of the way from where it set out and has all but come down when it arrives (m is the share of
  // the journey done, whichever way it goes), so the place it comes to is already close and composed, not still drawn back.
  const bump = (m) => (256 / 27) * m * (1 - m) ** 3; // peaks a quarter of the way, about 6% of it left at 80%
  const lift = lerp(bump(1 - k), bump(k), (Math.max(-1, Math.min(1, lead)) + 1) / 2); // zero at either end whatever the lead
  out.dist += ARC * Math.abs(STATION_X[i + 1] - STATION_X[i]) * lift;
  out.pitch += rad(ARC_PITCH) * lift;
  return out;
}
