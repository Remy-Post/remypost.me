/**
 * Smooth wheel scrolling with Lenis, started with the stage (after first paint). Lenis keeps the page's own scrolling
 * and only eases the wheel, so the keyboard, anchors, find-in-page and the scrollbar behave as they always did. Touch
 * stays native. Off under reduced motion (and back on if that changes). Its frame loop runs only while the page is
 * actually moving.
 */
import Lenis from 'lenis';
import { setSmooth } from '../scene/smooth.js';
import { onReducedMotion, reducedMotion } from './services.js';

export function startSmooth() {
  let lenis = null;
  let raf = 0;
  const tick = (time) => {
    raf = 0;
    lenis?.raf(time);
    // Lenis's own 'scroll' event calls kick() from inside raf(), which has already asked for the next frame: asking again here
    // gave two callbacks a frame, each of which asked for two more, so the queue doubled every frame while the page scrolled.
    if (lenis?.isScrolling && !raf) raf = requestAnimationFrame(tick);
  };
  const kick = () => {
    if (lenis && !raf) raf = requestAnimationFrame(tick);
  };
  const make = () => {
    if (lenis) return;
    lenis = new Lenis({ autoRaf: false, smoothWheel: true, syncTouch: false, lerp: 0.11, wheelMultiplier: 0.95, anchors: false });
    lenis.on('scroll', kick);
    lenis.on('virtual-scroll', kick);
    setSmooth(lenis, kick);
  };
  const drop = () => {
    cancelAnimationFrame(raf);
    raf = 0;
    lenis?.destroy();
    lenis = null;
    setSmooth(null);
  };
  if (!reducedMotion()) make();
  const off = onReducedMotion((on) => (on ? drop() : make()));
  return () => {
    off();
    drop();
  };
}
