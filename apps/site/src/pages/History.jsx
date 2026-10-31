import { useCopy } from '../content/copy/index.jsx';
import Opener from '../components/Opener.jsx';
import { usePageTitle } from '../components/Reveal.js';

export default function History() {
  const { copy } = useCopy();
  usePageTitle('04 History — Remy Post', copy.historyIntro);
  return (
    <>
      <Opener no="04" title="History" intro={copy.historyIntro} />
      <ol className="wrap timeline">
        {copy.timeline.map((t, i) => (
          <li key={i} className="tl reveal">
            <span className="tl__year">{t.year}</span>
            <span className="tl__place mono copy">{t.place}</span>
            <div className="tl__body">
              <h2 className="copy">{t.title}</h2>
              <p className="copy">{t.blurb}</p>
            </div>
          </li>
        ))}
      </ol>
    </>
  );
}
