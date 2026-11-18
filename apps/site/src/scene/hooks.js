import { useEffect, useState, useSyncExternalStore } from 'react';
import { getHot, onHot } from './hot.js';
import { getProgress, onProgress } from './progress.js';

/** The section the visitor is in ('top', 'education', 'experience', 'projects', 'links'); re-renders only when it changes. */
export function useSection() {
  const [section, setSection] = useState('top');
  useEffect(() => {
    const update = (p) => setSection(p.section);
    update(getProgress());
    return onProgress(update);
  }, []);
  return section;
}

/** What the stage or the text is pointing at (scene/hot.js). */
export const useHot = () => useSyncExternalStore(onHot, getHot);
