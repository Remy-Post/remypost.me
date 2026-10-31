/**
 * DRAFT COPY — development stage.
 *
 * This file is the template. Every string is a placeholder that says what goes
 * there and roughly how long it should be. Replace them with your own words
 * (or copy researched.js and edit it), and the layout won't need to change.
 * Keys must match researched.js exactly.
 */

const ph = (label, words, hint) => `[${label} · ~${words} words] ${hint}`;

const project = (name) => ({
  remark: ph(`${name} — the remark`, 15, 'The one sentence you want repeated about this project.'),
  problem: ph('Problem', 30, 'What was broken, slow or missing, and for whom.'),
  role: ph('Role', 25, 'What you personally designed, built or decided.'),
  outcome: ph('Outcome', 30, 'What changed because it exists. A number if you have one.'),
});

export default {
  id: 'draft',
  label: 'Draft copy',

  tagline: '[Tagline · 6–8 words]',
  positioning: ph('Positioning', 25, 'Who you are, who you build for, and what makes your work different from a very good developer.'),
  intro: ph('Intro', 45, 'Two or three sentences in your own voice. Where you study, what you just did, what you build when nobody asks.'),
  availability: '[Availability · e.g. “Open to co-op and junior roles from May 2027.”]',

  brandIntro: ph('Chapter intro', 30, 'Why a developer would bother writing brand guidelines for himself.'),
  mission: ph('Mission', 35, 'Why you build. What you want the people who use your work to feel.'),
  principle: {
    title: '[Principle · 4–6 words]',
    body: ph('Principle', 50, 'The idea behind the brand: being worth a remark beats being very good.'),
  },
  values: [
    { name: '[Value 1]', line: ph('Value', 14, 'One line on how this shows up in your work.') },
    { name: '[Value 2]', line: ph('Value', 14, 'One line on how this shows up in your work.') },
    { name: '[Value 3]', line: ph('Value', 14, 'One line on how this shows up in your work.') },
  ],

  identityIntro: ph('Chapter intro', 25, 'What the identity is made of, and the rule that holds it together.'),
  logoNote: ph('Wordmark note', 35, 'Why the mark looks the way it does.'),
  typeWhy: {
    Archivo: ph('Why this typeface', 18, 'What it does for the brand.'),
    Newsreader: ph('Why this typeface', 18, 'What it does for the brand.'),
    'Fragment Mono': ph('Why this typeface', 18, 'What it does for the brand.'),
  },
  colourIntro: ph('Colour intro', 30, 'The principle behind the palette.'),
  colourWhy: {
    ink: ph('Why Ink', 18, 'The psychology behind it.'),
    bone: ph('Why Bone', 18, 'The psychology behind it.'),
    stone: ph('Why Stone', 18, 'The psychology behind it.'),
    clay: ph('Why Clay', 18, 'The psychology behind it.'),
    pine: ph('Why Pine', 18, 'The psychology behind it.'),
  },
  voice: [
    { say: '[I say · example sentence]', dont: '[I don’t say · the cliché version]' },
    { say: '[I say · example sentence]', dont: '[I don’t say · the cliché version]' },
    { say: '[I say · example sentence]', dont: '[I don’t say · the cliché version]' },
  ],

  workIntro: ph('Chapter intro', 30, 'How to read the projects: each one is an application of the brand.'),
  projects: {
    'course-hub': project('Course Hub'),
    'cftdc-sharepoint': project('CFTDC SharePoint'),
    'lawn-guy': project('The Lawn Guy'),
    agentui: project('AgentUI'),
    'watch-music': project('Music for Galaxy Watch'),
    'restaurant-review': project('Restaurant Review App'),
    'meals-app': project('Meals App'),
  },

  historyIntro: ph('Chapter intro', 30, 'The through-line of your story in one breath.'),
  timeline: [
    { year: '2020', place: '[Place]', title: '[Milestone · ~6 words]', blurb: ph('Blurb', 30, 'What happened and what it gave you.') },
    { year: '2023', place: '[Place]', title: '[Milestone · ~6 words]', blurb: ph('Blurb', 30, 'What happened and what it gave you.') },
    { year: '2024', place: '[Place]', title: '[Milestone · ~6 words]', blurb: ph('Blurb', 30, 'What happened and what it gave you.') },
    { year: '2026', place: '[Place]', title: '[Milestone · ~6 words]', blurb: ph('Blurb', 30, 'What happened and what it gave you.') },
    { year: 'Now', place: '[Place]', title: '[Milestone · ~6 words]', blurb: ph('Blurb', 30, 'What you are doing now.') },
  ],

  experience: {
    dnd: { remark: ph('Remark', 12, 'One line worth repeating.'), points: [ph('Achievement', 20, 'Verb first. Specific.'), ph('Achievement', 20, 'Verb first. Specific.'), ph('Achievement', 20, 'Verb first. Specific.')] },
    camp: { remark: ph('Remark', 12, 'One line worth repeating.'), points: [ph('Achievement', 20, 'Verb first. Specific.'), ph('Achievement', 20, 'Verb first. Specific.')] },
    foodbasics: { remark: ph('Remark', 12, 'One line worth repeating.'), points: [ph('Achievement', 20, 'Verb first. Specific.')] },
  },

  writingIntro: ph('Chapter intro', 20, 'What you write about and why.'),
  letters: [
    {
      slug: 'draft-letter',
      no: '001',
      date: '2026-10-31',
      title: '[Letter title · ~6 words]',
      dek: ph('Dek', 15, 'The one-line summary under the title.'),
      read: '3 min',
      body: [
        ph('Opening', 50, 'Start with a specific moment, not a thesis.'),
        { h: '[Subheading]' },
        ph('Paragraph', 70, 'What you did and what surprised you.'),
        { q: '[Pull quote · your own sentence, ~12 words]' },
        ph('Closing', 50, 'What you would tell someone about to try the same thing.'),
      ],
    },
  ],

  funFacts: ['[Fun fact 1 · true and specific]', '[Fun fact 2]', '[Fun fact 3]'],
  contactCta: ph('Contact line', 15, 'One sentence that makes it easy to reach out.'),
};
