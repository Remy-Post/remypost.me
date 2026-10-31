/** Chapter opener: big number, title, and the chapter's intro paragraph. */
export default function Opener({ no, title, intro, children }) {
  return (
    <header className="opener wrap">
      <div className="opener__top mono reveal">
        <span>Chapter {no}</span>
        <span>{title}</span>
      </div>
      <div className="rule reveal" />
      <div className="opener__grid">
        <span className="opener__no reveal" aria-hidden="true">
          {no}
        </span>
        <div>
          <h1 className="opener__title reveal" style={{ '--d': '80ms' }}>
            {title}
          </h1>
          {intro && (
            <p className="opener__intro voice copy reveal" style={{ '--d': '160ms' }}>
              {intro}
            </p>
          )}
          {children}
        </div>
      </div>
    </header>
  );
}

/** A numbered sub-section heading inside a chapter (e.g. "02.3 Colour"). */
export function Section({ id, no, title, note, children, className = '' }) {
  return (
    <section id={id} className={`sect wrap ${className}`}>
      <header className="sect__head reveal">
        <span className="mono">{no}</span>
        <h2>{title}</h2>
        {note && <p className="sect__note copy">{note}</p>}
      </header>
      {children}
    </section>
  );
}
