/**
 * Everything the site says, in one place: who Remy is, education, work, the nine projects, the intro and the links.
 * The case studies' longer text (problem, what I did, how it turned out) is in cases.js, which only that page loads.
 * `object` is the name of the project's 3D object (and of its still, assets/objects/<object>.webp); `hint` says what
 * the visitor can do to it.
 */

export const person = {
  name: 'Remy Post',
  email: 'remy.post.06@gmail.com',
  location: 'Bradford, Ontario',
  github: 'https://github.com/Remy-Post',
  linkedin: 'https://www.linkedin.com/in/remy-post-7b60b8279',
  resumePdf: '/Remy-Post-Resume.pdf',
};

export const intro = {
  lead: 'Developer and third-year computer science student in Bradford, Ontario. I build web apps, a watch app and the automation that runs my week.',
  availability: 'Open to co-op and junior developer roles.',
  hint: 'Scroll to look around.',
};

/**
 * Education, in reading order. `pennant` names the school pennant that comes forward while the step is read
 * (three/stations/education.js); the last step has none.
 */
export const education = [
  {
    key: 'lakehead',
    pennant: 'lakehead',
    school: 'Lakehead University',
    when: 'September 2024 to present',
    text: 'Honours BSc in Computer Science, taken at the same time as the Computer Programmer diploma at Georgian College.',
  },
  {
    key: 'georgian',
    pennant: 'georgian',
    school: 'Georgian College',
    when: 'September 2024 to present',
    text: 'Computer Programmer diploma, concurrent with the Honours BSc at Lakehead University.',
  },
  {
    key: 'renaissance',
    pennant: null,
    school: 'École secondaire catholique Renaissance, Aurora',
    lang: 'fr',
    when: '2020 to 2024',
    text: 'Ontario Secondary School Diploma in the French curriculum, with a Specialist High Skills Major in Health and Wellness.',
  },
];

/**
 * Work, newest first. Each point lists the patches (three/stations/experience.js, node `patch_<id>`) that pin onto
 * the sash while the job is in front; hovering a patch or its point lights the other.
 */
export const jobs = [
  {
    key: 'dnd',
    badge: 'dnd',
    org: 'Department of National Defence, CFB Borden',
    role: 'IT co-op student and Temporary Unit Information Management Officer',
    when: 'June to August 2026',
    remark: 'A co-op student trusted with the unit’s information management.',
    points: [
      { text: 'Led the SharePoint modernization for 75+ staff across nearly ten departments as Temporary Unit IMO.', patches: ['sharepoint'] },
      { text: 'Ran recurring requirements meetings with each department and turned them into redesigned pages and libraries.', patches: ['requirements'] },
      { text: 'Implemented a Protection B folder architecture and set page- and folder-level permissions to DND standards.', patches: ['permissions'] },
      { text: 'Built a Power BI classroom-utilization report and a Power Apps showcase for the learning support centre.', patches: ['powerbi', 'powerapps'] },
      { text: 'Replaced a recurring manual process with a Power Automate flow, and wrote the SOPs staff now follow.', patches: ['automate', 'sops'] },
    ],
  },
  {
    key: 'camp',
    badge: 'camp',
    org: 'Town of Bradford West Gwillimbury',
    role: 'Camp counsellor',
    when: 'Summers 2023 to 2025',
    remark: 'Three summers of plans meeting reality in ninety seconds.',
    points: [
      { text: 'Designed and ran daily activities for groups of 30+ campers aged 4 to 8.', patches: ['camp_2023', 'camp_2024', 'camp_2025'] },
      { text: 'Mediated conflicts and gave parents clear daily updates, in English or French.', patches: [] },
      { text: 'Certified in Standard First Aid and CPR Level C.', patches: ['firstaid'] },
    ],
  },
  {
    key: 'foodbasics',
    badge: 'food',
    org: 'Food Basics, Bradford',
    role: 'Meat associate',
    when: 'January to June 2023',
    remark: 'Supply and demand, observed at close range.',
    points: [{ text: 'Served customers and kept the counter moving through peak hours.', patches: ['counter'] }],
  },
];

export const skills = [
  ['Languages', 'TypeScript, JavaScript, Java, C#, C++, Kotlin, PHP, SQL'],
  ['Front end', 'React 19, Next.js, Vite, Tailwind, React Native, Jetpack Compose'],
  ['Back end', 'Node, Express, ASP.NET MVC, Entity Framework, MongoDB, PostgreSQL'],
  ['Automation', 'n8n, Power Automate, Power Apps, SharePoint Online, Claude Agent SDK'],
  ['Ops', 'Docker, Caddy, Nginx, Cloudflare Tunnel, Oracle Cloud, Linux, Git'],
];

/**
 * Important links. Each is a real link in the text column and, when the model has a node `key_<key>`, a keycap on the
 * stage. The list may grow: a link without a keycap is still listed.
 */
