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
    if (type === 'POP' && location.key in positions) window.scrollTo({ top: positions[location.key], behavior: 'instant' });
    else if (target) scrollToTarget(target, { smooth: behavior === 'smooth', margin: scrollMargin(target) });
    else scrollToTarget(0, { smooth: behavior === 'smooth' });
    routeChanged();
  }, [location, type]);

  return null;
}
