/**
 * What every model on the stage shares: how it is prepared for the light, faded in and out, sized, and given
 * invisible hit volumes for the pointer. Imports three, so reach it only from stage code.
 */
import { Box3, BoxGeometry, Mesh, MeshBasicMaterial, MeshDepthMaterial, RGBADepthPacking, Vector3 } from 'three';

/** Emissive screens are driven this much harder so they glow against the dark. */
export const GLOW = 1.5;
/**
 * The most light (linear, before tone mapping) a lit surface that does not emit may send to the camera. It is the
 * ceiling of diffuse white and of a metal's brightest reflection; bloom's threshold sits just above it (post.js), so only
 * emissive materials ever reach the bloom.
 */
export const LIT_MAX = 1.7;

/**
 * Darken a shader by a shared 0 to 1 uniform: how an object leaves the light without any transparency. A surface that
 * does not emit is also kept to LIT_MAX, by scaling its colour (so a saturated one keeps its hue), unless it is glass
 * (what it shows of a screen behind it is the screen's own light and must reach the bloom).
 */
export function fadeOut(shader, fade, cap = true) {
  shader.uniforms.uFade = fade;
  shader.fragmentShader = shader.fragmentShader
    .replace('#include <common>', '#include <common>\nuniform float uFade;')
    .replace(
      '#include <opaque_fragment>',
      `// Leaving or arriving, an object dissolves (a fixed noise decides which pixels stay) rather than darkening, which on the
      // lit floor read as a black silhouette; it keeps most of its light until it is gone.
      if (uFade < 0.995 && fract(52.9829189 * fract(dot(gl_FragCoord.xy, vec2(0.06711056, 0.00583715)))) > uFade) discard;
      outgoingLight *= 0.7 + 0.3 * uFade;
${cap ? `outgoingLight *= min(1.0, ${LIT_MAX.toFixed(2)} / max(max(outgoingLight.r, max(outgoingLight.g, outgoingLight.b)), 1e-4));\n` : ''}#include <opaque_fragment>`,
    );
}

/**
 * Set up a parsed model for the stage: it casts and receives shadows (glass and cut-outs do not cast), its materials
 * fade by `fade` (a `{ value }` uniform), textures are sharp at a slant, metals take their own reflection strength, emissive screens glow. `tweak(material, mesh)`
 * may adjust a material, and `extend(shader, material, mesh)` may add to its shader after the fade. The parsed model is
 * shared across stages, so everything done here is idempotent.
 */
export function prepare(model, { fade, aniso, metals, env, tweak, extend }) {
  model.traverse((m) => {
    if (!m.isMesh) return;
    if (m.isSkinnedMesh) m.frustumCulled = false; // a skin's bounds are those of its rest pose, not of where it moves to
    const mats = [m.material].flat();
    m.castShadow = !mats.some((x) => x.transmission > 0 || x.transparent);
    m.receiveShadow = true;
    // The shadow pass draws every object with one shared depth material and does not refresh its texture uniform between
    // objects that have a map, so it keeps pointing at the first one's texture: after that model is freed the pass would
    // upload the freed texture again. A mesh with a map gets a depth material of its own, which goes when it does.
    if (m.castShadow && mats.some((x) => x.map || x.alphaMap)) m.customDepthMaterial = new MeshDepthMaterial({ depthPacking: RGBADepthPacking });
    for (const x of mats) {
      const cap = !(x.transmission > 0) && !x.emissiveMap && !(x.emissive && x.emissive.getHex() > 0);
      x.onBeforeCompile = (shader) => {
        fadeOut(shader, fade, cap);
        extend?.(shader, x, m);
      };
      if (extend) x.customProgramCacheKey = () => `extended:${m.name}`;
      tweak?.(x, m);
      // Metals reflect the studio at their own strength (the stage sets it each frame): a mirror of softboxes washes out.
      if (metals && env && x.metalness > 0.4 && !x.envMap) {
        x.envMap = env;
        metals.add(x);
      }
      if (x.emissiveMap && !x.userData.glow) {
        x.userData.glow = true;
        x.emissiveIntensity *= GLOW;
      }
      for (const v of Object.values(x)) if (v?.isTexture) v.anisotropy = aniso;
    }
  });
}

/**
 * Scale a model so its largest dimension is `size`, with its footprint centred and its base on y = 0, inside `fit`
 * (a Group); call it before the model is added to `fit`. Returns the normalised size `{ w, h, d }`, the footprint radius and the scale `k`.
 */
export function normalise(model, fit, size) {
  // The model is not inside the scene yet, so its own space is `fit`'s space: where the station stands does not matter.
  model.updateMatrixWorld(true);
  const box = new Box3().setFromObject(model, true);
  const dims = box.getSize(new Vector3());
  const k = size / Math.max(dims.x, dims.y, dims.z);
  const mid = box.getCenter(new Vector3());
  fit.scale.setScalar(k);
  fit.position.set(-mid.x * k, -box.min.y * k, -mid.z * k);
  return { w: Math.max(dims.x, dims.z) * k, h: dims.y * k, d: Math.min(dims.x, dims.z) * k, radius: (Math.max(dims.x, dims.z) * k) / 2, k };
}

const hitMaterial = new MeshBasicMaterial({ visible: false });

/**
 * An invisible box over `node`'s bounds, grown by `pad` metres and added to `node` itself so it moves with it, that the
 * pointer ray tests instead of the node's own thousands of triangles. `id` names what it stands for. Call it once the
 * model is at its rest pose and not yet inside a station (so only the model's own transforms count).
 */
export function hitBox(root, node, id, pad = 0.002) {
  root.updateMatrixWorld(true);
  node.updateWorldMatrix(true, true);
  const inv = node.matrixWorld.clone().invert();
  const scale = new Vector3().setFromMatrixScale(node.matrixWorld);
  const box = new Box3().setFromObject(node, true).applyMatrix4(inv);
  const size = box.getSize(new Vector3());
  size.x += (2 * pad) / scale.x;
  size.y += (2 * pad) / scale.y;
  size.z += (2 * pad) / scale.z;
  const mesh = new Mesh(new BoxGeometry(size.x, size.y, size.z), hitMaterial);
  box.getCenter(mesh.position);
  mesh.userData.hit = id;
  mesh.visible = false;
  node.add(mesh);
  mesh.updateMatrixWorld(true);
  return mesh;
}

/** The first hit's id among `boxes` for `raycaster`, or null. */
export function pickId(raycaster, boxes) {
  if (!boxes.length) return null;
  const hits = raycaster.intersectObjects(boxes, false);
  return hits.length ? hits[0].object.userData.hit : null;
}

