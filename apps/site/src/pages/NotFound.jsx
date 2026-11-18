import { Link } from 'react-router';

/** Anything the router does not know, and a /work/ slug that is not a project. */
export default function NotFound() {
  return (
    <section className="sec" aria-labelledby="lost-name">
      <title>Page not found, Remy Post</title>
      <h1 id="lost-name" className="display">
        This page doesn’t exist.
      </h1>
      <div className="actions">
        <Link className="btn btn--solid" to={{ pathname: '/', hash: '#projects' }}>
          Go to the projects
        </Link>
      </div>
    </section>
  );
}
