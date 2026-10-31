/**
 * Facts that don't change between copy variants: links, stacks, dates, the
 * colour and type system. Words live in ./copy/*.js.
 */

export const person = {
  name: 'Remy Post',
  email: 'remy.post.06@gmail.com',
  location: 'Bradford, Ontario',
  github: 'https://github.com/Remy-Post',
  linkedin: 'https://www.linkedin.com/in/remy-post-7b60b8279',
  resumePdf: '/Remy-Post-Resume.pdf',
};

export const edition = { version: '1.0', date: 'October 2026' };

/** The book's chapters, in order. `path` doubles as the route. */
export const chapters = [
  { no: '00', path: '/', title: 'Cover', short: 'Cover' },
  { no: '01', path: '/brand', title: 'The brand', short: 'Brand' },
  { no: '02', path: '/identity', title: 'Identity', short: 'Identity' },
  { no: '03', path: '/work', title: 'Applications', short: 'Work' },
  { no: '04', path: '/history', title: 'History', short: 'History' },
  { no: '05', path: '/writing', title: 'Correspondence', short: 'Writing' },
  { no: '06', path: '/resume', title: 'Credentials', short: 'Resume' },
];

/** Project facts. Text for each slug comes from copy.projects[slug]. */
export const projects = [
  {
    slug: 'course-hub',
    name: 'Course Hub',
    kind: 'Product',
    year: '2026',
    stack: ['Next.js 16', 'React 19', 'n8n', 'Cloudflare Tunnel', 'zod', 'Docker'],
    repo: null,
    plate: { bg: '#1f2a24', fg: '#e9e4d8', mark: 'CH' },
  },
  {
    slug: 'cftdc-sharepoint',
    name: 'CFTDC SharePoint',
    kind: 'Public sector',
    year: '2026',
    stack: ['SharePoint Online', 'Power Automate', 'Power Apps', 'Microsoft Lists'],
    repo: null,
    plate: { bg: '#2c3440', fg: '#e8e6e1', mark: 'IM' },
  },
  {
    slug: 'lawn-guy',
    name: 'The Lawn Guy',
    kind: 'Client',
    year: '2026',
    stack: ['Next.js 15', 'Express 5', 'MongoDB', 'Turborepo', 'Tailwind'],
    repo: 'https://github.com/Remy-Post/grass_v2',
    plate: { bg: '#d9dcc4', fg: '#26301f', mark: 'LG' },
  },
  {
    slug: 'agentui',
    name: 'AgentUI',
    kind: 'Tool',
    year: '2026',
    stack: ['React 19', 'Electron', 'Express 5', 'MongoDB', 'SSE'],
    repo: 'https://github.com/Remy-Post/AgentUI',
    plate: { bg: '#e7e1d6', fg: '#1c1b19', mark: 'A/' },
  },
  {
    slug: 'watch-music',
    name: 'Music for Galaxy Watch',
    kind: 'Product',
    year: '2026',
    stack: ['Kotlin', 'Wear OS', 'Jetpack Compose', 'MediaStore'],
    repo: 'https://github.com/Remy-Post/WatchMusicOS',
    plate: { bg: '#141414', fg: '#f2efe8', mark: '◐' },
  },
  {
    slug: 'restaurant-review',
    name: 'Restaurant Review App',
    kind: 'Coursework',
    year: '2025',
    stack: ['ASP.NET MVC', 'C#', 'EF Core', 'Stripe'],
    repo: 'https://github.com/Remy-Post/Restaurant_Review_App',
    plate: { bg: '#efe2cf', fg: '#3b2a1c', mark: '★' },
  },
  {
    slug: 'meals-app',
    name: 'Meals App',
    kind: 'Coursework',
    year: '2025',
    stack: ['React 19', 'Vite', 'GitHub Pages'],
    repo: 'https://github.com/Remy-Post/Meals-App',
    plate: { bg: '#e9d9c9', fg: '#40261a', mark: 'M' },
  },
];

/** The colour system ("Clay & Ink"). Values mirror styles/tokens.css; `why` is in copy. */
export const palette = [
  { key: 'ink', name: 'Ink', hex: '#211D18', dark: '#F3ECE0', role: 'Text, rules, the wordmark', contrast: '14.9 : 1' },
  { key: 'bone', name: 'Bone', hex: '#F6F1E7', dark: '#17140F', role: 'Paper. Every page sits on it', contrast: 'Ground' },
  { key: 'stone', name: 'Stone', hex: '#6B6355', dark: '#B6AC9A', role: 'Second voice: captions, meta', contrast: '5.3 : 1' },
  { key: 'clay', name: 'Clay', hex: '#A8441F', dark: '#E07A52', role: 'The one accent. Used rarely', contrast: '5.3 : 1' },
  { key: 'pine', name: 'Pine', hex: '#2E4034', dark: '#6FA383', role: 'Depth: plates, quiet emphasis', contrast: '9.8 : 1' },
];

export const typefaces = [
  { name: 'Archivo', role: 'Brand & display', family: 'var(--f-brand)', axes: 'Width 62–125 · Weight 100–900', sample: 'Rr' },
  { name: 'Newsreader', role: 'Voice & long reading', family: 'var(--f-voice)', axes: 'Optical size 6–72 · Weight 200–800', sample: 'Rr' },
  { name: 'Fragment Mono', role: 'Specs & labels', family: 'var(--f-mono)', axes: 'Regular · Italic', sample: 'Rr' },
];

export const skills = [
  ['Languages', 'TypeScript, JavaScript, Java, C#, C++, Kotlin, PHP, SQL'],
  ['Front end', 'React 19, Next.js, Vite, Tailwind, React Native, Jetpack Compose'],
  ['Back end', 'Node, Express, ASP.NET MVC, Entity Framework, MongoDB, PostgreSQL'],
  ['Automation', 'n8n, Power Automate, Power Apps, SharePoint Online, Claude Agent SDK'],
  ['Ops', 'Docker, Caddy, Nginx, Cloudflare Tunnel, Oracle Cloud, Linux, Git'],
];

export const education = [
  {
    org: 'Lakehead University – Georgian College',
    role: 'Honours BSc Computer Science + Computer Programmer diploma, concurrent',
    when: 'Sep 2024 – present',
  },
  {
    org: 'École secondaire catholique Renaissance, Aurora',
    role: 'OSSD, French curriculum · SHSM Health & Wellness',
    when: '2020 – 2024',
  },
];

export const jobs = [
  { key: 'dnd', org: 'Department of National Defence, CFB Borden', role: 'IT Co-op Student & Temporary Unit IMO', when: 'Jun – Aug 2026' },
  { key: 'camp', org: 'Town of Bradford West Gwillimbury', role: 'Camp Counsellor', when: 'Summers 2023 – 2025' },
  { key: 'foodbasics', org: 'Food Basics, Bradford', role: 'Meat Associate', when: 'Jan – May 2023' },
];
