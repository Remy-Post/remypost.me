/**
 * The scroll-progress signal: where the visitor is in the story, as numbers the 3D stage can follow.
 * Three-free and React-free; reads the DOM only when asked and does no work while nothing subscribes.
 *
 *   getProgress()  -> { route, slug, t, near, section, local, step, job, within, p }
 *   onProgress(fn) -> unsubscribe; fn(progress, frameTime) fires on scroll, resize and route change, from one rAF per frame
 *   routeChanged() -> tell subscribers the route changed (the router calls it once the new page is in the DOM)
 *
 * route    'home' | 'project' | 'other'.
 * section  'top' | 'education' | 'experience' | 'projects' | 'links': the one the focus line (the middle of the part of
 *          the page the text is read in) is in. A project page counts as 'projects'.
 * local    0 to 1 through that section.
 * step     continuous index through the `[data-step]` blocks of the section (the three schools, the three jobs): n when
 *          block n is centred on the focus line, linear in between. 0 elsewhere.
 * within   how far through the text of the nearest `[data-step]` block the focus line is, 0 at its top to 1 at its bottom
 *          (0.5 outside any section with steps).
 * point    index of the `.points li` bullet being read in the nearest block, `pointFrac` how far through it, 0 to 1.
 * job      `step` while in 'experience', else 0.
 * p        the camera's place along the path of stations, continuous: 0 the intro, 1 education, 2 experience,
 *          3 the projects, 4 the links. It holds at a whole number through a section and moves across the seam between
 *          two sections, over a window of one reading height centred on the seam.
 * t        the turntable, as before: 0 until the seam before the projects, 1..9 when project n is centred, 10 at the links.
 * near     the project the visitor is at, 1..9 (0 at the intro and the links): `t` rounded, held until `t` is clearly closer to
 *          another; above the text (phones) between two projects it is the next one, whose text is the one in view. The one
 *          answer for the index, the stills, the hint and where the stage's turntable comes to rest.
 */
import { projects } from '../content/site.js';

const slugs = projects.map((p) => p.slug);
/** How far past the halfway point `t` must travel before `near` changes, so it never flickers. */
const HYSTERESIS = 0.12;
let held = null; // the whole number `t` is currently rounded to
/** `t` rounded to the nearest whole project, keeping the current one until `t` is clearly closer to another. */
function holdNear(t) {
  if (held === null || Math.abs(t - held) > 0.5 + HYSTERESIS) held = Math.round(t);
  return held;
}
const STATIONS = ['top', 'education', 'experience', 'projects', 'links'];
/** The breakpoint where the stage moves beside the text (see site.css). Narrower, the stage sits above it. */
const WIDE = '(min-width: 960px)';

const routeOf = () => {
  const path = window.location.pathname.replace(/\/+$/, '') || '/';
  if (path === '/') return { route: 'home', slug: null };
  const slug = path.match(/^\/work\/([^/]+)$/)?.[1];
  let decoded = slug;
  try {
    decoded = slug && decodeURIComponent(slug);
  } catch {
    /* a malformed escape is not a project */
  }
  return slugs.includes(decoded) ? { route: 'project', slug: decoded } : { route: 'other', slug: null };
};

/** Viewport box of the part of the page the text is read in: below the bar, and below the stage on phones. */
function readingArea() {
  const bar = document.querySelector('.bar')?.offsetHeight ?? 0;
  const stage = document.querySelector('.stage');
  const top = window.matchMedia(WIDE).matches || !stage ? bar : stage.getBoundingClientRect().bottom;
  return { top, bottom: window.innerHeight };
}

const smooth = (k) => {
  const x = Math.min(1, Math.max(0, k));
  return x * x * (3 - 2 * x);
};

/** Page-space box of an element. */
const box = (el, scroll) => {
  const r = el.getBoundingClientRect();
  return { top: r.top + scroll, height: r.height, mid: r.top + scroll + r.height / 2 };
};

/** Linear interpolation of `values` at the points `at` (ascending), clamped at both ends. */
function along(at, values, x) {
  if (x <= at[0]) return values[0];
  const last = at.length - 1;
  if (x >= at[last]) return values[last];
  let i = 0;
  while (at[i + 1] <= x) i++;
  return values[i] + ((values[i + 1] - values[i]) * (x - at[i])) / (at[i + 1] - at[i]);
}

const REST = { t: 0, section: 'top', local: 0, step: 0, job: 0, within: 0.5, point: 0, pointFrac: 0, p: 0 };

/** Page-space top of the first line and bottom of the last line of an element's content (its padding left out). */
const text = (el, scroll) => {
  const a = el.firstElementChild ?? el;
  const z = el.lastElementChild ?? el;
  return { top: a.getBoundingClientRect().top + scroll, bottom: z.getBoundingClientRect().bottom + scroll };
};

/**
 * Where something that is `at` the given page positions has got to: `values[i]` all along [at[2i], at[2i+1]] (a plateau),
 * and a straight line from one plateau's end to the next one's start. Beyond either end, the first or last value.
 */
function plateaus(at, values, x) {
  const knots = [];
  const vals = [];
  at.forEach(([a, b], i) => {
    knots.push(a, b);
    vals.push(values[i], values[i]);
  });
  return along(knots, vals, x);
}

