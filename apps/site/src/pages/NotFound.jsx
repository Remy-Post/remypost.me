import { Link } from 'react-router';
import { Arrow } from '../components/Icons.jsx';
import { usePageTitle } from '../components/Reveal.js';

export default function NotFound() {
  usePageTitle('Page not found — Remy Post');
  return (
    <section className="wrap lost">
      <p className="mono">Error 404 · Page not in this edition</p>
      <h1>This page isn’t in the book.</h1>
      <p className="voice">It may have moved, or it never existed. The contents page knows where everything is.</p>
      <Link to="/" className="btn">
        Back to the cover <Arrow />
      </Link>
    </section>
  );
}
