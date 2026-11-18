/**
 * Smooth scrolling, when it is on. Lenis (loaded after first paint by three/smooth-start.js) keeps the page's own
 * scrolling and only eases the wheel, so window.scrollY, anchors, find-in-page and the keyboard all keep working.
 * ScrollManager scrolls through here, so an in-page jump uses Lenis's easing when it is on and the browser's when not.
 * Three-free.
 */
let lenis = null;
let kick = () => {};

/** Register the Lenis instance and the function that starts its frame loop (it only runs while the page moves). */
export const setSmooth = (instance, start = () => {}) => {
  lenis = instance;
  kick = start;
};

/**
 * Scroll the window to an element or a y, instantly or smoothly. `offset` is added to a y, or to where an element's
 * top would be; Lenis already leaves an element's `scroll-margin-top` above it, the browser's own scrolling does not.
 */
export function scrollToTarget(target, { smooth = false, offset = 0, margin = 0 } = {}) {
  if (lenis) {
    // The page has just changed height (a route change): Lenis still holds the old page's scroll limit and would clamp to it.
    lenis.resize();
    if (smooth) {
      // A y, not the element: given an element Lenis leaves both its scroll-margin-top and the page's scroll-padding-top above it, and
      // here they are the same distance (under the bar, and on a phone the stage): a heading landed twice that far down.
      const to = typeof target === 'number' ? target : target.getBoundingClientRect().top + window.scrollY - margin;
      lenis.scrollTo(to + offset, { duration: 1.1 });
      return kick();
    }
  }
  const y = typeof target === 'number' ? target : target.getBoundingClientRect().top + window.scrollY - margin;
  window.scrollTo({ top: y + offset, behavior: smooth ? 'smooth' : 'instant' });
  if (lenis && !smooth) lenis.scrollTo(y + offset, { immediate: true, force: true }); // keep its own idea of the position in step
}
