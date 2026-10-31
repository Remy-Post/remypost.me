import { Link } from 'react-router';
import { projects } from '../content/base.js';
import { useCopy } from '../content/copy/index.jsx';
import Opener, { Section } from '../components/Opener.jsx';
import { Arrow } from '../components/Icons.jsx';
import { usePageTitle } from '../components/Reveal.js';

export default function Brand() {
  const { copy } = useCopy();
  usePageTitle('01 The brand — Remy Post', copy.mission);
  const samples = projects.slice(0, 3);

  return (
    <>
      <Opener no="01" title="The brand" intro={copy.brandIntro} />

      <Section no="01.1" title="Positioning">
        <div className="position reveal">
          <span className="label">Statement</span>
          <p className="position__text copy">{copy.positioning}</p>
        </div>
      </Section>

      <Section no="01.2" title="Mission">
        <p className="statement voice copy reveal">{copy.mission}</p>
      </Section>

      <Section no="01.3" title="Values">
        <ol className="values">
          {copy.values.map((v, i) => (
            <li key={i} className="value reveal" style={{ '--d': `${i * 90}ms` }}>
              <span className="mono">0{i + 1}</span>
              <h3 className="value__name copy">{v.name}</h3>
              <p className="copy">{v.line}</p>
            </li>
          ))}
        </ol>
      </Section>

      <Section no="01.4" title="Principle">
        <div className="principle reveal">
          <h3 className="principle__title copy">{copy.principle.title}</h3>
          <p className="principle__body voice copy">{copy.principle.body}</p>
        </div>
        <div className="applied">
          <p className="label reveal">Applied — the remark, from three projects</p>
          {samples.map((p, i) => (
            <Link key={p.slug} to={`/work/${p.slug}`} className="applied__row reveal" style={{ '--d': `${i * 70}ms` }}>
              <span className="mono">{p.name}</span>
              <span className="applied__text voice copy">“{copy.projects[p.slug].remark}”</span>
              <Arrow />
            </Link>
          ))}
        </div>
      </Section>
    </>
  );
}
