/**
 * Shared page services, three-free: one listener each for the whole stage. A listener is attached when the first
 * subscriber arrives and removed when the last one leaves. Every `on…` returns its unsubscribe.
 *
 *   onPointer((e) => …)         PointerEvent: 'pointermove' on window, 'pointerleave' on <html>;
 *                               only where there is a fine hovering pointer, never for touch
 *   onReducedMotion((on) => …)  prefers-reduced-motion changed (it can change while the page is open)
 *   onVisibility((hidden) => …) the tab was hidden or shown
 *
 * Plus live state to read: reducedMotion(), isHidden(), `pointer`.
 */

/** A subscribe function whose `attach(emit)` runs for the first subscriber and whose result runs for the last. */
function channel(attach) {
  const subs = new Set();
  let detach = null;
  const emit = (arg) => {
    for (const s of subs) s.fn(arg);
  };
  return (fn) => {
    const sub = { fn }; // an object per call, so subscribing the same function twice is two subscriptions
    subs.add(sub);
    if (subs.size === 1) detach = attach(emit);
    return () => {
      if (subs.delete(sub) && !subs.size) {
        detach();
        detach = null;
      }
    };
  };
}

// ── reduced motion ───────────────────────────────────────────────────────
// Chrome drops the `change` event of a MediaQueryList whose `.matches` is read from a frame or a timer (12 toggles,
// 0 to 6 events delivered, measured). So the list that is listened to is never read, and everybody reads the value
// this listener keeps; it is seeded from a second list, read once. The listener exists only while somebody subscribes
// (the stage does, for as long as it is alive), and is attached afresh, with a fresh seed, each time.
const REDUCE = '(prefers-reduced-motion: reduce)';
let reduced = matchMedia(REDUCE).matches;
export const reducedMotion = () => reduced;
export const onReducedMotion = channel((emit) => {
  reduced = matchMedia(REDUCE).matches; // read once, from a list nothing listens to
  const watch = matchMedia(REDUCE); // listened to, and never read
  const change = (e) => {
    reduced = e.matches; // the event's own value, not a read of the list
    emit(reduced);
  };
  watch.addEventListener('change', change);
  return () => watch.removeEventListener('change', change);
});

// ── tab visibility ───────────────────────────────────────────────────────
export const isHidden = () => document.hidden;
export const onVisibility = channel((emit) => {
  const f = () => emit(document.hidden);
  document.addEventListener('visibilitychange', f);
  return () => document.removeEventListener('visibilitychange', f);
});

// ── pointer ──────────────────────────────────────────────────────────────
/** Last known pointer: client px, and -1…1 across the viewport (nx right, ny down). 0, 0 when it has left. */
export const pointer = { x: 0, y: 0, nx: 0, ny: 0, inside: false };
export const onPointer = channel((emit) => {
  const fine = matchMedia('(hover: hover) and (pointer: fine)');
  const root = document.documentElement;
  const move = (e) => {
    if (e.pointerType === 'touch') return;
    pointer.x = e.clientX;
    pointer.y = e.clientY;
    pointer.nx = (e.clientX / window.innerWidth) * 2 - 1;
    pointer.ny = (e.clientY / window.innerHeight) * 2 - 1;
    pointer.inside = true;
    emit(e);
  };
  const leave = (e) => {
    pointer.nx = pointer.ny = 0;
    pointer.inside = false;
    emit(e);
  };
  let on = false;
  const unlisten = () => {
    window.removeEventListener('pointermove', move);
    root.removeEventListener('pointerleave', leave);
    on = false;
  };
  const sync = () => {
    if (fine.matches === on) return;
    if (!fine.matches) return unlisten();
    window.addEventListener('pointermove', move, { passive: true });
    root.addEventListener('pointerleave', leave);
    on = true;
  };
  fine.addEventListener('change', sync); // a mouse docked to a tablet starts it, undocked stops it
  sync();
  return () => {
    fine.removeEventListener('change', sync);
    unlisten();
  };
});
