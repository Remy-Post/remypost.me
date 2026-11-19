import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';
import { fetchBuffer, forgetBuffer } from './live.js';
import * as pixels from './pixels.js';

// Decoding meshes (a few MB of wasm work per model) happens in workers of its own, not between two frames.
if (typeof Worker === 'function') MeshoptDecoder.useWorkers(Math.max(1, Math.min(3, (navigator.hardwareConcurrency || 4) - 2)));

/** Parse a .glb held in memory (meshopt-compressed, textures as WebP). Needs no GL context. */
const parse = (buffer) => new GLTFLoader().setMeshoptDecoder(MeshoptDecoder).parseAsync(buffer, '').then((gltf) => gltf.scene);

/** Reject when `signal` aborts, without disturbing `promise` or anyone else waiting on it. */
function abortable(promise, signal) {
  if (!signal) return promise;
  return new Promise((resolve, reject) => {
    if (signal.aborted) return reject(signal.reason);
    const onAbort = () => reject(signal.reason);
    signal.addEventListener('abort', onAbort, { once: true });
    promise.then(resolve, reject).finally(() => signal.removeEventListener('abort', onAbort));
  });
}

/**
 * Bring every texture of `scene` down to at most `cap` pixels on its longer side, before anything is uploaded: a 2048 px
 * RGBA texture is 22 MB on the GPU with its mips, and the models carry dozens. The decoded full-size bitmap is freed as soon
 * as the smaller one exists. Textures that are small enough are left alone.
 */
async function shrink(scene, cap) {
  const sources = new Set();
  scene.traverse((o) => {
    for (const m of [o.material].flat()) {
      if (!m) continue;
      for (const v of Object.values(m)) if (v?.isTexture && v.source) sources.add(v.source);
    }
  });
  await Promise.all(
    [...sources].map(async (src) => {
      const img = src.data;
      if (!img || !(img.width > cap || img.height > cap) || typeof createImageBitmap !== 'function') return;
      const k = cap / Math.max(img.width, img.height);
      const width = Math.max(1, Math.round(img.width * k));
      const height = Math.max(1, Math.round(img.height * k));
      let from = img;
      let small;
      try {
        // In the pixel worker when there is one: the bitmap moves there (and is closed there), it is not cloned.
        if (!(await pixels.ready())) throw new Error('no worker');
        small = (await pixels.send({ op: 'shrink', bitmap: img, width, height }, undefined, [img])).bitmap;
        src.data = small;
        return;
      } catch (error) {
        if (error.bitmap) from = error.bitmap; // sent and sent back
        small = await createImageBitmap(from, { resizeWidth: width, resizeHeight: height, resizeQuality: 'high' });
        from.close?.();
        src.data = small;
        return;
      }
    }),
  );
}

/**
 * Fetch and parse a .glb into a scene of its own, with textures at most `cap` px. The caller owns it: give it back with
 * disposeModel() when it is no longer wanted (the GPU and the decoded images are then freed; nothing is cached here).
 * Aborting `signal` rejects this call.
 */
export async function loadModel(url, signal, cap = 2048) {
  const buffer = await fetchBuffer(url, signal);
  const scene = await abortable(parse(buffer), signal);
  forgetBuffer(url);
  await abortable(shrink(scene, cap), signal);
  return scene;
}

/** Free everything a loaded model holds: geometry and textures on the GPU, and the decoded images in memory. */
export function disposeModel(scene) {
  scene.removeFromParent();
  scene.traverse((o) => {
    o.geometry?.dispose();
    o.customDepthMaterial?.dispose();
    for (const m of [o.material].flat()) {
      if (!m) continue;
      for (const [key, v] of Object.entries(m)) {
        if (!v?.isTexture || key === 'envMap') continue; // the studio's environment belongs to the stage, not to a model
        v.dispose();
        v.source?.data?.close?.();
      }
      m.dispose();
    }
  });
}
