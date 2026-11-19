/**
 * Three-free helpers the stage wrappers import statically. Nothing here may import `three`:
 * everything else in this folder is reached only through dynamic import().
 */

let webgl2;

/**
 * THE OBJECTS SWITCH: the visitor's off switch for every 3D object, `<html data-objects="off">`. index.html sets it
 * before first paint (from localStorage, or `?objects=off` for one load) and setObjects() flips it. While it is off
 * canGoLive() is false, and the stage wrappers follow it live (components/Objects.jsx): they dispose their views
 * and show what they show without WebGL.
 */
export const objectsOn = () => document.documentElement.dataset.objects !== 'off';

const watchers = new Set();
/** Call `fn(on)` whenever the switch is flipped; returns the unsubscribe. */
export function onObjects(fn) {
  watchers.add(fn);
  return () => watchers.delete(fn);
}

/** Flip the switch and keep the choice: the key is stored only while it is off. */
export function setObjects(on) {
  const html = document.documentElement;
  if (on) delete html.dataset.objects;
  else html.dataset.objects = 'off';
  try {
    if (on) localStorage.removeItem('objects');
    else localStorage.setItem('objects', 'off');
  } catch {
    /* not persisted in private mode */
  }
  for (const fn of watchers) fn(on);
}

/**
 * What of the 3D is really there, so that the page only promises what it can do. The stage marks each object (by its
 * name) and station (education, experience, links) ready once it is loaded, compiled and drawable, and clears them all when
 * it goes. Three-free; components read it with the hooks in components/Objects.jsx.
 */
const readyNames = new Set();
const readyWatchers = new Set();
let readyVersion = 0;
export const isReady = (name) => readyNames.has(name);
export const onReady = (fn) => (readyWatchers.add(fn), () => readyWatchers.delete(fn));
export const readyVersionNow = () => readyVersion;
export function markReady(name, on) {
  if (readyNames.has(name) === on) return;
  on ? readyNames.add(name) : readyNames.delete(name);
  readyVersion++;
  for (const fn of readyWatchers) fn();
}
export function clearReady() {
  if (!readyNames.size) return;
  readyNames.clear();
  readyVersion++;
  for (const fn of readyWatchers) fn();
}

/** The stage's state as the switch should show it: 'off', 'loading', 'live', or 'unavailable' (no usable WebGL, or it failed). */
let status = 'off';
const statusWatchers = new Set();
export const getStatus = () => status;
export const onStatus = (fn) => (statusWatchers.add(fn), () => statusWatchers.delete(fn));
function setStatus(next) {
  if (status === next) return;
  status = next;
  for (const fn of statusWatchers) fn();
}

let frames = 0;
/** Called by the studio once per frame it draws (stage.js). */
export const countFrame = () => frames++;
/** Frames drawn by any view since the page loaded: only ever goes up, so a reader can tell whether anything is moving. */
export const framesDrawn = () => frames;

/**
 * True when hardware WebGL 2 is available, the visitor has not asked to save data and has not switched the
 * objects off. A software rasteriser counts as unavailable. Call it from an effect.
 */
export function canGoLive() {
  if (!objectsOn() || navigator.connection?.saveData) return false;
  if (webgl2 === undefined) {
    try {
      const gl = document.createElement('canvas').getContext('webgl2', { failIfMajorPerformanceCaveat: true });
      webgl2 = !!gl;
      gl?.getExtension('WEBGL_lose_context')?.loseContext(); // hand the probe context straight back
    } catch {
      webgl2 = false;
    }
  }
  return webgl2;
}

const buffers = new Map(); // url → { promise, refs, ac, done }

/**
 * Fetch a file once per URL for the page session; later callers share the same promise (the files are
 * small .glb models). Each caller has its own `signal`: aborting one rejects only that caller's promise,
 * and the request itself is cancelled only when every caller still waiting has aborted. A failed or
 * cancelled fetch is forgotten, so the next caller starts a new one. Wrappers call this to start the
 * download in parallel with the three chunk; loadModel() (models.js) then picks the same fetch up.
 */
export function fetchBuffer(url, signal) {
  if (signal?.aborted) return Promise.reject(signal.reason);
  const entry = buffers.get(url) ?? startFetch(url);
  entry.refs++;
  return new Promise((resolve, reject) => {
    const onAbort = () => {
      if (!entry.done && --entry.refs === 0) {
        entry.ac.abort();
        if (buffers.get(url) === entry) buffers.delete(url);
      }
      reject(signal.reason);
    };
    signal?.addEventListener('abort', onAbort, { once: true });
    entry.promise.then(
      (buf) => {
        signal?.removeEventListener('abort', onAbort);
        resolve(buf);
      },
      (err) => {
        signal?.removeEventListener('abort', onAbort);
        reject(err);
      },
    );
  });
}

/** Forget one downloaded file, once it has been parsed: the parsed model does not keep it, and a later load asks the browser's cache again. */
export function forgetBuffer(url) {
  const entry = buffers.get(url);
  if (entry?.done) buffers.delete(url);
}

