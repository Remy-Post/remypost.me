import { useEffect, useRef, useState } from 'react';
import { Link, useMatch } from 'react-router';
import { person, projects } from '../content/site.js';
import { ObjectsSwitch } from './Objects.jsx';

const PHONE = '(max-width: 759.98px)';
const SECTIONS = ['education', 'experience', 'projects', 'links'];

/**
 * The section being read: the last one whose top has come up into the upper part of the reading area (the stretch below the bar, and on a
 * phone below the stage, `scroll-padding-top`), or the last section when the page is at its end. A link in the bar lands a section's top
 * on that padding, so what it lands on is always marked; a landing that stops a little short (a page with no more room to scroll, as
 * the last section has) still is.
 */
function useReading() {
  const [here, setHere] = useState(null);
  useEffect(() => {
    let frame = 0;
    const read = () => {
      frame = 0;
      const pad = parseFloat(getComputedStyle(document.documentElement).scrollPaddingTop) || 0;
      const line = pad + (window.innerHeight - pad) / 3;
      let now = null;
      for (const id of SECTIONS) {
        const el = document.getElementById(id);
        if (el && el.getBoundingClientRect().top <= line) now = id;
      }
      if (now && window.scrollY + window.innerHeight >= document.documentElement.scrollHeight - 2) now = SECTIONS.at(-1);
      setHere(now);
    };
    const schedule = () => {
      if (!frame) frame = requestAnimationFrame(read);
    };
    read();
    window.addEventListener('scroll', schedule, { passive: true });
    window.addEventListener('resize', schedule);
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener('scroll', schedule);
      window.removeEventListener('resize', schedule);
    };
  }, []);
  return here;
}
const FOCUSABLE = 'a[href], button:not([disabled])';

/**
 * The fixed bar. From 760 px it holds the links; under that they fold into a "Menu" button that opens a plain list
 * (with the projects in it, since the index is hidden). While the menu is open focus stays in the bar and the list
 * (Tab wraps), Escape closes it and returns focus to the button; the page behind is `inert` (see Frame).
 */
export default function Bar({ open, setOpen, hrefFor }) {
  const bar = useRef(null);
  const button = useRef(null);
  // The section being read (on a case study: Projects): marked in the bar and in the menu.
  const reading = useReading();
  const onCase = useMatch('/work/:slug');
  const here = onCase ? 'projects' : reading;
  const mark = (name) => (here === name ? 'location' : undefined);

  // Keys, and the menu closing when the window grows past the phone width, only while it is open.
  useEffect(() => {
    if (!open) return;
    const media = window.matchMedia(PHONE);
    const onMedia = () => !media.matches && setOpen(false);
    const onKey = (e) => {
      if (e.key === 'Escape') {
        setOpen(false);
        button.current.focus();
      }
    };
    media.addEventListener('change', onMedia);
    document.addEventListener('keydown', onKey);
    return () => {
      media.removeEventListener('change', onMedia);
      document.removeEventListener('keydown', onKey);
    };
  }, [open, setOpen]);

  // Focus moves into the menu when it opens, and (when a choice in it closed it) back to its button, not into nowhere.
  const wasOpen = useRef(false);
  useEffect(() => {
    if (open) bar.current.querySelector('.menu a')?.focus();
    else if (wasOpen.current && (!document.activeElement || document.activeElement === document.body)) button.current.focus({ preventScroll: true });
    wasOpen.current = open;
  }, [open]);

  /** Keep Tab inside the bar and the open menu. */
  const trap = (e) => {
    if (!open || e.key !== 'Tab') return;
    const items = [...bar.current.querySelectorAll(FOCUSABLE)].filter((el) => el.getClientRects().length);
    const first = items[0];
    const last = items[items.length - 1];
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  };

  return (
    <header className="bar" ref={bar} onKeyDown={trap}>
      <div className="bar__inner">
        <Link className="bar__brand" to="/">
          {person.name}
        </Link>
        <nav className="bar__links" aria-label="Main">
          <ul>
            <li>
              <Link to={{ pathname: '/', hash: '#education' }} aria-current={mark('education')}>Education</Link>
            </li>
            <li>
              <Link to={{ pathname: '/', hash: '#experience' }} aria-current={mark('experience')}>Experience</Link>
            </li>
            <li>
              <Link to={{ pathname: '/', hash: '#projects' }} aria-current={mark('projects')}>Projects</Link>
            </li>
            <li>
              <Link to={{ pathname: '/', hash: '#links' }} aria-current={mark('links')}>Links</Link>
            </li>
            <li>
              <a href={person.resumePdf}>Résumé</a>
            </li>
          </ul>
        </nav>
        <ObjectsSwitch />
        <button ref={button} type="button" className="bar__menu" aria-expanded={open} aria-controls="menu" onClick={() => setOpen(!open)}>
          Menu
        </button>
      </div>
      {open && (
        <nav id="menu" className="menu" aria-label="Menu" data-lenis-prevent>
          <ul>
            <li>
              <Link to={{ pathname: '/', hash: '#education' }} aria-current={mark('education')}>Education</Link>
            </li>
            <li>
              <Link to={{ pathname: '/', hash: '#experience' }} aria-current={mark('experience')}>Experience</Link>
            </li>
            <li>
              <Link to={{ pathname: '/', hash: '#projects' }} aria-current={mark('projects')}>Projects</Link>
              <ul>
                {projects.map((p) => (
                  <li key={p.slug}>
                    <Link to={hrefFor(p.slug)}>{p.short}</Link>
                  </li>
                ))}
              </ul>
            </li>
            <li>
              <Link to={{ pathname: '/', hash: '#links' }} aria-current={mark('links')}>Links</Link>
            </li>
            <li>
              <a href={person.resumePdf}>Résumé</a>
            </li>
          </ul>
        </nav>
      )}
    </header>
  );
}
