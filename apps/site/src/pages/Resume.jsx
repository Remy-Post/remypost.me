import { education, jobs, person, skills } from '../content/base.js';
import { useCopy } from '../content/copy/index.jsx';
import Opener, { Section } from '../components/Opener.jsx';
import { ArrowUpRight, Download } from '../components/Icons.jsx';
import { usePageTitle } from '../components/Reveal.js';

export default function Resume() {
  const { copy } = useCopy();
  usePageTitle('06 Credentials — Remy Post', 'Remy Post’s resume: experience, education and skills.');
  return (
    <>
      <Opener no="06" title="Credentials" intro={copy.availability}>
        <div className="btns opener__btns reveal" style={{ '--d': '220ms' }}>
          <a className="btn" href={person.resumePdf} download>
            Download PDF <Download />
          </a>
          <a className="btn btn--line" href={person.linkedin} target="_blank" rel="noreferrer">
            LinkedIn <ArrowUpRight />
          </a>
          <a className="btn btn--line" href={person.github} target="_blank" rel="noreferrer">
            GitHub <ArrowUpRight />
          </a>
        </div>
      </Opener>

      <Section no="06.1" title="Experience">
        {jobs.map((j, i) => {
          const e = copy.experience[j.key];
          return (
            <article key={j.key} className="cv reveal" style={{ '--d': `${i * 60}ms` }}>
              <div className="cv__when mono">{j.when}</div>
              <div>
                <h3 className="cv__org">{j.org}</h3>
                <p className="cv__role">{j.role}</p>
                <p className="cv__remark voice copy">{e.remark}</p>
                <ul className="cv__points">
                  {e.points.map((pt, k) => (
                    <li key={k} className="copy">
                      {pt}
                    </li>
                  ))}
                </ul>
              </div>
            </article>
          );
        })}
      </Section>

      <Section no="06.2" title="Education">
        {education.map((e) => (
          <article key={e.org} className="cv reveal">
            <div className="cv__when mono">{e.when}</div>
            <div>
              <h3 className="cv__org">{e.org}</h3>
              <p className="cv__role">{e.role}</p>
            </div>
          </article>
        ))}
      </Section>

      <Section no="06.3" title="Skills">
        <dl className="skills">
          {skills.map(([k, v], i) => (
            <div key={k} className="reveal" style={{ '--d': `${i * 50}ms` }}>
              <dt className="mono">{k}</dt>
              <dd>{v}</dd>
            </div>
          ))}
        </dl>
      </Section>

      <Section no="06.4" title="The document">
        <object className="pdf reveal" data={`${person.resumePdf}#view=FitH`} type="application/pdf" aria-label="Resume PDF">
          <p>
            Your browser can’t show PDFs inline.{' '}
            <a className="ul" href={person.resumePdf}>
              Download it instead.
            </a>
          </p>
        </object>
      </Section>
    </>
  );
}
