import { useState } from 'react';
import { palette, typefaces } from '../content/base.js';
import { useCopy } from '../content/copy/index.jsx';
import Monogram from '../components/Monogram.jsx';
import Opener, { Section } from '../components/Opener.jsx';
import { usePageTitle } from '../components/Reveal.js';

/** Share of a typical page each colour covers — the 60/30/10 idea, stretched to five. */
const proportion = [
  ['bone', 68],
  ['ink', 20],
  ['stone', 7],
  ['pine', 4],
  ['clay', 1],
];

const scale = [
  { name: 'Display', spec: 'Archivo 125% · 500 · 96/1.0', style: { fontSize: 'clamp(48px, 7vw, 96px)', fontStretch: '125%', fontWeight: 500 } },
  { name: 'Title', spec: 'Archivo 100% · 500 · 44/1.05', style: { fontSize: 'clamp(30px, 3.6vw, 44px)', fontWeight: 500 } },
  { name: 'Voice', spec: 'Newsreader · 400 · 26/1.35', style: { fontSize: 26, fontFamily: 'var(--f-voice)', letterSpacing: 0 } },
  { name: 'Body', spec: 'Archivo 100% · 400 · 16/1.55', style: { fontSize: 16, letterSpacing: 0 } },
  { name: 'Label', spec: 'Fragment Mono · 11/1.5', style: { fontSize: 11, fontFamily: 'var(--f-mono)', letterSpacing: '0.02em' } },
];

function Copyable({ value, children, className }) {
  const [done, setDone] = useState(false);
  return (
    <button
      className={className}
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(value);
          setDone(true);
          setTimeout(() => setDone(false), 1400);
        } catch {
          /* clipboard blocked — nothing to do */
        }
      }}
      aria-label={`Copy ${value}`}
    >
      {children}
      <span className="mono swatch__copy">{done ? 'Copied' : 'Copy'}</span>
    </button>
  );
}

export default function Identity() {
  const { copy } = useCopy();
  usePageTitle('02 Identity — Remy Post', copy.identityIntro);

  return (
    <>
      <Opener no="02" title="Identity" intro={copy.identityIntro} />

      <Section no="02.1" title="Wordmark" note={copy.logoNote}>
        <figure className="mark-plate reveal">
          <div className="mark-plate__stage">
            <span className="mark-plate__word">Remy Post</span>
          </div>
          <figcaption className="mark-plate__cap mono">
            <span>Archivo · width 125% · weight 560 · tracking −2%</span>
            <span>Clear space = cap height on every side</span>
          </figcaption>
        </figure>
        <div className="marks">
          <figure className="mark-tile reveal">
            <Monogram size={96} />
            <figcaption className="mono">Monogram · on Bone</figcaption>
          </figure>
          <figure className="mark-tile mark-tile--ink reveal" style={{ '--d': '80ms' }}>
            <Monogram size={96} invert />
            <figcaption className="mono">Monogram · reversed</figcaption>
          </figure>
          <figure className="mark-tile reveal" style={{ '--d': '160ms' }}>
            <div className="mark-sizes">
              <Monogram size={48} />
              <Monogram size={32} />
              <Monogram size={20} />
            </div>
            <figcaption className="mono">Minimum size · 20 px</figcaption>
          </figure>
        </div>
      </Section>

      <Section no="02.2" title="Typography">
        <div className="faces">
          {typefaces.map((t, i) => (
            <article key={t.name} className="face reveal" style={{ '--d': `${i * 80}ms` }}>
              <span className="face__sample" style={{ fontFamily: t.family }}>
                Aa
              </span>
              <h3 className="face__name" style={{ fontFamily: t.family }}>
                {t.name}
              </h3>
              <p className="label">{t.role}</p>
              <p className="label">{t.axes}</p>
              <p className="face__why copy">{copy.typeWhy[t.name]}</p>
            </article>
          ))}
        </div>
        <div className="scale">
          {scale.map((s, i) => (
            <div key={s.name} className="scale__row reveal" style={{ '--d': `${i * 50}ms` }}>
              <span className="scale__meta mono">
                <b>{s.name}</b>
                {s.spec}
              </span>
              <span className="scale__sample" style={s.style}>
                Remy Post
              </span>
            </div>
          ))}
        </div>
      </Section>

      <Section no="02.3" title="Colour" note={copy.colourIntro}>
        <div className="swatches">
          {palette.map((c, i) => (
            <article key={c.key} className={`swatch swatch--${c.key} reveal`} style={{ '--d': `${i * 70}ms` }}>
              <Copyable value={c.hex} className="swatch__chip">
                <span className="swatch__name">{c.name}</span>
              </Copyable>
              <dl className="swatch__spec mono">
                <div>
                  <dt>Light</dt>
                  <dd>{c.hex}</dd>
                </div>
                <div>
                  <dt>Dark</dt>
                  <dd>{c.dark}</dd>
                </div>
                <div>
                  <dt>On Bone</dt>
                  <dd>{c.contrast}</dd>
                </div>
              </dl>
              <p className="swatch__role">{c.role}</p>
              <p className="swatch__why copy">{copy.colourWhy[c.key]}</p>
            </article>
          ))}
        </div>
        <figure className="proportion reveal">
          <div className="proportion__bar">
            {proportion.map(([k, v]) => (
              <span key={k} className={`proportion__seg swatch--${k}`} style={{ flexGrow: v }} title={`${k} ${v}%`} />
            ))}
          </div>
          <figcaption className="proportion__legend mono">
            {proportion.map(([k, v]) => (
              <span key={k}>
                <i className={`swatch--${k}`} /> {k[0].toUpperCase() + k.slice(1)} {v}%
              </span>
            ))}
          </figcaption>
        </figure>
      </Section>

      <Section no="02.4" title="Voice">
        <div className="voice-table">
          <div className="voice-table__head mono reveal">
            <span>I say</span>
            <span>I don’t say</span>
          </div>
          {copy.voice.map((v, i) => (
            <div key={i} className="voice-table__row reveal" style={{ '--d': `${i * 70}ms` }}>
              <p className="voice copy">{v.say}</p>
              <p className="copy">
                <s>{v.dont}</s>
              </p>
            </div>
          ))}
        </div>
      </Section>

      <Section no="02.5" title="Motion">
        <div className="motion reveal">
          <div className="motion__demo" aria-hidden="true">
            <span />
          </div>
          <dl className="motion__spec mono">
            <div>
              <dt>Duration</dt>
              <dd>600–700 ms</dd>
            </div>
            <div>
              <dt>Curve</dt>
              <dd>cubic-bezier(.22,.61,.24,1)</dd>
            </div>
            <div>
              <dt>Distance</dt>
              <dd>8–14 px, never more</dd>
            </div>
            <div>
              <dt>Rule</dt>
              <dd>Move to explain, not to impress. Off under reduced motion.</dd>
            </div>
          </dl>
        </div>
      </Section>
    </>
  );
}
