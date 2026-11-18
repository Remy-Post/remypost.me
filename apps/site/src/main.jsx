import { StrictMode, Suspense, lazy } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router';
import '@fontsource-variable/instrument-sans/wdth.css';
import './styles/site.css';
import ErrorBoundary from './components/ErrorBoundary.jsx';
import Frame from './components/Frame.jsx';
import Home from './pages/Home.jsx';
import NotFound from './pages/NotFound.jsx';


/**
 * The case-study page is its own chunk, fetched when the browser is idle after the first paint, so the page a visitor
 * lands on carries nothing of it. By the time a case study is opened the chunk is already there.
 */
const loadProject = () => import('./pages/Project.jsx');
const Project = lazy(loadProject);
// The preload is only a head start: if it fails (a blocked or stale file) nothing is wrong yet; opening the page will say so.
const preload = () => loadProject().catch(() => {});
if ('requestIdleCallback' in window) requestIdleCallback(preload, { timeout: 4000 });
else setTimeout(preload, 2000);

/** Routes of the old brand-book site that now land somewhere on the new one. */
const redirects = [
  ['work', '/#projects'],
  ['resume', '/#experience'],
  ['brand', '/'],
  ['identity', '/'],
  ['history', '/'],
  ['writing', '/'],
  ['writing/*', '/'],
];

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <ErrorBoundary>
        <Routes>
          <Route element={<Frame />}>
            <Route index element={<Home />} />
            <Route
              path="work/:slug"
              element={
                <Suspense fallback={null}>
                  <Project />
                </Suspense>
              }
            />
            <Route path="*" element={<NotFound />} />
          </Route>
          {redirects.map(([path, to]) => (
            <Route key={path} path={path} element={<Navigate to={to} replace />} />
          ))}
        </Routes>
      </ErrorBoundary>
    </BrowserRouter>
  </StrictMode>,
);
