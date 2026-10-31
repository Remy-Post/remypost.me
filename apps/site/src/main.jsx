import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Route, Routes } from 'react-router';
import '@fontsource-variable/archivo/wdth.css';
import '@fontsource-variable/newsreader/opsz.css';
import '@fontsource-variable/newsreader/opsz-italic.css';
import '@fontsource/fragment-mono/400.css';
import './styles/base.css';
import './styles/book.css';
import { CopyProvider } from './content/copy/index.jsx';
import Book from './components/Book.jsx';
import Cover from './pages/Cover.jsx';
import Brand from './pages/Brand.jsx';
import Identity from './pages/Identity.jsx';
import { WorkDetail, WorkIndex } from './pages/Work.jsx';
import History from './pages/History.jsx';
import { Letter, WritingIndex } from './pages/Writing.jsx';
import Resume from './pages/Resume.jsx';
import NotFound from './pages/NotFound.jsx';

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <CopyProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<Book />}>
            <Route index element={<Cover />} />
            <Route path="brand" element={<Brand />} />
            <Route path="identity" element={<Identity />} />
            <Route path="work" element={<WorkIndex />} />
            <Route path="work/:slug" element={<WorkDetail />} />
            <Route path="history" element={<History />} />
            <Route path="writing" element={<WritingIndex />} />
            <Route path="writing/:slug" element={<Letter />} />
            <Route path="resume" element={<Resume />} />
            <Route path="*" element={<NotFound />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </CopyProvider>
  </StrictMode>,
);