export const links = [
  { key: 'email', label: 'Email', detail: person.email, href: `mailto:${person.email}` },
  { key: 'resume', label: 'Résumé', detail: 'PDF', href: person.resumePdf, download: true },
  { key: 'github', label: 'GitHub', detail: 'Remy-Post', href: person.github },
  { key: 'linkedin', label: 'LinkedIn', detail: 'remy-post', href: person.linkedin },
  { key: 'tokens', label: 'Tokens', detail: 'tokens.remypost.me', href: 'https://tokens.remypost.me' },
  { key: 'specs', label: 'Specs', detail: 'specs.remypost.me', href: 'https://specs.remypost.me' },
  { key: 'aa', label: 'AA', detail: 'aa.remypost.me', href: 'https://aa.remypost.me' },
  { key: 'earnings', label: 'Earnings', detail: 'earnings.remypost.me', href: 'https://earnings.remypost.me' },
];

/** In the order they appear on the page and in the index. */
export const projects = [
  {
    slug: 'course-hub',
    name: 'Course Hub',
    short: 'Course Hub',
    kind: 'Product',
    year: '2026',
    stack: ['Next.js 16', 'React 19', 'n8n', 'Cloudflare Tunnel', 'zod', 'Docker'],
    repo: null,
    status: null,
    object: 'planner',
    hint: 'Click or tap to tear off the top page.',
    remark: 'A study planner that reads my syllabi, plans my week and puts it on my calendar.',
  },
  {
    slug: 'cftdc-sharepoint',
    name: 'CFTDC SharePoint',
    short: 'CFTDC SharePoint',
    kind: 'Public sector',
    year: '2026',
    stack: ['SharePoint Online', 'Power Automate', 'Power Apps', 'Microsoft Lists'],
    repo: null,
    status: null,
    object: 'filebox',
    hint: 'Hover a folder, click to pull the document up.',
    remark: 'Rebuilt the intranet for a 75-person Canadian Forces training unit — as a co-op student.',
  },
  {
    slug: 'grocery-brand',
    name: 'Untitled grocery app',
    short: 'Grocery app',
    kind: 'Brand strategy',
    year: '2026',
    stack: ['Positioning', 'Pricing tiers', 'Brand core', 'Market research'],
    repo: null,
    status: 'In progress',
    object: 'pricetag',
    hint: 'Drag the tag to rock it in its holder.',
    remark: 'A grocery-savings app I branded before writing a line of it.',
  },
  {
    slug: 'stem-marketplace',
    name: 'STEM Centre Marketplace',
    short: 'STEM Centre Marketplace',
    kind: 'Team',
    year: '2026',
    stack: ['Web app', 'Requirements', 'Team of five', 'COMP 3415'],
    repo: null,
    status: 'In progress',
    object: 'textbooks',
    hint: 'Drag to slosh the flask, click to nudge the top book.',
    remark: 'A course-materials marketplace for Lakehead’s STEM Centre, built by a team of five.',
  },
  {
    slug: 'lawn-guy',
    name: 'The Lawn Guy',
    short: 'The Lawn Guy',
    kind: 'Client',
    year: '2026',
    stack: ['Next.js 15', 'Express 5', 'MongoDB', 'Turborepo', 'Tailwind'],
    repo: 'https://github.com/Remy-Post/grass_v2',
    status: null,
    object: 'yardsign',
    hint: 'Brush the grass, flick the sign.',
    remark: 'A real website for a real Bradford lawn-care business, deployment scripts included.',
  },
  {
    slug: 'agentui',
    name: 'AgentUI',
    short: 'AgentUI',
    kind: 'Tool',
    year: '2026',
    stack: ['React 19', 'Electron', 'Express 5', 'MongoDB', 'SSE'],
    repo: 'https://github.com/Remy-Post/AgentUI',
    status: null,
    object: 'window',
    hint: 'Click or tap to send the next message.',
    remark: 'My own desktop client for Claude agents, before I knew I wanted one.',
  },
  {
    slug: 'watch-music',
    name: 'Music for Galaxy Watch',
    short: 'Music for Galaxy Watch',
    kind: 'Product',
    year: '2026',
    stack: ['Kotlin', 'Wear OS', 'Jetpack Compose', 'MediaStore'],
    repo: 'https://github.com/Remy-Post/WatchMusicOS',
    status: null,
    object: 'watch',
    hint: 'Click or tap the screen to play and pause.',
    remark: 'A Wear OS music player with no phone, no cloud and no network permission.',
  },
  {
    slug: 'restaurant-review',
    name: 'Restaurant Review App',
    short: 'Restaurant Review App',
    kind: 'Coursework',
    year: '2025',
    stack: ['ASP.NET MVC', 'C#', 'EF Core', 'Stripe'],
    repo: 'https://github.com/Remy-Post/Restaurant_Review_App',
    status: null,
    object: 'cloche',
    hint: 'Click or tap to lift the dome.',
    remark: 'Ratings, roles and a working Stripe checkout in ASP.NET MVC.',
  },
  {
    slug: 'meals-app',
    name: 'Meals App',
    short: 'Meals App',
    kind: 'Coursework',
    year: '2025',
    stack: ['React 19', 'Vite', 'GitHub Pages'],
    repo: 'https://github.com/Remy-Post/Meals-App',
    status: null,
    object: 'takeout',
    hint: 'Click or tap to lift the chopsticks.',
    remark: 'A meal-ordering interface in React 19, shipped straight to GitHub Pages.',
  },
];

/** The project with this slug, or undefined. */
export const projectBySlug = (slug) => projects.find((p) => p.slug === slug);
