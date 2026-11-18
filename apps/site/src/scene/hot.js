/**
 * What the visitor is pointing at, shared by the text column and the stage: a keycap or a patch, by id. The HTML link or
 * bullet sets it on hover and focus, the stage sets it when the pointer is over the object, and each side lights up
 * for what the other points at. Three-free and React-free.
 *
 *   getHot()         -> { kind: 'key' | 'patch' | null, ids: string[], owner }
 *   setHot(kind, ids, owner) / clearHot(kind, owner)
 *   onHot(fn)        -> unsubscribe
 */
const NONE = { kind: null, ids: [], owner: null };
let hot = NONE;
const subs = new Set();

export const getHot = () => hot;
export const onHot = (fn) => (subs.add(fn), () => subs.delete(fn));

const same = (a, b) => a.kind === b.kind && a.owner === b.owner && a.ids.length === b.ids.length && a.ids.every((id, i) => id === b.ids[i]);

export function setHot(kind, ids, owner = 'text') {
  const next = kind && ids.length ? { kind, ids, owner } : NONE;
  if (same(hot, next)) return;
  hot = next;
  for (const fn of subs) fn(hot);
}

/**
 * Clear the highlight, but only if it still belongs to `kind` and to `owner` ('text' for the page's links and bullets, 'stage'
 * for the canvas): a hover that has moved from the keycap to its own link must not be undone by the keycap's leave.
 */
export function clearHot(kind, owner = 'text') {
  if (hot.kind === kind && hot.owner === owner) setHot(null, []);
}
