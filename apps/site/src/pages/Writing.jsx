import { Link, useParams } from 'react-router';
import { useCopy } from '../content/copy/index.jsx';
import Opener from '../components/Opener.jsx';
import { Arrow } from '../components/Icons.jsx';
import { usePageTitle } from '../components/Reveal.js';
import NotFound from './NotFound.jsx';

const fmt = (d) => new Date(`${d}T12:00:00`).toLocaleDateString('en-CA', { day: 'numeric', month: 'long', year: 'numeric' });

export function WritingIndex() {
  const { copy } = useCopy();
  usePageTitle('05 Correspondence — Remy Post', copy.writingIntro);
  return (
    <>
      <Opener no="05" title="Correspondence" intro={copy.writingIntro} />
      <ul className="wrap letters">
        {copy.letters.map((l, i) => (
          <li key={l.slug} className="reveal" style={{ '--d': `${i * 60}ms` }}>
            <Link to={`/writing/${l.slug}`} className="letter-row">
              <span className="mono">No. {l.no}</span>
              <span className="letter-row__title copy">{l.title}</span>
              <span className="letter-row__dek voice copy">{l.dek}</span>
              <span className="mono letter-row__date">
                {fmt(l.date)} · {l.read}
              </span>
              <Arrow className="letter-row__arrow" />
            </Link>
          </li>
        ))}
      </ul>
    </>
  );
}

export function Letter() {
  const { slug } = useParams();
  const { copy } = useCopy();
  const i = copy.letters.findIndex((l) => l.slug === slug);
  const l = copy.letters[i];
  usePageTitle(l ? `${l.title} — Remy Post` : 'Not found — Remy Post', l?.dek);
  if (!l) return <NotFound />;
  const next = copy.letters[(i + 1) % copy.letters.length];

  return (
    <article className="wrap article">
      <Link to="/writing" className="mono ul">
        ← All letters
      </Link>
      <header className="article__head">
        <p className="mono reveal">
          No. {l.no} · {fmt(l.date)} · {l.read}
        </p>
        <h1 className="reveal copy" style={{ '--d': '60ms' }}>
          {l.title}
        </h1>
        <p className="article__dek voice copy reveal" style={{ '--d': '120ms' }}>
          {l.dek}
        </p>
      </header>
      <div className="article__body voice">
        {l.body.map((b, j) => {
          if (typeof b === 'string') return <p key={j} className="copy">{b}</p>;
          if (b.h) return <h2 key={j} className="copy">{b.h}</h2>;
          return (
            <blockquote key={j} className="article__pull copy">
              {b.q}
            </blockquote>
          );
        })}
        <p className="article__sign">— Remy</p>
      </div>
      {copy.letters.length > 1 && (
        <Link to={`/writing/${next.slug}`} className="case__next">
          <span className="label">Next letter</span>
          <span className="case__next-name copy">
            {next.title} <Arrow />
          </span>
        </Link>
      )}
    </article>
  );
}
