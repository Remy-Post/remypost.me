import { useCallback, useEffect, useState } from 'react';
import { Outlet, useLocation, useMatch, useNavigate } from 'react-router';
import { projectBySlug } from '../content/site.js';
import Bar from './Bar.jsx';
import { useLive } from './Objects.jsx';
import ProjectIndex from './ProjectIndex.jsx';
import ScrollManager from './ScrollManager.jsx';
import Stage from './Stage.jsx';

/**
 * The one frame every route sits in: the bar, a text column (the route) and the stage, which persists across routes
 * so the object never reloads. The text scrolls; the stage is sticky (see site.css).
 */
export default function Frame() {
  const location = useLocation();
  const navigate = useNavigate();
  const match = useMatch('/work/:slug');
  const page = match ? projectBySlug(match.params.slug) : undefined;
  const onProject = !!page;
  const live = useLive(page?.object);
  // The menu is open for one history entry: any navigation closes it.
  const [openAt, setOpenAt] = useState(null);
  const menu = openAt === location.key;
  const key = location.key;
  const setOpen = useCallback((on) => setOpenAt(on ? key : null), [key]);
  // The old /#about is now the links.
  useEffect(() => {
    if (location.pathname === '/' && location.hash === '#about') navigate({ pathname: '/', hash: '#links' }, { replace: true });
  }, [location, navigate]);
  /** Where a project's name in the menu or the index goes: its section on home, or its page when already on a project. */
  const hrefFor = (slug) => (onProject ? `/work/${slug}` : { pathname: '/', hash: `#${slug}` });

  return (
    <>
      <ScrollManager />
      <a
        className="skip"
        href="#main"
        onClick={(e) => {
          e.preventDefault();
          document.getElementById('main')?.focus({ preventScroll: true });
        }}
      >
        Skip to content
      </a>
      <Bar open={menu} setOpen={setOpen} hrefFor={hrefFor} />
      <div className="page" inert={menu}>
        <div className="frame">
          <Stage />
          <main className="text" id="main" tabIndex={-1}>
            <Outlet />
          </main>
        </div>
        <ProjectIndex hrefFor={hrefFor} />
        {onProject && live && <p className="stage-hint">Drag to turn it.</p>}
      </div>
    </>
  );
}
