/**
 * RESEARCHED COPY — assembled from Remy's resume, GitHub repos, coursework and
 * Google Drive career files. Same keys as draft.js. Lines that rest on
 * interpretation rather than a document are fair game for Remy to rewrite.
 */

export default {
  id: 'researched',
  label: 'Researched copy',

  tagline: 'Developer with a brand brain.',
  positioning:
    'A computer science student who builds software the way a brand is built: one clear idea, said plainly, made to be remembered.',
  intro:
    'I’m in third year of a concurrent CS degree and programming diploma in Ontario. This summer I ran information management for a Canadian Forces training unit of 75+ people as a co-op student. The rest of the time I build the tools I want to exist.',
  availability: 'Open to co-op and junior developer roles.',

  brandIntro:
    'Most student portfolios are very good, and very good is invisible. So I treated mine like a brand: a point of view, a small system, and rules I actually follow.',
  mission:
    'I build software that people can explain to someone else in one sentence. If a user can’t say what it does, I haven’t finished designing it.',
  principle: {
    title: 'Worth a remark.',
    body:
      'Seth Godin’s old TED talk argues that people ignore what is merely good and pass on what is remarkable — literally, worth making a remark about. Every project here carries one line written to be repeated. If you only remember one sentence about me, I want to choose it.',
  },
  values: [
    { name: 'Plain', line: 'If it needs a paragraph to explain, the design isn’t done.' },
    { name: 'Specific', line: '75 people and ten departments, not “various stakeholders.”' },
    { name: 'Owned', line: 'I ship it, document it, and stay for the second meeting.' },
  ],

  identityIntro:
    'Four colours, three typefaces, one rule: the work is loud, the system is quiet.',
  logoNote:
    'The wordmark is set in Archivo at its widest, so the name reads like a sign rather than a signature. The monogram stacks R over P inside a square — the smallest version of the brand that still says who it is.',
  typeWhy: {
    Archivo: 'A grotesque with a width axis: wide for the name, narrow for labels. One family, many voices.',
    Newsreader: 'Built for reading on screens. It carries the voice: letters, quotes, anything meant to be read slowly.',
    'Fragment Mono': 'Specs, dates and labels. It makes the book feel engineered without shouting about it.',
  },
  colourIntro:
    'The research on colour is weaker than the internet suggests — “blue means trust” rests on a handful of studies. What holds up better: lightness and saturation shape impressions more than hue, muted and darker tones read as sophisticated, and a colour has to fit the job. So the palette is quiet, warm and deliberately not the indigo every developer template ships with.',
  colourWhy: {
    ink: 'Warm near-black, not #000. Reads as print, which reads as care, and stays easy on the eye.',
    bone: 'A warm off-white. Pure white feels clinical; bone feels like paper someone chose.',
    stone: 'A warm grey for the second voice. Quiet enough that the hierarchy is never in doubt.',
    clay: 'Warmth next to competence: one human, earthy accent, rare enough that it always means “look here.”',
    pine: 'Dark, desaturated green for depth. Low saturation reads as established rather than trendy.',
  },
  voice: [
    { say: 'I rebuilt the intranet for a 75-person unit.', dont: 'I leveraged SharePoint to drive digital transformation.' },
    { say: 'It plans my study week and puts it on my calendar.', dont: 'An AI-powered productivity solution.' },
    { say: 'I don’t know yet. I’ll find out by Friday.', dont: 'Great question! Let me circle back.' },
  ],

  workIntro:
    'Each project is an application of the brand: one problem, one line worth repeating, and the decisions I made along the way.',
  projects: {
    'course-hub': {
      remark: 'A study planner that reads my syllabi, plans my week and puts it on my calendar.',
      problem:
        'Five courses means five syllabi, dozens of deadlines and weights that change after week one. Keeping a planner honest by hand never lasted past October.',
      role:
        'Designed and built all of it: n8n workflows and a local model on my Mac, a Next.js 16 front end on an Oracle VM, and a Cloudflare tunnel with a service token between them.',
      outcome:
        'A 6 AM plan every day, a 30-second evening check-in, and a “check my facts” flow that asks me to confirm each weight against the syllabus line it came from.',
    },
    'cftdc-sharepoint': {
      remark: 'Rebuilt the intranet for a 75-person Canadian Forces training unit — as a co-op student.',
      problem:
        'Nearly ten departments shared one SharePoint site nobody loved: documents were hard to find, access didn’t match who needed what, and some weekly tasks were still manual.',
      role:
        'As Temporary Unit Information Management Officer I ran requirements meetings with every department, redesigned pages and libraries, and set permissions to DND information-management standards.',
      outcome:
        'A restructured site with a Protection B folder architecture, a Power Automate flow that retired a manual process, a Power BI classroom-utilization report, a Power Apps showcase for the learning support centre, and SOPs the staff adopted. 397.5 hours, start to finish.',
    },
    'grocery-brand': {
      remark: 'A grocery-savings app I branded before writing a line of it.',
      problem: 'Flyer deals and coupons are scattered across stores and apps; students and families overpay because finding the best price takes too long.',
      role: 'Drafted the brand core with two collaborators — purpose, audience, positioning, promise, personality, palette — and a three-tier pricing model with a student discount.',
      outcome: 'Still building, and still unnamed. The strategy came first on purpose: it decides what the product is allowed to be.',
    },
    'stem-marketplace': {
      remark: 'A course-materials marketplace for Lakehead’s STEM Centre, built by a team of five.',
      problem: 'Students buy and sell textbooks and lab gear through scattered group chats with no trust or structure.',
      role: 'Front-end developer on account registration and listing creation, inside a full requirements-and-planning process for COMP 3415.',
      outcome: 'In progress this term — requirements and plan delivered, build underway.',
    },
    'lawn-guy': {
      remark: 'A real website for a real Bradford lawn-care business, deployment scripts included.',
      problem: 'A local service business needed a site that looked established and could capture and track leads without a monthly SaaS bill.',
      role: 'Built a Next.js storefront and Express API in a Turborepo monorepo, driven by one brand configuration, with an admin panel for content and leads.',
      outcome: 'A production setup with systemd units, Nginx, SSL and backups — the brand lives in one file, so a reskin is a config change.',
    },
    agentui: {
      remark: 'My own desktop client for Claude agents, before I knew I wanted one.',
      problem: 'Working with agents in a terminal is powerful but hard to review; I wanted conversations I could keep, search and share.',
      role: 'Built an Electron app and a browser app over one Express backend, streaming agent turns over server-sent events into MongoDB.',
      outcome: 'A local-first client where API keys stay in the OS keychain and every agent run is a conversation I can return to.',
    },
    'watch-music': {
      remark: 'A Wear OS music player with no phone, no cloud and no network permission.',
      problem: 'I wanted music on my watch on a run without carrying a phone or trusting an app with the network.',
      role: 'Wrote it in Kotlin and Compose for a 480 × 480 Galaxy Watch8: library, podcasts, favourites and gestures along the screen edges.',
      outcome: 'Album art blurred behind the player sets the accent colour, podcasts resume where they stopped, and it never asks for the internet.',
    },
    'restaurant-review': {
      remark: 'Ratings, roles and a working Stripe checkout in ASP.NET MVC.',
      problem: 'Coursework brief: a catalogue people can review, with real authentication and a payment flow.',
      role: 'Built the MVC app, role-based auth, Entity Framework data layer and the Stripe integration.',
      outcome: 'Users browse, rate and review; admins manage; payments go through Stripe’s test gateway end to end.',
    },
    'meals-app': {
      remark: 'A meal-ordering interface in React 19, shipped straight to GitHub Pages.',
      problem: 'Learning React properly meant building something with real state, not another to-do list.',
      role: 'Built the UI with hooks and context while working through a long React course, and set up the deploy.',
      outcome: 'A small, fast ordering flow and the habit of shipping every project to a public URL.',
    },
  },

  historyIntro:
    'None of my stops pointed straight at software. Each one cost something and bought something — the only economics I really need.',
  timeline: [
    {
      year: '2020',
      place: 'Bradford',
      title: 'The Snow Guy.',
      blurb: 'My first brand: a neighbourhood snow-shovelling flyer with tiered pricing and a neighbour discount. The naming pattern came back six years later as The Lawn Guy.',
    },
    {
      year: '2020',
      place: 'Aurora',
      title: 'Four years of high school, in French.',
      blurb: 'A French-curriculum school, a Specialist High Skills Major in Health & Wellness, and a francophone summer program in Moncton in 2022.',
    },
    {
      year: '2023',
      place: 'Bradford',
      title: 'The meat counter.',
      blurb: 'January to June at Food Basics. Supply and demand in real time: what’s full at four, gone by six, and who comes back asking.',
    },
    {
      year: '2023',
      place: 'Bradford',
      title: 'Thirty kids at a time.',
      blurb: 'Hired at sixteen by the same town camp I went to as a kid. Three summers with groups of 30+ kids aged four to eight; every plan meets reality in ninety seconds.',
    },
    {
      year: '2024',
      place: 'Barrie',
      title: 'Two programs on one clock.',
      blurb: 'The concurrent BSc in Computer Science and Computer Programmer diploma began, and I served as VP Communications on the residence council.',
    },
    {
      year: '2026',
      place: 'Barrie',
      title: 'A hackathon, from the other side.',
      blurb: 'Volunteered at Honda’s AUTOHACK 2.0 at Georgian College in March.',
    },
    {
      year: '2026',
      place: 'CFB Borden',
      title: 'A co-op with an officer’s job title.',
      blurb: 'Temporary Unit Information Management Officer for the Canadian Forces Training Development Centre, with Reliability Status clearance. My supervisor’s evaluation called me a strong candidate for future employment.',
    },
    {
      year: 'Now',
      place: 'Bradford',
      title: 'Third year, building in public.',
      blurb: 'A five-person software engineering team project, microeconomics, and a grocery-app brand on the side — plus Course Hub, a watch app and this brand book.',
    },
  ],

  experience: {
    dnd: {
      remark: 'A co-op student trusted with the unit’s information management.',
      points: [
        'Led the SharePoint modernization for 75+ staff across nearly ten departments as Temporary Unit IMO.',
        'Ran recurring requirements meetings with each department and turned them into redesigned pages and libraries.',
        'Implemented a Protection B folder architecture and set page- and folder-level permissions to DND standards.',
        'Built a Power BI classroom-utilization report and a Power Apps showcase for the learning support centre.',
        'Replaced a recurring manual process with a Power Automate flow, and wrote the SOPs staff now follow.',
      ],
    },
    camp: {
      remark: 'Three summers of plans meeting reality in ninety seconds.',
      points: ['Designed and ran daily activities for groups of 30+ campers aged 4 to 8.', 'Mediated conflicts and gave parents clear daily updates, in English or French.', 'Certified in Standard First Aid and CPR Level C.'],
    },
    foodbasics: {
      remark: 'Supply and demand, observed at close range.',
      points: ['Served customers and kept the counter moving through peak hours.'],
    },
  },

  writingIntro: 'Short letters, written when something I built taught me something worth keeping.',
  letters: [
    {
      slug: 'why-a-brand-book',
      no: '004',
      date: '2026-10-31',
      title: 'Why my portfolio is a brand book',
      dek: 'On being worth a remark, and writing for an audience of two.',
      read: '3 min',
      body: [
        'I expect about two recruiters to read this site. That number is the whole design brief.',
        'In a 2003 TED talk, Seth Godin describes driving past cows: you’ve seen a thousand, so you don’t see this one. A purple one, you’d pull over for. His point is that remarkable literally means worth making a remark about, and that when people have too many choices and too little time, they ignore what is merely good.',
        { h: 'Very good is the trap' },
        'A student portfolio is the most crowded category there is. Dark mode, a gradient, a grid of cards, “passionate full-stack developer.” I’ve built four of them. Each one was fine. None was something you’d mention to a colleague.',
        'Godin also argues you should stop aiming at the middle and talk to the few people who care. For a portfolio, that’s the one or two people who opened the link on purpose. Everything here is written for them.',
        { q: 'If you only remember one sentence about me, I want to choose it.' },
        { h: 'Why a brand book' },
        'Because the thing I want to show isn’t a list of frameworks. It’s judgment: choosing a typeface for a reason, a colour from evidence, a voice and the rules to keep it. A brand book is where designers show their reasoning. So this is mine, with my projects as the applications.',
      ],
    },
    {
      slug: 'fifty-people-one-sharepoint',
      no: '003',
      date: '2026-09-12',
      title: 'Seventy-five people, ten departments, one SharePoint',
      dek: 'What a summer as a temporary IMO taught me about the meeting before the code.',
      read: '4 min',
      body: [
        'For most of this summer I held the title Temporary Unit Information Management Officer for the Canadian Forces Training Development Centre at CFB Borden. In practice it meant one thing: the unit’s SharePoint site was mine to fix.',
        { h: 'Nobody asks for a new intranet' },
        'People don’t ask for a new SharePoint. They ask why they can’t find last year’s form, or why another department can see a folder it shouldn’t. The site is just where those complaints live.',
        'So I started with a meeting per department, and kept having them. The first meeting is a list of features. The second, once people see a rough page, is where the real requirements appear: who owns this document, who approves it, who only needs to read it.',
        { q: 'The hard part of software is the meeting before it.' },
        { h: 'Permissions are the product' },
        'The redesign people noticed was the pages. The work that mattered more was permissions, structured by department to DND standards. Good permissions are invisible; bad ones are a security problem or a support ticket.',
        { h: 'Automate one boring thing well' },
        'I built one Power Automate flow to replace a recurring manual task. One flow that removes steps people do every week beats five clever ones. Then I wrote the guides, because a system nobody can use gets replaced next year.',
      ],
    },
    {
      slug: 'opportunity-cost',
      no: '002',
      date: '2026-10-23',
      title: 'Opportunity cost, applied to me',
      dek: 'A microeconomics midterm question, used on my own career.',
      read: '3 min',
      body: [
        'The first question on my ECON 1010 midterm was a production possibilities frontier: a country making robots and computers, and what each extra ten robots costs. The answer climbs — ten computers, then twenty, thirty, forty — because the resources you move last are the least suited to the new job.',
        { h: 'The cheap robots' },
        'The first things I learned in software were cheap. Explaining things to six-year-olds at camp became writing documentation. Running a counter through a rush became thinking about queues. Those transfers cost almost nothing.',
        'The expensive ones came later. SharePoint permission inheritance didn’t borrow from anything I knew. Every hour came out of something else, usually sleep.',
        { q: 'You don’t get past the frontier by trying harder. You get past it by growing.' },
        { h: 'Moving the curve' },
        'Points outside the curve are unattainable with current resources. The way out is growth: better tools, more people. For one person, that’s automation — and it’s the real reason I want to join a team.',
      ],
    },
    {
      slug: 'moving-my-automations-home',
      no: '001',
      date: '2026-10-31',
      title: 'Moving my automations home',
      dek: 'Why my n8n now runs on a Mac, and only a website is left in the cloud.',
      read: '3 min',
      body: [
        'For most of this year my n8n instance lived on an Oracle Cloud VM. Today it moved to the Mac on my desk, and the VM is down to a web server and a tunnel.',
        { h: 'Why move it' },
        'My automations touch personal data: my calendar, my syllabi, a local model that reads them. Running that on my own machine is easier to reason about than a server I have to keep patched. The trade-off is that a Mac sleeps.',
        { h: 'Designing for a sleeping server' },
        'Course Hub is built around that. The browser never talks to n8n; a small Next.js app does, server-side, through a tunnel that requires a service token, validating every response and trimming it to what the UI needs.',
        { q: 'Design for the server being asleep, and it stops mattering that it sometimes is.' },
        'When the Mac is asleep, the page shows the last good answer with its timestamp instead of an error. That one decision made the whole thing feel reliable.',
      ],
    },
  ],

  endorsement: {
    quote: 'A strong candidate for future employment opportunities.',
    source: 'DND supervisor, co-op evaluation · August 2026',
  },
  funFacts: [
    'Ran a snow-shovelling business with tiered pricing in 2020.',
    'Went to high school entirely in French.',
    'Wrote a music player for his own watch.',
  ],
  contactCta: 'If your team needs someone who sits in the meeting before the code and then writes the code, let’s talk.',
};
