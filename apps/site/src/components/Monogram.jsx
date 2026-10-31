/** The monogram: R over P in a square. Drawn as text so it inherits the brand face. */
export default function Monogram({ size = 40, invert = false, className = '' }) {
  return (
    <span className={`monogram ${invert ? 'monogram--invert' : ''} ${className}`} style={{ '--m': `${size}px` }} aria-hidden="true">
      <span>R</span>
      <span>P</span>
    </span>
  );
}
