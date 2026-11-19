import { useEffect, useLayoutEffect, useRef } from 'react';
import { useLocation, useNavigationType } from 'react-router';
import { projects } from '../content/site.js';
import { routeChanged } from '../scene/progress.js';
import { scrollToTarget } from '../scene/smooth.js';

const STORE = 'scroll';
/** decodeURIComponent that does not throw on a malformed escape (`#%`): the text as it is then. */
const safeDecode = (s) => {
  try {
    return decodeURIComponent(s);
  } catch {
    return s;
  }
};
const reduced = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches;

/** How long after a jump to a section it keeps checking that the section is still where the jump was aimed (ms). */
const HOLD = 8000;
/** The visitor's own hand on the page: the first of these ends the check for good. */
const TAKEOVER = ['wheel', 'touchstart', 'pointerdown', 'keydown'];

/** The scroll-margin-top the section asks for (what scrollIntoView honoured, and Lenis and scrollTo do not). */
const scrollMargin = (el) => parseFloat(getComputedStyle(el).scrollMarginTop) || 0;

const load = () => {
  try {
    return JSON.parse(sessionStorage.getItem(STORE)) ?? {};
  } catch {
    return {};
  }
};
// The router gives an entry that was not created by a navigation (the one a visit starts on) the key 'default', which
// every such visit would share. Give it its own, so a saved position can never belong to a different visit.
if (!history.state?.key) history.replaceState({ ...history.state, key: Math.random().toString(36).slice(2, 10) }, '');

/** Where each history entry was last scrolled to, by location.key. Kept in sessionStorage so a reload restores it too. */
const positions = load();
const save = () => {
  try {
    const keys = Object.keys(positions);
    for (const k of keys.slice(0, Math.max(0, keys.length - 60))) delete positions[k]; // oldest first
    sessionStorage.setItem(STORE, JSON.stringify(positions));
  } catch {
    /* private mode: restoring is best effort */
  }
};

/**
 * A landing that keeps its line. Something above the target can change height after the jump was aimed: the hint that goes with
 * each object, which the stage lets go of as the camera comes to the links (nine of them, 770 px in all), a picture, a font.
 * Chrome and Firefox move the scroll position to compensate (scroll anchoring); Safari does not, so the jump stopped at the end
 * of the shorter page and left the Links heading hidden under the stage. For a few seconds after a jump, whenever the target's
 * place on the page has moved, the jump is aimed again at the new place (still gliding if it was a glide and is still going). The
 * visitor's first wheel, touch, press or key takes over for good. Returns the function that ends the check.
 */
function holdLanding(target, margin, glide) {
  const place = () => target.getBoundingClientRect().top + window.scrollY - margin;
  const started = performance.now();
  let aimed = place();
  const watch = new ResizeObserver(() => {
    const now = place();
    if (Math.abs(now - aimed) < 1) return;
    aimed = now;
    scrollToTarget(target, { smooth: glide && performance.now() - started < 1300, margin });
  });
  watch.observe(document.querySelector('.frame') ?? document.body);
  const stop = () => {
    watch.disconnect();
    clearTimeout(timer);
    for (const type of TAKEOVER) window.removeEventListener(type, stop);
  };
  const timer = setTimeout(stop, HOLD);
  for (const type of TAKEOVER) window.addEventListener(type, stop, { passive: true });
  return stop;
}

/**
 * The page's scrolling, which the router does not do in declarative mode. No scroll hijacking: this only decides where a
 * navigation lands. Back/Forward return to the saved position; a link with a #hash lands on that section (smoothly when
 * already on the page, unless reduced motion); anything else starts at the top. Renders nothing.
 */
export default function ScrollManager() {
  const location = useLocation();
  const type = useNavigationType();
  const key = useRef(location.key);
  const path = useRef(null);

  useEffect(() => {
    history.scrollRestoration = 'manual';
    let timer;
    const onScroll = () => {
      positions[key.current] = window.scrollY;
      clearTimeout(timer);
      timer = setTimeout(save, 200);
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('pagehide', save);
    return () => {
      clearTimeout(timer);
      window.removeEventListener('scroll', onScroll);
      window.removeEventListener('pagehide', save);
    };
  }, []);

  useLayoutEffect(() => {
    key.current = location.key; // before the browser reports the scroll the new page causes
    const samePage = path.current === location.pathname;
    path.current = location.pathname;
    const behavior = samePage && !reduced() ? 'smooth' : 'instant';
    // The first project is reached through its "Projects" heading, which sits just above it: landing on the section alone would
    // leave the heading under the bar.
    const wanted = location.hash && safeDecode(location.hash.slice(1));
    const target = wanted && document.getElementById(wanted === projects[0].slug ? 'projects' : wanted);
    let hold;
    if (type === 'POP' && location.key in positions) window.scrollTo({ top: positions[location.key], behavior: 'instant' });
    else if (target) {
      scrollToTarget(target, { smooth: behavior === 'smooth', margin: scrollMargin(target) });
      hold = holdLanding(target, scrollMargin(target), behavior === 'smooth');
    } else scrollToTarget(0, { smooth: behavior === 'smooth' });
    routeChanged();
    return () => hold?.();
  }, [location, type]);

  return null;
}
