import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

/** The one file worth blocking first paint for: the latin variable face that sets every heading. */
const PRELOAD_FONTS = [/^instrument-sans-latin-wdth-normal-[\w-]+\.woff2$/];

/** Preloads it. Vite hashes the files, so find the emitted names in the bundle. */
function preloadFonts() {
  let base = '/';
  return {
    name: 'preload-fonts',
    configResolved(config) {
      base = config.base;
    },
    transformIndexHtml(html, ctx) {
      if (!ctx.bundle) return; // dev server: fonts are served unhashed, nothing to preload
      const files = Object.keys(ctx.bundle).filter((f) => f.startsWith('assets/'));
      return PRELOAD_FONTS.map((pattern) => {
        const file = files.find((f) => pattern.test(f.slice('assets/'.length)));
        if (!file) throw new Error(`preload-fonts: no emitted asset matches ${pattern}`);
        return {
          tag: 'link',
          attrs: { rel: 'preload', as: 'font', type: 'font/woff2', href: base + file, crossorigin: '' },
          injectTo: 'head',
        };
      });
    },
  };
}

export default defineConfig({
  plugins: [react(), preloadFonts()],
  build: { target: 'es2022', assetsInlineLimit: 0 },
});
