import { useEffect, useState } from 'react';
import { Link, NavLink, Outlet, useLocation } from 'react-router';
import { chapters, edition, neighbours, person } from '../content/base.js';
import { showSwitcher, useCopy, variants } from '../content/copy/index.jsx';
import { Arrow, Half } from './Icons.jsx';
import Monogram from './Monogram.jsx';
import { useReveal } from './Reveal.js';

/** Which chapter a path belongs to ("/work/agentui" → "03"). */
export function chapterFor(pathname) {
  const top = '/' + (pathname.split('/')[1] || '');
  return chapters.find((c) => c.path === top) || null;
}

function ThemeToggle() {
  const [theme, setTheme] = useState(() => {
    try {
      return localStorage.getItem('theme');
    } catch {
      return null;
    }
  });
  useEffect(() => {
    if (theme) document.documentElement.dataset.theme = theme;
    else delete document.documentElement.dataset.theme;
  }, [theme]);
  const dark = theme ? theme === 'dark' : window.matchMedia('(prefers-color-scheme: dark)').matches;
  const flip = () => {
    const next = dark ? 'light' : 'dark';
    setTheme(next);
    try {
      localStorage.setItem('theme', next);
    } catch {
      /* not persisted in private mode */
    }
  };
  return (
    <button className="bar__btn" onClick={flip} aria-label={`Switch to ${dark ? 'light' : 'dark'} mode`}>
      <Half />
    </button>
  );
}

function Bar({ open, setOpen }) {
  const { pathname } = useLocation();
  const ch = chapterFor(pathname);
  return (
    <header className="bar">
      <div className="bar__inner">
        <Link to="/" className="bar__brand" aria-label="Remy Post — cover">
          <Monogram size={26} />
          <span className="bar__name">Remy Post</span>
        </Link>
        <span className="bar__spec mono">
          Identity Guidelines <i>/</i> v{edition.version} <i>/</i> {edition.date}
        </span>
        <nav className="bar__nav" aria-label="Chapters">
          {chapters.slice(1).map((c) => (
            <NavLink key={c.no} to={c.path} className="bar__link mono">
              <span>{c.no}</span>
              {c.short}
            </NavLink>
          ))}
        </nav>
        <div className="bar__tools">
          <span className="bar__page mono" aria-hidden="true">
            {ch ? ch.no : '—'} / {chapters[chapters.length - 1].no}
          </span>
          <ThemeToggle />
          <button className="bar__btn bar__menu" onClick={() => setOpen(!open)} aria-expanded={open} aria-controls="index">
            <span className="mono">{open ? 'Close' : 'Index'}</span>
          </button>
        </div>
      </div>
    </header>
  );
}

function Index({ open }) {
  return (
    <div id="index" className={`index ${open ? 'is-open' : ''}`} aria-hidden={!open} inert={!open ? '' : undefined}>
      <div className="wrap index__inner">
        <p className="label">Contents</p>
        <ol className="index__list">
          {chapters.map((c, i) => (
            <li key={c.no} style={{ '--i': i }}>
              <NavLink to={c.path} end={c.path === '/'} className="index__link">
                <span className="mono">{c.no}</span>
                <span className="index__title">{c.title}</span>
              </NavLink>
            </li>
          ))}
        </ol>
        <div className="index__foot mono">
          <a href={person.github} target="_blank" rel="noreferrer">
            GitHub ↗
          </a>
          <a href={person.linkedin} target="_blank" rel="noreferrer">
            LinkedIn ↗
          </a>
          <a href={person.resumePdf} download>
            Resume PDF ↓
          </a>
        </div>
      </div>
    </div>
  );
}

/** Big "next chapter" link at the foot of every chapter. */
function NextChapter() {
  const { pathname } = useLocation();
  const ch = chapterFor(pathname);
  if (!ch) return null;
  const i = chapters.indexOf(ch);
  const next = chapters[(i + 1) % chapters.length];
  return (
    <Link to={next.path} className="next wrap reveal">
      <span className="label">Next — {next.no}</span>
      <span className="next__title">
        {next.title}
        <Arrow />
      </span>
    </Link>
  );
}

function Colophon() {
  const { copy } = useCopy();
  return (
    <footer className="colophon">
      <div className="wrap colophon__grid">
        <div className="colophon__cta">
          <p className="label">Contact</p>
          <p className="colophon__line voice copy">{copy.contactCta}</p>
          <a className="colophon__mail ul" href={`mailto:${person.email}`}>
            {person.email}
          </a>
        </div>
        <dl className="colophon__spec mono">
          <div>
            <dt>Elsewhere</dt>
            <dd>
              <a className="ul" href={person.github} target="_blank" rel="noreferrer">
                GitHub
              </a>
              {' · '}
              <a className="ul" href={person.linkedin} target="_blank" rel="noreferrer">
                LinkedIn
              </a>
              {' · '}
              <a className="ul" href={person.resumePdf} download>
                Resume
              </a>
            </dd>
          </div>
          <div>
            <dt>Set in</dt>
            <dd>Archivo, Newsreader &amp; Fragment Mono</dd>
          </div>
          <div>
            <dt>Colour</dt>
            <dd>Clay &amp; Ink</dd>
          </div>
          <div>
            <dt>Built</dt>
            <dd>React, by hand, in {person.location}. No cookies, no trackers.</dd>
          </div>
          <div>
            <dt>Next door</dt>
            <dd>
              {neighbours.map((site, i) => (
                <span key={site.name}>
                  {i > 0 && ' · '}
                  <a className="ul" href={site.url}>
                    {site.name}
                  </a>
                </span>
              ))}
            </dd>
          </div>
        </dl>
      </div>
      <div className="wrap colophon__fine mono">
        <span>© 2026 Remy Post · Identity Guidelines v{edition.version}</span>
        <span>
          <a className="ul" href="/privacy.html">
            My n8n privacy
          </a>{' '}
          ·{' '}
          <a className="ul" href="/terms.html">
            terms
          </a>
        </span>
      </div>
    </footer>
  );
}

function CopySwitcher() {
  const { id, setId } = useCopy();
  if (!showSwitcher()) return null;
  return (
    <div className="switcher mono" role="group" aria-label="Copy variant (mock)">
      <span>Mock copy</span>
      {Object.values(variants).map((v) => (
        <button key={v.id} className={v.id === id ? 'is-on' : ''} aria-pressed={v.id === id} onClick={() => setId(v.id)}>
          {v.id === 'researched' ? 'Researched' : 'Draft'}
        </button>
      ))}
    </div>
  );
}

export default function Book() {
  const { pathname } = useLocation();
  const [open, setOpen] = useState(false);
  const { id } = useCopy();
  useReveal();
  useEffect(() => {
    setOpen(false);
    window.scrollTo(0, 0);
  }, [pathname]);
  useEffect(() => {
    const onKey = (e) => e.key === 'Escape' && setOpen(false);
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  return (
    <>
      <a href="#main" className="skip">
        Skip to content
      </a>
      <Bar open={open} setOpen={setOpen} />
      <Index open={open} />
      <main id="main" key={`${pathname}:${id}`} className="route">
        <Outlet />
        <NextChapter />
      </main>
      <Colophon />
      <CopySwitcher />
    </>
  );
}
