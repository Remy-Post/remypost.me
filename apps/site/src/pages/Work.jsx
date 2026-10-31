import { Link, useParams } from 'react-router';
import { projects } from '../content/base.js';
import { useCopy } from '../content/copy/index.jsx';
import Opener from '../components/Opener.jsx';
import { Arrow, ArrowUpRight } from '../components/Icons.jsx';
import { usePageTitle } from '../components/Reveal.js';
import NotFound from './NotFound.jsx';

/** A project's "application plate": its own tiny identity, in two colours and a mark. */
export function Plate({ p, big = false }) {
  return (
    <div className={`plate ${big ? 'plate--big' : ''}`} style={{ '--pb': p.plate.bg, '--pf': p.plate.fg }} aria-hidden="true">
      <span className="plate__mark">{p.plate.mark}</span>
      <span className="plate__name">{p.name}</span>
      <span className="plate__meta mono">
        {p.kind} · {p.year}
      </span>
    </div>
  );
}

export function WorkIndex() {
  const { copy } = useCopy();
  usePageTitle('03 Applications — Remy Post', copy.workIntro);
  return (
    <>
      <Opener no="03" title="Applications" intro={copy.workIntro} />
      <section className="wrap apps">
        {projects.map((p, i) => (
          <Link key={p.slug} to={`/work/${p.slug}`} className="app reveal" style={{ '--d': `${(i % 2) * 90}ms` }}>
            <Plate p={p} />
            <div className="app__text">
              <span className="mono app__meta">
                03.{i + 1} · {p.kind} · {p.year}
                {p.status ? ` · ${p.status}` : ''}
              </span>
              <h2 className="app__name">{p.name}</h2>
              <p className="app__remark voice copy">{copy.projects[p.slug].remark}</p>
              <span className="app__go mono">
                Read the application <Arrow />
              </span>
            </div>
          </Link>
        ))}
      </section>
    </>
  );
}

export function WorkDetail() {
  const { slug } = useParams();
  const { copy } = useCopy();
  const i = projects.findIndex((p) => p.slug === slug);
  const p = projects[i];
  usePageTitle(p ? `${p.name} — Remy Post` : 'Not found — Remy Post', p && copy.projects[p.slug].remark);
  if (!p) return <NotFound />;
  const t = copy.projects[p.slug];
  const next = projects[(i + 1) % projects.length];

  return (
    <article className="case">
      <div className="wrap">
        <Link to="/work" className="mono case__back ul">
          ← All applications
        </Link>
      </div>
      <header className="wrap case__head">
        <div className="case__title">
          <p className="mono reveal">
            03.{i + 1} · {p.kind} · {p.year}
            {p.status ? ` · ${p.status}` : ''}
          </p>
          <h1 className="reveal" style={{ '--d': '60ms' }}>
            {p.name}
          </h1>
          <p className="case__remark voice copy reveal" style={{ '--d': '120ms' }}>
            {t.remark}
          </p>
        </div>
        <div className="reveal" style={{ '--d': '160ms' }}>
          <Plate p={p} big />
        </div>
      </header>

      <div className="wrap case__body">
        <dl className="case__spec mono reveal">
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
          <div>
            <dt>Source</dt>
            <dd>
              {p.repo ? (
                <a className="ul" href={p.repo} target="_blank" rel="noreferrer">
                  GitHub <ArrowUpRight style={{ width: 12, display: 'inline' }} />
                </a>
              ) : (
                'Private — walkthrough on request'
              )}
            </dd>
          </div>
        </dl>
        <div className="case__story">
          {[
            ['Problem', t.problem],
            ['Role', t.role],
            ['Outcome', t.outcome],
          ].map(([k, v], j) => (
            <section key={k} className="case__part reveal" style={{ '--d': `${j * 60}ms` }}>
              <h2 className="mono">{k}</h2>
              <p className="copy">{v}</p>
            </section>
          ))}
        </div>
      </div>

      <div className="wrap">
        <Link to={`/work/${next.slug}`} className="case__next reveal">
          <span className="label">Next application</span>
          <span className="case__next-name">
            {next.name} <Arrow />
          </span>
        </Link>
      </div>
    </article>
  );
}
