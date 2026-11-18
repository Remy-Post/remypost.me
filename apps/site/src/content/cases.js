/**
 * The longer text of each case study, by project slug. Only the case-study page loads this file.
 */
export const cases = {
  'course-hub': {
    problem:
      'Five courses means five syllabi, dozens of deadlines and weights that change after week one. Keeping a planner honest by hand never lasted past October.',
    did:
      'Designed and built all of it: n8n workflows and a local model on my Mac, a Next.js 16 front end on an Oracle VM, and a Cloudflare tunnel with a service token between them.',
    result:
      'A 6 AM plan every day, a 30-second evening check-in, and a “check my facts” flow that asks me to confirm each weight against the syllabus line it came from.',
  },
  'cftdc-sharepoint': {
    problem:
      'Nearly ten departments shared one SharePoint site nobody loved: documents were hard to find, access didn’t match who needed what, and some weekly tasks were still manual.',
    did:
      'As Temporary Unit Information Management Officer I ran requirements meetings with every department, redesigned pages and libraries, and set permissions to DND information-management standards.',
    result:
      'A restructured site with a Protection B folder architecture, a Power Automate flow that retired a manual process, a Power BI classroom-utilization report, a Power Apps showcase for the learning support centre, and SOPs the staff adopted. 397.5 hours, start to finish.',
  },
  'grocery-brand': {
    problem:
      'Flyer deals and coupons are scattered across stores and apps; students and families overpay because finding the best price takes too long.',
    did:
      'Drafted the brand core with two collaborators — purpose, audience, positioning, promise, personality, palette — and a three-tier pricing model with a student discount.',
    result:
      'Still building, and still unnamed. The strategy came first on purpose: it decides what the product is allowed to be.',
  },
  'stem-marketplace': {
    problem:
      'Students buy and sell textbooks and lab gear through scattered group chats with no trust or structure.',
    did:
      'Front-end developer on account registration and listing creation, inside a full requirements-and-planning process for COMP 3415.',
    result:
      'In progress this term — requirements and plan delivered, build underway.',
  },
  'lawn-guy': {
    problem:
      'A local service business needed a site that looked established and could capture and track leads without a monthly SaaS bill.',
    did:
      'Built a Next.js storefront and Express API in a Turborepo monorepo, driven by one brand configuration, with an admin panel for content and leads.',
    result:
      'A production setup with systemd units, Nginx, SSL and backups — the brand lives in one file, so a reskin is a config change.',
  },
  'agentui': {
    problem:
      'Working with agents in a terminal is powerful but hard to review; I wanted conversations I could keep, search and share.',
    did:
      'Built an Electron app and a browser app over one Express backend, streaming agent turns over server-sent events into MongoDB.',
    result:
      'A local-first client where API keys stay in the OS keychain and every agent run is a conversation I can return to.',
  },
  'watch-music': {
    problem:
      'I wanted music on my watch on a run without carrying a phone or trusting an app with the network.',
    did:
      'Wrote it in Kotlin and Compose for a 480 × 480 Galaxy Watch8: library, podcasts, favourites and gestures along the screen edges.',
    result:
      'Album art blurred behind the player sets the accent colour, podcasts resume where they stopped, and it never asks for the internet.',
  },
  'restaurant-review': {
    problem:
      'Coursework brief: a catalogue people can review, with real authentication and a payment flow.',
    did:
      'Built the MVC app, role-based auth, Entity Framework data layer and the Stripe integration.',
    result:
      'Users browse, rate and review; admins manage; payments go through Stripe’s test gateway end to end.',
  },
  'meals-app': {
    problem:
      'Learning React properly meant building something with real state, not another to-do list.',
    did:
      'Built the UI with hooks and context while working through a long React course, and set up the deploy.',
    result:
      'A small, fast ordering flow and the habit of shipping every project to a public URL.',
  },
};
