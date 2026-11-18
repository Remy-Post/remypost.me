import { useEffect, useState } from 'react';
import { projects } from '../content/site.js';
import { getProgress, onProgress } from './progress.js';

const SLUGS = projects.map((p) => p.slug);

/** How far past the halfway point `t` must travel before the active project changes, so it never flickers. */
const HYSTERESIS = 0.12;

/**
 * The slug of the project the visitor is at, or null at the intro and at about. Rounds `t` to the nearest whole
 * project, but keeps the current one until `t` is clearly closer to another. On a project page it is that project.
 */
export function useActiveProject() {
  const [slug, setSlug] = useState(null);
  useEffect(() => {
    let n = null; // the whole number `t` is currently rounded to
    const update = ({ route, t, slug: pageSlug }) => {
      if (route !== 'home') {
        n = null;
        return setSlug(route === 'project' ? pageSlug : null);
      }
      if (n === null || Math.abs(t - n) > 0.5 + HYSTERESIS) n = Math.round(t);
      setSlug(n >= 1 && n <= 9 ? SLUGS[n - 1] : null);
    };
    update(getProgress());
    return onProgress(update);
  }, []);
  return slug;
}
