/**
 * Small physics for the stage, three-free: damped pendulums and springs stepped at a fixed rate, so the motion does not
 * depend on the frame rate and cannot blow up. Nothing here allocates per step.
 *
 *   const p = pendulum({ k: 90, c: 5 })      // an angle held by a spring of stiffness k, damped by c (per second)
 *   push(p, 3)                                // an impulse: change of angular velocity (rad/s)
 *   advance(p, dt)                            // steps at FIXED_DT; true while the pendulum is still moving
 */

/** The fixed step (seconds). 120 Hz is stable for every stiffness used here (k up to a few hundred). */
export const FIXED_DT = 1 / 120;
/** Past this many fixed steps in one frame the rest of the time is dropped: a tab that was away does not fast-forward. */
const MAX_STEPS = 12;
/** A pendulum at rest: both its angle and its speed are below these. */
const REST_ANGLE = 4e-4;
const REST_SPEED = 2e-3;

/** A damped spring on one angle (radians), pulled toward `rest` (default 0). `limit` clamps the angle. */
export const pendulum = ({ k = 80, c = 5, limit = 1.2, rest = 0 } = {}) => ({ x: 0, v: 0, k, c, limit, rest, acc: 0, held: false });

/** Kick the pendulum: add `dv` rad/s. Clamped, so no input can inject unbounded energy. */
export function push(p, dv, max = 12) {
  p.v = Math.max(-max, Math.min(max, p.v + (Number.isFinite(dv) ? dv : 0)));
}

/**
 * Step by `dt` seconds (any size) in fixed steps, semi-implicit Euler: the speed is updated first, then the angle from
 * the new speed. Energy is clamped at the angle limit and the pendulum is snapped to rest once it is below the
 * thresholds, so it always settles. A held pendulum (being dragged) does not move on its own.
 * Returns true while it is still moving.
 */
export function advance(p, dt) {
  if (p.held) return true;
  p.acc = Math.min(p.acc + dt, FIXED_DT * MAX_STEPS);
  while (p.acc >= FIXED_DT) {
    p.acc -= FIXED_DT;
    p.v += (-p.k * (p.x - p.rest) - p.c * p.v) * FIXED_DT;
    p.x += p.v * FIXED_DT;
    if (p.x > p.limit) (p.x = p.limit), (p.v = Math.min(0, p.v));
    else if (p.x < -p.limit) (p.x = -p.limit), (p.v = Math.max(0, p.v));
  }
  if (!Number.isFinite(p.x) || !Number.isFinite(p.v)) (p.x = p.rest), (p.v = 0);
  if (Math.abs(p.x - p.rest) < REST_ANGLE && Math.abs(p.v) < REST_SPEED) {
    p.x = p.rest;
    p.v = 0;
    return false;
  }
  return true;
}

/** Grab: the pendulum follows `angle` exactly while held, and the speed it had at the last move is kept for the release. */
export function hold(p, angle, dt = FIXED_DT) {
  const x = Math.max(-p.limit, Math.min(p.limit, angle));
  p.v = dt > 0 ? Math.max(-12, Math.min(12, (x - p.x) / dt)) : 0;
  p.x = x;
  p.held = true;
}

export const release = (p) => {
  p.held = false;
  p.acc = 0;
};