/** Forget every downloaded file: the stage has gone, and the ArrayBuffers (a dozen MB) go with it. The browser's own cache still holds the files. */
export function clearBuffers() {
  for (const entry of buffers.values()) if (!entry.done) entry.ac.abort();
  buffers.clear();
}

function startFetch(url) {
  const entry = { ac: new AbortController(), refs: 0, done: false };
  entry.promise = fetch(url, { signal: entry.ac.signal }).then((r) => {
    if (!r.ok) throw new Error(`${url}: ${r.status}`);
    return r.arrayBuffer();
  });
  entry.promise.then(
    () => (entry.done = true),
    () => buffers.get(url) === entry && buffers.delete(url),
  );
  buffers.set(url, entry);
  return entry;
}

const painted = () => performance.getEntriesByName('first-contentful-paint').length > 0;

/**
 * Run `fn` once the page has loaded, has painted for the first time, and the browser is idle, so none
 * of the three work (chunk, model, GL context) competes with first paint. Returns a cancel function.
 */
export function whenIdle(fn) {
  let done = false;
  let started = false;
  let id;
  let po;
  let fallback;
  const idle = 'requestIdleCallback' in window;
  const run = () => {
    if (!done) {
      done = true;
      fn();
    }
  };
  const go = () => {
    if (started) return;
    started = true;
    po?.disconnect();
    clearTimeout(fallback);
    id = idle ? requestIdleCallback(run, { timeout: 1500 }) : setTimeout(run, 200);
  };
  const afterLoad = () => {
    if (painted()) return go();
    try {
      po = new PerformanceObserver(() => painted() && go());
      po.observe({ type: 'paint', buffered: true });
      fallback = setTimeout(go, 2500); // a browser that never reports paint timing must not wait forever
    } catch {
      go();
    }
  };
  if (document.readyState === 'complete') afterLoad();
  else window.addEventListener('load', afterLoad, { once: true });
  return () => {
    done = true;
    window.removeEventListener('load', afterLoad);
    po?.disconnect();
    clearTimeout(fallback);
    if (idle) cancelIdleCallback(id);
    else clearTimeout(id);
  };
}

/** Settles when the stage that was last started has let go of the GPU and of the shared parsed models (see startLive). */
let busy = Promise.resolve();

/**
 * Put the live stage into `mount` once the page has painted and is idle, when 3D is allowed. `onState(true)` when the
 * canvas is up, `onState(false)` when it is gone (switched off, WebGL lost, or it could not start); the stills the
 * caller keeps underneath are the fallback in every case. A lost context is rebuilt from scratch when it comes back.
 * Returns the stop function: it disposes the stage and cancels anything pending.
 *
 * Starts are strictly one after another: a start waits for the stage before it to be gone, whatever state that one was
 * in (still loading its environment, half way through a model), because the studio's globals (the ready names, the
 * downloaded files, the highlight) are shared and a stage that is still unwinding must never clear what the next one has
 * made. Stopping aborts a start that is under way; `busy` is let go only when that start has really finished (its
 * `finally`), never by the stop itself.
 */
export function startLive(mount, onState) {
  let stage = null;
  let gone = false;
  let release = () => {};
  const ac = new AbortController();
  setStatus(objectsOn() ? 'loading' : 'off');
  async function run() {
    if (gone) return;
    if (!canGoLive()) return setStatus(objectsOn() ? 'unavailable' : 'off');
    const before = busy;
    busy = new Promise((resolve) => (release = resolve));
    const mine = release;
    try {
      await before;
      if (gone) return;
      const { createStage } = await import('./stage.js');
      if (gone) return;
      const made = await createStage(mount, { onLost: (restored) => onLost(restored, mine), signal: ac.signal });
      if (gone) return made.dispose();
      stage = made;
      setStatus('live');
      onState(true);
    } catch (err) {
      if (gone) return;
      console.warn('The 3D stage could not start; showing the stills.', err);
      setStatus('unavailable');
      onState(false);
    } finally {
      // A start that did not end with a stage in hand leaves nobody to wait for.
      if (!stage) mine();
    }
  }
  function onLost(restored, mine) {
    stage = null;
    mine();
    setStatus('loading');
    onState(false);
    if (!gone) restored.then(() => !gone && run());
  }
  const cancel = whenIdle(run);
  return () => {
    gone = true;
    ac.abort();
    cancel();
    // A stage in hand goes now, and only then may the next start begin. A start still inside createStage lets go of `busy` itself
    // (run's finally), after it has disposed what it made: releasing here would let a second renderer be built beside it. The
    // release is in a finally, so a dispose that throws cannot leave `busy` held for the rest of the session.
    const held = stage;
    stage = null;
    try {
      held?.dispose();
    } finally {
      if (held) release();
      setStatus('off');
      onState(false);
    }
  };
}
