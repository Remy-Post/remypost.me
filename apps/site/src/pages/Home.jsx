import { Link } from 'react-router';
import { useLive, useStatus } from '../components/Objects.jsx';
import { clearHot, setHot } from '../scene/hot.js';
import { useHot } from '../scene/hooks.js';
import { education, intro, jobs, links, person, projects, skills } from '../content/site.js';

const toProjects = { pathname: '/', hash: '#projects' };

/** Pointer and focus handlers that tell the stage what this piece of text stands for (scene/hot.js). */
const points = (kind, ids) => ({
  onPointerEnter: () => setHot(kind, ids),
  onPointerLeave: () => clearHot(kind),
  onFocus: () => setHot(kind, ids),
  onBlur: () => clearHot(kind),
});

/** A line saying what to do with an object: shown only while that object is really on the stage. */
function Hint({ name, children }) {
  return useLive(name) ? <p className="hint">{children}</p> : null;
}

/**
 * `/`: the intro, education, work, the nine projects and the links. The scroll position drives the stage
 * (scene/progress.js); each section has its own object on it.
 */
export default function Home() {
  const status = useStatus();
  const experienceLive = useLive('experience');
  const hot = useHot();
  const lit = (kind, ids) => hot.kind === kind && ids.some((id) => hot.ids.includes(id));
  return (
    <>
      <title>Remy Post, developer</title>
      <section id="top" className="sec sec--intro" aria-labelledby="intro-name">
        <h1 id="intro-name" className="display">
          {person.name}
        </h1>
        <p>{intro.lead}</p>
        <p>{intro.availability}</p>
        <div className="actions">
          <Link className="btn btn--solid" to={toProjects}>
            See the projects
          </Link>
          <a className="btn btn--line" href={person.resumePdf} download>
            Download résumé
          </a>
        </div>
        {status === 'live' && <p className="hint">{intro.hint}</p>}
      </section>

      <section id="education" className="sec sec--steps" aria-labelledby="education-name">
        <h2 id="education-name" className="display">
          Education
        </h2>
        {education.map((e) => (
          <article key={e.key} className="step" data-step={e.key}>
            <p className="meta">{e.when}</p>
            <h3 className="step__title" lang={e.lang}>
              {e.school}
            </h3>
            <p>{e.text}</p>
          </article>
        ))}
      </section>

      <section id="experience" className="sec sec--steps" aria-labelledby="experience-name">
        <h2 id="experience-name" className="display">
          Work experience
        </h2>
        {jobs.map((j) => (
          <article key={j.key} className="step" data-step={j.key}>
            <p className="meta">{j.when}</p>
            <h3 className="step__title">{j.org}</h3>
            <p className="step__role">{j.role}</p>
            <p>{j.remark}</p>
            <ul className="points">
              {j.points.map((pt) => (
                <li key={pt.text} className={lit('patch', pt.patches) ? 'is-lit' : undefined} tabIndex={pt.patches.length && experienceLive ? 0 : undefined} {...(pt.patches.length ? points('patch', pt.patches) : {})}>
                  {pt.text}
                </li>
              ))}
            </ul>
          </article>
        ))}
        <div className="skills">
          <h3 className="step__title">Skills</h3>
          <dl>
            {skills.map(([name, list]) => (
              <div key={name}>
                <dt>{name}</dt>
                <dd>{list}</dd>
              </div>
            ))}
          </dl>
        </div>
      </section>

      <div id="projects" className="projects">
        {projects.map((p, i) => (
          <section key={p.slug} id={p.slug} className="sec" aria-labelledby={`${p.slug}-name`}>
            {i === 0 && <h2 className="projects__title">Projects</h2>}
            <p className="meta">
              {p.kind}, {p.year}
            </p>
            <h2 id={`${p.slug}-name`} className="display">
              {p.name}
            </h2>
            <p>{p.remark}</p>
            <p className="meta">{p.stack.join(', ')}</p>
            <div className="actions">
              <Link className="btn btn--solid" to={`/work/${p.slug}`}>
                Read the case study
              </Link>
              {p.repo && (
                <a className="btn btn--line" href={p.repo}>
                  Source on GitHub
                </a>
              )}
              {p.status && <span className="status">{p.status}</span>}
            </div>
            {p.hint && <Hint name={p.object}>{p.hint}</Hint>}
          </section>
        ))}
      </div>

      <section id="links" className="sec" aria-labelledby="links-name">
        <h2 id="links-name" className="display">
          Important links
        </h2>
        <ul className="links">
          {links.map((l) => (
            <li key={l.key}>
              <a className={lit('key', [l.key]) ? 'link is-lit' : 'link'} href={l.href} data-key={l.key} download={l.download ? '' : undefined} {...points('key', [l.key])}>
                <span className="link__label">{l.label}</span>
                {l.detail && <span className="link__detail">{l.detail}</span>}
              </a>
            </li>
          ))}
        </ul>
      </section>
    </>
  );
}
