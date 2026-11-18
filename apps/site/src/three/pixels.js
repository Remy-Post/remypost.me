/** Client of pixels.worker.js. Every call resolves with the worker's answer, or rejects; `available()` is false without a worker. */
let worker = null;
let failed = false;
let next = 1;
const waiting = new Map();

function start() {
  if (worker || failed) return worker;
  try {
    worker = new Worker(new URL('./pixels.worker.js', import.meta.url), { type: 'module' });
    worker.onmessage = ({ data }) => {
      const w = waiting.get(data.id);
      if (!w) return;
      waiting.delete(data.id);
      if (data.error) w.reject(Object.assign(new Error(data.error), { bitmap: data.bitmap }));
      else w.resolve(data);
    };
    worker.onerror = () => {
      // The worker could not run: everything waiting fails (callers fall back to the main thread) and it is not tried again.
      failed = true;
      worker = null;
      for (const w of waiting.values()) w.reject(new Error('pixel worker failed'));
      waiting.clear();
    };
  } catch {
    failed = true;
    worker = null;
  }
  return worker;
}

/** Send { op, ... } to the worker; `transfer` lists what moves with it. `id` ties a stripe reader to its opened bitmap. */
export function send(message, id = next++, transfer = []) {
  const w = start();
  if (!w) return Promise.reject(new Error('no pixel worker'));
  return new Promise((resolve, reject) => {
    waiting.set(id, { resolve, reject });
    w.postMessage({ ...message, id }, transfer);
  });
}

let probe = null;
/** Resolves true once the worker has answered a ping (so what is transferred to it will be received), false if there is none. */
export function ready() {
  if (typeof Worker !== 'function' || typeof OffscreenCanvas !== 'function' || typeof createImageBitmap !== 'function') return Promise.resolve(false);
  probe ??= send({ op: 'ping' }).then(() => true, () => false);
  return probe;
}

export const newId = () => next++;
