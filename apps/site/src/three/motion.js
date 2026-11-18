/**
 * Motion maths for the stage, three-free. Everything here chases a target: there are no fixed clips, so a target
 * that moves mid-flight (the visitor scrubbing back and forth) is simply followed from wherever the value is.
 */

export const clamp = (x, lo, hi) => Math.min(hi, Math.max(lo, x));
export const lerp = (a, b, k) => a + (b - a) * k;
export const smoothstep = (a, b, x) => {
  const k = clamp((x - a) / (b - a), 0, 1);
  return k * k * (3 - 2 * k);
};

/**
 * The stage's spring families, natural frequencies in rad/s (about 4 / omega seconds to settle): the camera is slow and
 * heavy, whole objects are medium, parts of an object are quick and a key or a lifted patch is quicker still. Every
 * critically damped chase in the stage uses one of these, so everything on screen moves in the same language.
 */
export const RATE = { camera: 4.2, ring: 5.5, object: 7, part: 12, quick: 20, key: 26 };

/** A critically damped spring's state: position `x`, velocity `v` (per second). */
export const spring = (x = 0) => ({ x, v: 0 });

/**
 * Step a spring toward `target` by `dt` seconds with natural frequency `omega` (rad/s; about 4 / omega seconds to
 * settle). Critically damped, so it never overshoots, and solved exactly, so the result does not depend on the frame rate.
 */
export function chase(s, target, omega, dt) {
  const e = Math.exp(-omega * dt);
  const d = s.x - target;
  const k = (s.v + omega * d) * dt;
  s.x = target + (d + k) * e;
  s.v = (s.v - omega * k) * e;
  return s.x;
}

/** Is the spring at rest on `target`, to well under a pixel, and moving by less than a pixel a second? Used to stop drawing frames. */
export const settled = (s, target, eps = 2e-3) => Math.abs(s.x - target) < eps && Math.abs(s.v) < eps * 6; // the speed allowed is looser: at 4 rad/s it is a fraction of a pixel a second

/** Put a spring on `target` with no motion. */
export function jump(s, target) {
  s.x = target;
  s.v = 0;
}
