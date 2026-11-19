/**
 * The image pipeline (pmndrs/postprocessing). The scene is drawn, multisampled, into half-float buffers at the canvas's own
 * pixel ratio (the composer, bloom's buffers and SMAA all follow renderer.getDrawingBufferSize, so a 2x display gets 2x).
 * Then, in one pass: bloom, tone mapping (Neutral, once, here and nowhere else: the renderer itself does none, as the
 * library asks) and a dither in output space that keeps the dark floor's fade from banding in 8 bits. A last pass
 * anti-aliases the result with SMAA, and is where the sRGB encoding happens (SMAA reads perceptual colour).
 *
 * Only what truly emits may bloom: the threshold sits above anything a lit surface can reach (common.js caps every
 * non-emissive material below it), so only the watch's and the window's screens glow. A depth of field sits in its own
 * pass that is only on while the camera is travelling between two stations, where its soft blur carries the eye from
 * one object to the next; at rest nothing is blurred and the pass costs nothing.
 */
import { HalfFloatType, Vector3 } from 'three';
import { BlendFunction, BloomEffect, DepthOfFieldEffect, Effect, EffectComposer, EffectPass, RenderPass, SMAAEffect, SMAAPreset, ToneMappingEffect, ToneMappingMode } from 'postprocessing';
import { LIT_MAX } from './common.js';

/** Triangular-distribution noise of one 8-bit step in output (sRGB) space, from interleaved gradient noise: static, so a still frame stays still. */
const DITHER = `
float gradientNoise(vec2 p) {
  return fract(52.9829189 * fract(dot(p, vec2(0.06711056, 0.00583715))));
}
void mainImage(const in vec4 inputColor, const in vec2 uv, out vec4 outputColor) {
  vec2 p = floor(uv * resolution);
  float n = gradientNoise(p) + gradientNoise(p + vec2(47.0, 13.0)) - 1.0;
  vec4 s = sRGBTransferOETF(vec4(clamp(inputColor.rgb, 0.0, 1.0), inputColor.a));
  s.rgb += n / 255.0;
  outputColor = sRGBTransferEOTF(s);
}`;

class DitherEffect extends Effect {
  constructor() {
    super('DitherEffect', DITHER, { blendFunction: BlendFunction.SRC });
  }
}

export function createPost(renderer, scene, camera, { bloom = true, dof = true, smaa = true, samples = 4 } = {}) {
  const composer = new EffectComposer(renderer, { frameBufferType: HalfFloatType, multisampling: samples });
  // The library gives both of its buffers the sample count, but only the one the scene is drawn into has geometry edges to
  // average: every pass after it draws one screen-sized quad into the other, where four samples change no pixel and cost 120 MB
  // (colour and depth) at a retina stage.
  composer.outputBuffer.samples = 0;
  const renderPass = new RenderPass(scene, camera);
  composer.addPass(renderPass);

  const focus = new Vector3();
  const dofEffect = dof ? new DepthOfFieldEffect(camera, { focusDistance: 4, focusRange: 2, bokehScale: 1, resolutionScale: 0.5 }) : null;
  let dofPass = null;
  if (dofEffect) {
    dofEffect.target = focus;
    dofPass = new EffectPass(camera, dofEffect);
    dofPass.enabled = false;
    composer.addPass(dofPass);
  }
  const bloomEffect = bloom ? new BloomEffect({ intensity: 0.32, luminanceThreshold: LIT_MAX + 0.3, luminanceSmoothing: 0.2, mipmapBlur: true, radius: 0.7, levels: 6 }) : null;
  const tone = new ToneMappingEffect({ mode: ToneMappingMode.NEUTRAL });
  composer.addPass(new EffectPass(camera, ...(bloomEffect ? [bloomEffect] : []), tone, new DitherEffect()));
  if (smaa) composer.addPass(new EffectPass(camera, new SMAAEffect({ preset: SMAAPreset.HIGH })));

  return {
    composer,
    /** Draw the scene from another (identical) camera: each camera keeps a transmission buffer of its own size. */
    setSceneCamera(cam) {
      renderPass.camera = cam;
    },
    /** Where the depth of field is focused (world), and how deep the sharp zone is. */
    setFocus(point, range) {
      focus.copy(point);
      if (dofEffect) dofEffect.cocMaterial.focusRange = range;
    },
    /** 0 at rest (the pass is skipped), up to 1 mid-travel. */
    setBlur(amount) {
      if (!dofPass) return;
      dofPass.enabled = amount > 0.03;
      dofEffect.bokehScale = 0.4 + 1.6 * amount;
    },
    bloom: bloomEffect,
    dof: dofEffect,
    render: (dt) => composer.render(dt),
    setSize: (w, h) => composer.setSize(w, h, false),
    dispose: () => composer.dispose(),
  };
}
