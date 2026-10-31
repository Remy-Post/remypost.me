import { createContext, useContext, useEffect, useState } from 'react';
import draft from './draft.js';
import researched from './researched.js';

/** Copy variants share one shape. Add a file here to add a variant. */
export const variants = { researched, draft };

const DEFAULT = variants[import.meta.env.VITE_COPY] ? import.meta.env.VITE_COPY : 'researched';

function initial() {
  try {
    const q = new URLSearchParams(window.location.search).get('copy');
    if (q && variants[q]) return q;
    const s = sessionStorage.getItem('copy');
    if (s && variants[s]) return s;
  } catch {
    /* storage blocked: fall through to the default */
  }
  return DEFAULT;
}

const Ctx = createContext({ copy: variants[DEFAULT], id: DEFAULT, setId: () => {} });

export function CopyProvider({ children }) {
  const [id, setId] = useState(initial);
  useEffect(() => {
    document.documentElement.dataset.copy = id;
    try {
      sessionStorage.setItem('copy', id);
    } catch {
      /* ignore */
    }
  }, [id]);
  return <Ctx.Provider value={{ copy: variants[id], id, setId }}>{children}</Ctx.Provider>;
}

export const useCopy = () => useContext(Ctx);

/** The mock switcher shows in dev, on the preview host, or when ?copy= is in the URL. */
export function showSwitcher() {
  if (import.meta.env.DEV) return true;
  try {
    return window.location.hostname.startsWith('preview.') || new URLSearchParams(window.location.search).has('copy');
  } catch {
    return false;
  }
}
