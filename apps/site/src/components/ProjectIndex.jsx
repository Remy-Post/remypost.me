import { Link } from 'react-router';
import { projects } from '../content/site.js';
import { useSection } from '../scene/hooks.js';
import { useActiveProject } from '../scene/useActiveProject.js';

/** The nine projects, fixed at the top right of the stage (desktop only) while the visitor is among the projects. */
export default function ProjectIndex({ hrefFor }) {
  const active = useActiveProject();
  const section = useSection();
  return (
    <nav className={section === 'projects' ? 'index is-on' : 'index'} aria-label="Projects">
      <ul>
        {projects.map((p) => (
          <li key={p.slug}>
            <Link to={hrefFor(p.slug)} aria-current={p.slug === active ? 'true' : undefined}>
              {p.short}
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}
