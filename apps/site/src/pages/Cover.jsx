import { Link } from 'react-router';
import { chapters, edition, jobs, person } from '../content/base.js';
import { useCopy } from '../content/copy/index.jsx';
import { Arrow, Download } from '../components/Icons.jsx';
import { usePageTitle } from '../components/Reveal.js';

/** One-line summaries for the contents page, keyed by chapter number. */
const blurbs = {
  '01': 'Positioning, mission, values and the one principle behind it all.',
  '02': 'Wordmark, typography, colour and voice — and why each was chosen.',
  '03': 'Projects, read as applications of the brand.',
  '04': 'Where I’ve been, and what each stop cost and bought.',
  '05': 'Short letters on what building things taught me.',
  '06': 'Experience, education, skills, and the PDF.',
};

export default function Cover() {
  const { copy } = useCopy();
  usePageTitle('Remy Post — Identity Guidelines', copy.positioning);

  return (
    <>
      <section className="cover wrap">
        <div className="cover__meta mono">
          <span>Identity Guidelines</span>
          <span>Version {edition.version}</span>
          <span>{edition.date}</span>
          <span>{person.location}</span>
        </div>

        <h1 className="wordmark" aria-label="Remy Post">
          <span className="wordmark__line">Remy</span>
          <span className="wordmark__line">Post</span>
        </h1>

        <div className="cover__grid">
          <p className="cover__tagline voice copy reveal">{copy.tagline}</p>
          <div className="cover__intro reveal" style={{ '--d': '120ms' }}>
            <p className="copy">{copy.positioning}</p>
            <div className="btns">
              <Link to="/brand" className="btn">
                Read the book <Arrow />
              </Link>
              <a href={person.resumePdf} className="btn btn--line" download>
                Resume <Download />
              </a>
            </div>
          </div>
        </div>
      </section>

      <section className="wrap glance reveal" aria-label="At a glance">
        <div className="rule" />
        <dl className="glance__grid">
          <div>
            <dt className="label">Role</dt>
            <dd>Developer, CS student</dd>
          </div>
          <div>
            <dt className="label">Studying</dt>
            <dd>BSc CS + diploma, Lakehead–Georgian, year 3</dd>
          </div>
          <div>
            <dt className="label">Most recent</dt>
            <dd>{jobs[0].role}, DND</dd>
          </div>
          <div>
            <dt className="label">Status</dt>
            <dd className="copy">{copy.availability}</dd>
          </div>
        </dl>
      </section>

      <section className="wrap contents">
        <header className="contents__head reveal">
          <p className="label">Contents</p>
          <p className="contents__intro voice copy">{copy.intro}</p>
        </header>
        <ol className="contents__list">
          {chapters.slice(1).map((c, i) => (
            <li key={c.no} className="reveal" style={{ '--d': `${i * 60}ms` }}>
              <Link to={c.path} className="contents__row">
                <span className="contents__no mono">{c.no}</span>
                <span className="contents__title">{c.title}</span>
                <span className="contents__blurb">{blurbs[c.no]}</span>
                <Arrow className="contents__arrow" />
              </Link>
            </li>
          ))}
        </ol>
      </section>

      {copy.endorsement && (
        <section className="wrap endorse reveal">
          <blockquote>
            <p className="voice copy">“{copy.endorsement.quote}”</p>
            <footer className="label copy">{copy.endorsement.source}</footer>
          </blockquote>
        </section>
      )}

      <section className="wrap facts">
        {copy.funFacts.map((f, i) => (
          <p key={i} className="fact reveal" style={{ '--d': `${i * 80}ms` }}>
            <span className="label">Fig. 0.{i + 1}</span>
            <span className="copy">{f}</span>
          </p>
        ))}
      </section>
    </>
  );
}