function homeProgress() {
  const secs = STATIONS.map((id) => document.getElementById(id));
  const cards = slugs.map((id) => document.getElementById(id));
  if (secs.includes(null) || cards.includes(null)) return REST;
  const scroll = window.scrollY;
  const area = readingArea();
  // Beside the text (desktop) everything follows the focus line, the middle of the reading area. Above it (phones, tablets) the
  // stage is a strip over the text, and what matters is what is at the stage's lower edge: each section's, school's and job's
  // object holds for as long as any of its text is on screen below the stage, and turns only across the gap between two.
  const narrow = !window.matchMedia(WIDE).matches;
  const edge = scroll + area.top + 24; // a line's height under the stage's edge: the first line is under the stage before the object has finished arriving, and the last is still seen when it starts to leave
  const line = narrow ? edge : scroll + (area.top + area.bottom) / 2; // the focus line, in page coordinates
  const S = secs.map((el) => box(el, scroll));
  const C = cards.map((el) => box(el, scroll));

  // The section the line is in, and how far through it.
  let k = STATIONS.length - 1;
  while (k > 0 && S[k].top > line) k--;
  const local = Math.min(1, Math.max(0, (line - S[k].top) / S[k].height));

  // The camera's place: whole through a section, eased across each seam over a window of one reading height (beside the text,
  // centred on the seam; above it, ending when the next section's top reaches the stage).
  const W = (area.bottom - area.top) / 2;
  let p = 0;
  for (let i = 1; i < S.length; i++) p += smooth(narrow ? (line - (S[i].top - 2 * W)) / (2 * W) : (line - (S[i].top - W)) / (2 * W));

  // The turntable: 0, a rise to 1 across the seam into the projects, 1..9 at the project centres, 10 at the links.
  // A last section too tall to reach the line (a short page end) still ends at 10.
  let t;
  if (narrow) {
    const T = cards.map((el) => text(el, scroll));
    const first = T[0].top;
    const start = Math.min(S[3].top - 2 * W, first - 2);
    const at = [[start, start], ...T.map((x) => [x.top, x.bottom]), [S[4].top, S[4].top + 1]];
    t = plateaus(at, [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10], line);
  } else {
    const maxLine = document.documentElement.scrollHeight - window.innerHeight + (area.top + area.bottom) / 2;
    const end = Math.max(C[8].mid + 1, Math.min(S[4].mid, maxLine));
    const start = Math.min(S[3].top - W, C[0].mid - 1);
    t = along([start, ...C.map((c) => c.mid), end], [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10], line);
  }

  // Steps within the section (schools, jobs).
  let step = 0;
  let within = 0.5;
  let point = 0;
  let pointFrac = 0;
  const steps = secs[k].querySelectorAll('[data-step]');
  if (steps.length) {
    const boxes = [...steps].map((el) => box(el, scroll));
    if (narrow) {
      const T = [...steps].map((el) => text(el, scroll));
      step = plateaus(T.map((x) => [x.top, x.bottom]), T.map((_, i) => i), line);
    } else {
      const mids = boxes.map((b) => b.mid);
      step = along(mids, mids.map((_, i) => i), line);
    }
    const near = boxes[Math.round(step)];
    // How far through its text the reader is, and which bullet: on a phone at a line a third of the way down what is under the stage.
    const read = narrow ? edge + 0.3 * (area.bottom - area.top) : line;
    within = Math.min(1, Math.max(0, (read - near.top) / near.height));
    const lis = [...steps[Math.round(step)].querySelectorAll('.points li')].map((el) => box(el, scroll));
    if (lis.length) {
      point = lis.findIndex((b) => read < b.top + b.height);
      if (point < 0) (point = lis.length - 1), (pointFrac = 1);
      else pointFrac = Math.min(1, Math.max(0, (read - lis[point].top) / lis[point].height));
    }
  }
  const section = STATIONS[k];
  return { t, section, local, step, job: section === 'experience' ? step : 0, within, point, pointFrac, p };
}

/** The window.scrollY that puts the middle of `el` on the focus line: where the arrow keys and badge clicks scroll to. */
export function scrollYFor(el) {
  const area = readingArea();
  const r = el.getBoundingClientRect();
  return r.top + window.scrollY + r.height / 2 - (area.top + area.bottom) / 2;
}

export function getProgress() {
  const { route, slug } = routeOf();
  if (route === 'home') {
    const home = homeProgress();
    // Beside the text a place between two projects belongs to the nearer one. Above it (phones) the text is read under the stage and
    // `t` crosses the gap between two blocks while the next one's first lines are already in view: so there it is the next one.
    const near = window.matchMedia(WIDE).matches ? holdNear(home.t) : Math.ceil(home.t - 0.02);
    return { route, slug, ...home, near };
  }
  held = null;
  if (route === 'project') return { route, slug, ...REST, t: slugs.indexOf(slug) + 1, near: slugs.indexOf(slug) + 1, section: 'projects', p: 3 };
  return { route, slug, ...REST, near: 0 };
}

const subscribers = new Set();
let frame = 0;

function schedule() {
  if (frame) return;
  frame = requestAnimationFrame((now) => {
    frame = 0;
    const progress = getProgress();
    for (const fn of subscribers) fn(progress, now);
  });
}

export function onProgress(fn) {
  subscribers.add(fn);
  if (subscribers.size === 1) {
    window.addEventListener('scroll', schedule, { passive: true });
    window.addEventListener('resize', schedule);
  }
  return () => {
    subscribers.delete(fn);
    if (subscribers.size === 0) {
      window.removeEventListener('scroll', schedule);
      window.removeEventListener('resize', schedule);
      cancelAnimationFrame(frame);
      frame = 0;
    }
  };
}

export function routeChanged() {
  if (subscribers.size) schedule();
}
