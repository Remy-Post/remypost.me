import { useEffect } from 'react';

const ORIGIN = 'https://remypost.me';

/**
 * Point the page's canonical link and `og:url` at this route's own address (index.html carries the home page's), and back
 * to the home page's when the route goes. They are tags that already exist in the document, so there is only ever one of each.
 */
export function useCanonical(path) {
  useEffect(() => {
    const link = document.querySelector('link[rel="canonical"]');
    const og = document.querySelector('meta[property="og:url"]');
    const url = ORIGIN + path;
    link?.setAttribute('href', url);
    og?.setAttribute('content', url);
    return () => {
      link?.setAttribute('href', `${ORIGIN}/`);
      og?.setAttribute('content', `${ORIGIN}/`);
    };
  }, [path]);
}
