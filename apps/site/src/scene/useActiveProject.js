import { useEffect, useState } from 'react';
import { projects } from '../content/site.js';
import { getProgress, onProgress } from './progress.js';

const SLUGS = projects.map((p) => p.slug);

/**
 * The slug of the project the visitor is at, or null at the intro and at about: progress.js's `near`, the same project the
 * stage's turntable comes to rest on. On a project page it is that project.
 */
export function useActiveProject() {
  const [slug, setSlug] = useState(null);
  useEffect(() => {
    const update = ({ near }) => setSlug(near >= 1 && near <= SLUGS.length ? SLUGS[near - 1] : null);
    update(getProgress());
    return onProgress(update);
  }, []);
  return slug;
}
