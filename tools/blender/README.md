# 3D assets

The brand book on the cover and the monogram block are built from code, not by hand.

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --python tools/blender/build_models.py -- --render
tools/blender/optimize.sh
```

- `build_models.py` models both objects (Blender 5.2), exports raw `.glb` files to `tools/blender/out/`,
  saves `out/remypost-models.blend` to open and look around in, and with `--render` writes the two
  fallback posters (`apps/site/src/assets/models/book-poster-{light,dark}.webp`) and the social card
  (`apps/site/public/og.jpg`). Add `--draft` for a fast, noisy render; `--preview` for look-dev stills.
- `optimize.sh` compresses the exports (meshopt + WebP, via `@gltf-transform/cli`) into
  `apps/site/src/assets/models/`. Those are the files the site ships.
- `fonts/` holds static instances of Archivo (SIL Open Font License), cut from the variable font the
  site already uses, because Blender cannot read variable axes.

Material and node names are the contract with `apps/site/src/three/`: materials are painted from
the CSS colour tokens by name (`Cover` = ink, `Foil` = bone, `Pages` = paper, `Endpaper` = pine,
`Ribbon` = clay), and `CoverFront` / `Ribbon` are the pivots the code turns.

## Model contracts

Axes are three.js's (y up, +z toward the camera). Only ever move the empties named below: nodes
ending in `Mesh` carry the compression's own transform.

| File | Nodes | Materials → token |
| --- | --- | --- |
| `book.glb` | `Book` › `Body`, `Pages`, `CoverFront` (hinge; open with `rotation.y = -angle`), `Ribbon` | Cover → ink, Foil → bone, Pages → paper, Endpaper → pine, Ribbon → clay |
| `monogram.glb` | `Monogram` › `Block`, `Letters` | Ink → ink, Bone → bone, Clay → clay |
| `marks.glb` | `Marks` › `Mark_<project slug>` × 9 | Mark (matte, no highlight) → the plate's own foreground colour |
| `envelope.glb` | `Envelope` › `Shell`, `Letter` (slides up: add to its own rest `position.y`, which is −0.715 because its pivot is the sheet's lower edge; +0.55 shows the letterhead), `Flap` (hinge; open with `rotation.x = -angle`, about 3.35 rad is fully open) | Paper → ink (an ink envelope, so it reads on the page in both themes), Liner → pine, Sheet → bone, Ink → ink, Lines → stone, Wax → clay |
| `badge.glb` | `Badge` (origin = the slot it hangs from) › `Card`, `Clip` | Card → ink, Print → bone, Back → pine, Metal → stone |

| `stamp.glb` | `Stamp` (origin = centre of the rubber face; stands along +y, 1.68 tall, face 0.84 across) › `StampBody` | Handle → ink, Band → bone, Rubber → clay |
| `board.glb` | `Board` › `BoardMesh`: a unit sample board, 1 × 1 across, 0.022 thick, front face at z = 0. Scale x and y to the element and z by the element's width | Face (unlit: exactly the element's CSS colour), Edge (lit) → the element's own colour |
| `chip.glb` | `Chip` › `ChipMesh`: the same unit board cut for the small colour chips (0.03 thick, wider bevel) | Face, Edge → the chip's token |
| `leaf.glb` | `Leaf` › `LeafMesh`: a sheet of paper, hinge on x = 0, free edge at x = 1, y from −0.5 to 0.5, flat at z = 0 facing +z, 64 × 8 quads; two skins on the same shape | Leaf → bone (pine for the endpaper), LeafBack → paper; both carry the paper-fibre normal map |
| `straps.glb` | `Straps` › `RibbonStrip` (swallowtail end) and `StrapStrip` (square end): 1 wide, hanging down −y from the origin in 40 rows 1 unit apart | Strap → clay, double-sided, grosgrain normal map |

- The site only moves these three: it bends the leaf's columns, lays the strap's rows along a simulated chain, and scales the board. Their shape and surface are set here.
- Marks: 1 unit = 1 em of `.plate__mark` (Archivo, width 125, weight 560, tracking −0.04 em). Origin is
  the baseline at the left edge of the text box; the mark's back is at z = 0 and it stands 0.064 em proud.
- Envelope: 2.3 wide × 1.55 tall, centred on the origin, seen from the flap side. The wax seal rides on the flap.
- Badge: the card is 1.0 × 1.5 and hangs below the origin; the lanyard is drawn in code and ties on at
  the top of the clasp, (0, 0.34, 0).
