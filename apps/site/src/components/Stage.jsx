import { useEffect, useRef, useState } from 'react';
import { useMatch } from 'react-router';
import { projectBySlug, projects } from '../content/site.js';
import { startLive } from '../three/live.js';
import { useSection } from '../scene/hooks.js';
import { useActiveProject } from '../scene/useActiveProject.js';
import { useLive, useObjects } from './Objects.jsx';

/**
 * One still per state, found by name: <object>.webp for a project, and table, education, experience and links for the
 * four stations. A missing file is simply not drawn (the stage stays dark). Vite resolves the glob at build time, so
 * nothing breaks before they exist.
 */
const files = import.meta.glob('../assets/objects/*.webp', { eager: true, query: '?url', import: 'default' });
const stills = Object.entries(files).map(([path, src]) => ({ name: path.slice(path.lastIndexOf('/') + 1, -'.webp'.length), src }));
const objectOf = Object.fromEntries(projects.map((p) => [p.slug, p.object]));
const STATION_STILL = { top: 'table', education: 'education', experience: 'experience', links: 'links' };

/**
 * The stage: the stills underneath, which are the loading state and the fallback, and the live WebGL canvas above
 * them (three/stage.js), which fades in over a still once its station has drawn. On a project page, and on a project's
 * section, the mount is a keyboard-operable viewer: drag or the arrow keys turn the object, Enter or Space tries it.
 * Education, work and the links have real text and links beside the stage, so the canvas stays hidden from readers.
 */
export default function Stage() {
  const slug = useActiveProject();
  const section = useSection();
  const objects = useObjects();
  const page = useMatch('/work/:slug');
  const project = page && projectBySlug(page.params.slug);
  const mount = useRef(null);
  const [, setLive] = useState(false);
  const current = section === 'projects' && slug ? objectOf[slug] : section === 'projects' ? 'table' : STATION_STILL[section];

  // One canvas for the whole site: this effect lives as long as the frame does, and only follows the 3D switch.
  useEffect(() => (objects ? startLive(mount.current, setLive) : undefined), [objects]);

  const hero = project ?? (section === 'projects' && slug ? projectBySlug(slug) : null);
  // Everything the mount promises (a tab stop, a name, help text) is there only while this object is really on the stage.
  const turnable = useLive(hero?.object) && !!hero;
  return (
    <div className="stage">
      {stills.map(({ name, src }) => (
        <img key={name} className={name === current ? 'stage__still is-on' : 'stage__still'} src={src} alt="" decoding="async" fetchPriority={name === 'table' ? 'high' : 'low'} />
      ))}
      <div
        ref={mount}
        className="stage__mount"
        data-stage-mount
        tabIndex={turnable ? 0 : undefined}
        role={turnable ? 'group' : undefined}
        aria-label={turnable ? `${hero.name}, 3D model` : undefined}
        aria-describedby={turnable ? 'stage-help' : undefined}
      />
      <span id="stage-help" hidden>
        {project ? 'Drag to turn it, or use the left and right arrow keys. Press Enter or Space to try it.' : 'Press Enter or Space to try it.'}
      </span>
    </div>
  );
}
