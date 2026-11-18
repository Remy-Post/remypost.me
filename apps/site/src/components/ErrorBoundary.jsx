import { Component } from 'react';

/**
 * Around the routes: if something throws while a page renders, or a page's chunk fails to load (a blocked or stale file
 * after a deploy), the visitor gets a plain page with a reload button instead of a blank screen.
 */
export default class ErrorBoundary extends Component {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  componentDidCatch(error) {
    console.error('The page failed to render.', error);
  }

  render() {
    if (!this.state.failed) return this.props.children;
    return (
      <main className="fail">
        <h1 className="fail__title">Something went wrong</h1>
        <p>The page could not be shown. Reloading usually fixes it.</p>
        <p>
          <button type="button" className="btn btn--solid" onClick={() => window.location.reload()}>
            Reload
          </button>{' '}
          <a className="btn btn--line" href="/">
            Go to the start
          </a>
        </p>
      </main>
    );
  }
}
