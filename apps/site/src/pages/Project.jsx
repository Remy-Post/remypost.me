import { Link, useParams } from 'react-router';
import { useLive } from '../components/Objects.jsx';
import { useCanonical } from '../components/useCanonical.js';
import { cases } from '../content/cases.js';
import { projects } from '../content/site.js';
import NotFound from './NotFound.jsx';

/** `/work/:slug`: the case study. An unknown slug is the 404. */
export default function Project() {
  const { slug } = useParams();
  const i = projects.findIndex((p) => p.slug === slug);
  const live = useLive(projects[i]?.object);
  useCanonical(i < 0 ? '/' : `/work/${slug}`);
  if (i < 0) return <NotFound />;
  const p = projects[i];
  const next = projects[(i + 1) % projects.length];
  return (
    <article className="case" aria-labelledby="case-name">
      <title>{`${p.name}, Remy Post`}</title>
      <Link className="back" to={{ pathname: '/', hash: `#${p.slug}` }}>
        Back to all projects
      </Link>
      <p className="meta">
        {p.kind}, {p.year}
      </p>
      <h1 id="case-name" className="display">
        {p.name}
      </h1>
      <p>{p.remark}</p>
      {live && <p className="meta">{p.hint}</p>}
      {p.repo && (
        <div className="actions">
          <a className="btn btn--line" href={p.repo}>
            Source on GitHub
          </a>
        </div>
      )}
      <dl className="facts">
        <div>
          <dt>Type</dt>
          <dd>{p.kind}</dd>
        </div>
        <div>
          <dt>Year</dt>
          <dd>{p.year}</dd>
        </div>
        <div>
          <dt>Built with</dt>
          <dd>{p.stack.join(', ')}</dd>
        </div>
      </dl>
      <section>
        <h2>The problem</h2>
        <p>{cases[p.slug].problem}</p>
      </section>
      <section>
        <h2>What I did</h2>
        <p>{cases[p.slug].did}</p>
      </section>
      <section>
        <h2>How it turned out</h2>
        <p>{cases[p.slug].result}</p>
      </section>
      <Link className="next" to={`/work/${next.slug}`}>
        <span className="next__label">Next project</span>
        <span className="next__name">{next.name}</span>
      </Link>
    </article>
  );
}
