# remypost.me

The portfolio of Remy Post, a computer science student and developer in Ontario. It is one scrolling page with a persistent 3D stage beside the text: as you scroll, the camera moves between four things on a dark studio floor, and each has something to touch. Everything works without WebGL: the text and links are ordinary HTML and the stage shows still images instead. The page is rendered in the browser, so with JavaScript off `index.html` shows a short summary (name, intro, résumé, GitHub, LinkedIn) in a `<noscript>` block.

## Page structure

`/` is one page of five sections, in this order:

| Section | Text column | 3D object (stage) |
| --- | --- | --- |
| `#top` | name, one-line intro, two buttons | all nine project objects on a turntable, seen from above |
| `#education` | three schools | two felt school pennants on a stand (they flutter; drag to swing) |
| `#experience` | three jobs, their points, skills | three ID badges on a lanyard and a sash of merit patches (scrolling brings a job's badge forward and pins its patches) |
| `#projects` | nine projects, one section each | the turntable, one object at the front per project (each has its own small interaction) |
| `#links` | eight links | a keypad; each key is a link, and hovering a link presses its key |

Other routes: `/work/:slug` is a case study with the same object turnable by drag; anything else is the 404. Old routes (`/work`, `/resume`, `/brand`, `/identity`, `/history`, `/writing`) redirect (see `apps/site/src/main.jsx`).

## Stack

- React ^19.3.1 and React Router ^8.5.1, plain JavaScript, plain CSS (`apps/site/src/styles/site.css`). No TypeScript, no UI library.
- Vite ^8.3.5 with `@vitejs/plugin-react` ^6.1.2.
- three ^0.187.0, `postprocessing` ^6.39.6 (bloom, depth of field, SMAA, tone mapping), `lenis` ^1.3.27 (smooth wheel scrolling).
- Instrument Sans (variable, self-hosted via `@fontsource-variable/instrument-sans` ^5.3.0).
- Models are made in Blender 5.2 and compressed with `@gltf-transform/cli` 4 (run through `npx`, not installed).
- CI builds with Node 24 (`.github/workflows/deploy.yml`).

## Run, build, preview

```sh
npm install
npm run dev       # Vite dev server
npm run build     # production build into apps/site/dist
npm run preview   # serve the build
```

The scripts at the root forward to the one workspace, `apps/site`. Adding `?objects=off` to any URL loads that page with the 3D off.

## Layout

```
apps/site/
  index.html              entry; an inline script applies the stored 3D on/off choice before first paint
  public/                 favicon, share image (og.jpg), résumé PDF, robots.txt, privacy and terms pages
  src/
    main.jsx              routes and redirects
    content/site.js       everything the page says: person, education, jobs, skills, projects, links
    content/cases.js      the longer case-study text, loaded only by the case-study page
    pages/                Home, Project (case study), NotFound
    components/           Frame (text + stage), Stage, Bar, ProjectIndex, ScrollManager, Objects (3D switch)
    scene/                three-free scroll signal and shared state (see below)
    three/                the stage; loaded only after first paint
    assets/models/        <object>.glb, one per 3D object
    assets/objects/       <object>.webp stills (and table, education, experience, links)
    assets/env/studio.hdr the studio's reflection map
deploy/                   Caddy config and VM setup script
tools/blender/hd/         Blender scripts that make the models, stills and the studio map
```

## The 3D pipeline

Each model has a script in `tools/blender/hd/` (`planner.py`, `filebox.py`, `pricetag.py`, `textbooks.py`, `yardsign.py`, `window.py`, `watch.py`, `cloche.py`, `takeout.py`, `badge.py`, `patches.py`, `pennants.py`, `keys.py`). They run headless in Blender 5.2 (see `common.py`):

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --python tools/blender/hd/<object>.py -- --render   # a still
/Applications/Blender.app/Contents/MacOS/Blender --background --python tools/blender/hd/<object>.py -- --export   # the web model
```

The flags differ a little per script; the docstring at the top of each lists them. An export bakes procedural materials into textures, writes the raw `.glb` under `tools/blender/out/hd/web/` and compresses it with `gltf-transform optimize` (meshopt geometry, WebP textures) into `apps/site/src/assets/models/<name>.glb`. `studio_env.py` writes `apps/site/src/assets/env/studio.hdr`.

The code finds parts of a model by node name, so the names are the contract (a node that is missing is skipped, not an error):

- Every model: one root node named after the file, in metres, Y up, front toward +Z, base on the floor.
- `planner`: `sheet_top`. `filebox`: `document`, `folder_1` to `folder_7` (and `folder_N_glass`). `pricetag`: `card`, `card_paper`. `textbooks`: `book_3`, `flask`, `liquid`. `yardsign`: `Sign`, `Grass`. `window`: `screen_base`, `bubble_*`, `tool_card`, `caret`, `Mask`. `watch`: `icon_play`, `icon_pause`, `ring_progress` (uv x runs along the arc), `Crystal`, `Button0`. `cloche`: `DomePivot`. `takeout`: `Chopsticks` and a `lifted` morph target on the noodle meshes.
- `pennants`: `pennant_lakehead`, `pennant_georgian`, `stand`; the cloth meshes end in `_cloth` and carry a second UV set (x: 0 at the stick, 1 at the tip).
- `badge`: `badge_dnd`, `badge_camp`, `badge_food`, `clip`, `lanyard` (its strap mesh `lanyard_0` has a second UV set: 0 at the bar, 1 at the clip). `patches`: `sash`, `patch_<id>`.
- `keys`: `key_<key>` (each moves 4 mm along its local -Y when pressed) and `plate`.

The stills in `src/assets/objects/` are screenshots of the live scene at a 1:1 stage; the page shows them while the 3D loads and whenever it is off or unavailable. `tools/blender/README.md` and `optimize.sh` still describe an earlier set of models and are out of date.

## Scroll and stage architecture

`src/scene/progress.js` is the one signal. It has no React and no three.js: `getProgress()` reads where the focus line (the middle of the reading area) is on the page and returns the route, the section, the camera's place along the five-stop path (`p`: intro, education, experience, projects, links), the turntable position (`t`, 1 to 9 as each project is centred), and the position within the current block or bullet. `onProgress(fn)` calls back once per animation frame while the page scrolls or resizes, and does nothing when nobody is subscribed.

`src/three/` is loaded by dynamic `import()` after first paint, and only when hardware WebGL 2 is available, the visitor has not asked to save data, and the 3D switch is on (`live.js`). It makes one canvas and one WebGL context for the whole site, kept across route changes. `stage.js` owns the frame loop. Everything it moves is a critically damped spring chasing a target (`motion.js`; the families of rates are in `RATE`), and it draws only while something is moving: zero frames at rest. `rig.js` holds the camera path: where the camera looks for each place, how it cranes up and back between two places, and which objects are visible. The stations (`stations/education.js`, `experience.js`, `links.js`) and the nine project objects (`objects.js`) each own their own interaction and picking. `post.js` is the image pipeline: a multisampled half-float buffer, bloom (only emissive materials exceed its threshold), tone mapping applied once, a dither, then SMAA. The page text and the stage react to the same signal in the same animation frame.

Memory is kept down by loading only what is near. The page is a line of steps (intro, education, experience, the nine projects, the links); a model is loaded when the visitor is within one step of it and let go of (GPU buffers, textures and decoded images) when they are more than two steps away. The turntable shows all nine objects at the intro, so then each is held small (textures at most 512 px); an object is held at full detail (2048 px) only while it is the front one or its neighbour. A small stage, a phone, or a device reporting 4 GB or less caps these at 384 and 1024 px. Textures are shrunk before they are uploaded (`models.js`), uploads happen a few at a time and only while nothing on screen is moving, and each model is drawn once off screen first so that showing it costs nothing. Switching 3D off frees everything, including the downloaded files. A model that fails to load is tried again after 30 seconds, not in a loop. `live.js` starts stages one after another.

What the page promises follows what is really on the stage, not the switch: hints, the stage's tab stop and name, and the switch's own label (`3D unavailable` when the browser cannot show it) are driven by `isReady()` and `getStatus()` in `live.js`, which the stage updates as models load and go.

## Adding a project

1. Add an entry to `projects` in `apps/site/src/content/site.js` (`slug`, `name`, `short`, `kind`, `year`, `stack`, `repo`, `status`, `object`, `hint`, `remark`) and its text to `cases` in `content/cases.js`, under the same slug.
2. Make the model `assets/models/<object>.glb` and the still `assets/objects/<object>.webp` (see above), and give the object its interaction in `three/objects.js` (a project with no behaviour is still shown and can be turned).
3. The turntable spaces objects evenly by the `COUNT` constant in `three/rig.js`; it is nine now, so a tenth means changing that and the ring arithmetic that depends on it.

A project without a model shows its still.

## Adding a link

Add `{ key, label, detail, href }` to `links` in `content/site.js`. It appears as a link in the text column. If `keys.glb` has a node `key_<key>`, that keycap is wired to it automatically (hover, focus, click and the matching highlight); without the node the link is simply listed.

## The 3D switch and fallbacks

The bar's "3D on / 3D off" button (`aria-pressed`) sets `<html data-objects="off">` and stores the choice in `localStorage` (only while it is off). Off means no canvas and no WebGL context, and the stills are shown. The stills are also what is shown while the stage loads, when WebGL is unavailable or software-only, when the visitor has asked to save data, and while a lost context is being rebuilt. Under `prefers-reduced-motion` the stage jumps to each target and draws once, and smooth scrolling is off. The text and links do not depend on the 3D code: if its files are blocked or fail, the stills stay and nothing is promised that is not there.

## Deployment

Every push to `main` runs `.github/workflows/deploy.yml`: `npm ci`, `npm run build`, then it sends `apps/site/dist` to the VM over SSH (a forced command there unpacks it into a new release and switches to it) and runs a smoke test against `https://remypost.me/` and the preview host. `deploy/remypost.caddy` is the Caddy block (long-cache `/assets/*`, no-cache pages, fallback to `index.html`); `deploy/vm-setup.sh` installs it. The secrets for the deploy are repository secrets and are not in the repo.
