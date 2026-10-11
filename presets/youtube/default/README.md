# YouTube Default — the long-form finishing preset

The ONE default for long-form YouTube videos. Steps 1-2 of the pipeline (intake, rough cut) are
universal and unchanged; this preset defines everything after the cut: timeline architecture,
section structure, title cards, SFX, graphics tier, grade, audio finish, and the export lock.
Every other look (`vox-collage`, `liquid-glass` takeovers) stays **opt-in by name**.

Skeleton reverse-engineered from a real shipped assembly (read live off the Resolve API 2026-08-27), then **fully dialled in
on Premiere** across the `your-job` intro (2026-08-29 → 08-31) — the graphics vocabulary,
the animation registry, the low band, the prop glow and the footage moves were all tuned there.
The look is app-agnostic; the per-app mechanics live in those apps' skills. Read the LANES section
next if you are finishing in anything other than Premiere.

## Where each pipeline step lives in here

The craft sections below are grouped by subject, not by step order, so start from this index.

| step | read |
|---|---|
| 3 · Audio polish | [§ Audio polish](#audio-polish-pipeline-step-3--right-after-the-cut-lands) |
| 4 · Grade | [§ Grade](#-grade-pipeline-step-4--before-graphics-and-underneath-them) |
| 5 · Graphics | [§ Graphics](#graphics-step-5) + the craft it uses: [`default-overlay-style.md`](default-overlay-style.md), [`creative-moves.md`](creative-moves.md), [`animations.md`](animations.md), [`text-animation/`](text-animation/), [`titles/`](titles/), [`backgrounds/`](backgrounds/), and [§ Opening zoom-out](#opening-zoom-out--every-video-starts-with-it-2026-08-29-re-dialled-2026-09-10) / [§ Emphasis push-in](#emphasis-push-in--the-default-zoom-in-2026-08-31) for the footage moves |
| 6 · SFX | [`sfx.md`](sfx.md) + [`sfx.json`](sfx.json) |
| Captions | [§ Captions](#captions-none-on-long-form) — none; a step-5 layer only on the short-form presets |
| 8 · Export | [§ Export](#export-step-8--the-lock) |

Steps 1–2 (intake, rough cut) and 7 (review) are universal and carry nothing preset-specific.

## 🔒 LANES — what is universal, and what is per-app

**This preset is a LOOK, not a Premiere project.** Everything that decides how the video looks is
app-independent; only two things are per-app: **where you put a clip** and **how you bake a move
onto footage.**

| Layer | Universal? | Notes |
|---|---|---|
| Graphics, title cards, text animations, backgrounds | ✅ fully | HTML comps → **alpha ProRes 4444 movs** (overlays) or **opaque mp4s** (full-screen graphics, grain baked; title cards via `titles/render.sh`, no grain). Any NLE takes both. |
| The in/out registry, THE FLOAT, arrows, burst reveals | ✅ fully | Runs inside the comp, before the file exists. |
| Card language, colours, THE LOW BAND, prop glow, scope | ✅ fully | Design rules, nothing to execute. |
| Section structure, title-card cadence, track roles | ✅ fully | A track map is generic NLE vocabulary (this one was read off a **Resolve** project). |
| The numbers on a footage move | ✅ fully | "100 → 115 over 18 frames, cubic ease-in-out" means the same everywhere. |
| **Placing** a graphic at a time on a track | ⚠️ per-app | Mechanics per lane, and which lanes have one: [`LANES.md`](../../../LANES.md). |
| **Baking** a footage move (zoom, push-in) | ⚠️ per-app | Same. Anything undocumented = keyframe by hand from the numbers above. |
| **Grading the footage and NOT the graphics** | ✅ the rule / ⚠️ the mechanism | The contract is universal: footage graded, graphics untouched, established before graphics are placed. How you get there is per-app. |
| Audio finish + export settings | ✅ the target / ⚠️ the mechanism | The targets are stated below; how each app hits them is per-lane. |

🔒 **[`LANES.md`](../../../LANES.md) owns everything about the per-app half — which lane has a
recipe for a step, where it lives, and what to do when it has none. Read the row for your step.**

## Project setup

- **Match the project to the SOURCE fps.** ffprobe the raw first; the app's own read of the
  imported clip is the final authority (iPhone footage is variable-rate and can ingest at a
  different rate than ffprobe reports). How a project is created at that rate is per-lane
  ([`LANES.md`](../../../LANES.md) § step 2 → the app skill's project-setup section).
- **Resolution follows the footage:** 3840×2160 when the video is screen-recording-heavy (screen
  captures are 4K sources), 1920×1080 when the footage is 1080. Whether the timeline auto-conforms
  a mismatched asset or needs a scale set is per-lane (the app skill); never hand-scale before
  checking which.
- **Every media file lives in `projects/<job>/`.** One shipped job played 3 clips straight out of
  `~/Downloads` (cold-open, demo recording, meme b-roll) — that is a defect, not a pattern. Copy
  cutaway/meme media into `broll/` at intake so the project survives a Downloads cleanup.
- **Whether the audio polish swaps source files or applies clip effects is a lane property**
  (see Audio polish below); the timeline is built against the raw sections either way.

### 🔒 The AUTHORING FRAME is always 1920×1080

**Every locked number in this preset is in a 1920×1080 coordinate space** — THE LOW BAND,
the placement table, the text-animation builder (`W, H = 1920, 1080`), the
background comps. **Author every graphic at 1920×1080 regardless of the footage's resolution**,
and let the timeline scale the overlays if the project is 4K. **How that scaling happens is
per-lane and is the ONE place a 4K project needs a decision:** some apps auto-conform a 1080
asset to a 4K frame and some need a scale set on the graphics track; the app skill says which
(via [`LANES.md`](../../../LANES.md)), and doing it the other app's way either crops the middle
out or leaves the overlay a quarter-size.

⚠️ **`chin-line.py` reports the chin in the SOURCE video's own pixels.** On a 4K raw, normalize
before using it: `y_authoring = y_measured × 1080 / source_height`. Feeding a 4K chin number
straight into a 1080 comp puts every overlay off the bottom of the frame.

## Timeline architecture — the track map

Read off `full assembly 4K30` as shipped, then **amended 2026-08-31 to seat the grade**:
the shipped job had graphics on V2 and no grade track. The map below is the one to build.

⚠️ **The grade track is why this map has to exist before the graphics pass starts.** The grade
has to reach the footage and nothing else, so on any track-based app the grade layer sits BETWEEN
footage and graphics, and it is created empty at project setup: adding it later means inserting a
track *underneath* graphics already placed (recoverable on the lanes that have a recipe for it,
but never free). A lane whose footage-only separation is a grouping rather than a track needs no
track shuffle; the contract (footage graded, graphics untouched, before any graphic lands) is the
same. Mechanics per lane: [`LANES.md`](../../../LANES.md) § step 4.

| track | role | contents |
|---|---|---|
| V1 | the spine | EDL-replayed section clips + 3s section title cards, butt-joined |
| **V2** | **the grade** | ONE grade layer spanning the whole timeline (pipeline step 4): an adjustment layer or the app's equivalent. It sits here — above the footage, below the graphics — so it grades the footage and nothing else. Created empty at project setup, before any graphic is placed. |
| V3 | graphics | HyperFrames alpha ProRes 4444 overlay cards (rendered STRAIGHT alpha; a lane that composites premultiplied converts on its own side) + opaque full-screen mp4s, meme/b-roll cutaways, text callouts |
| V4 | accents | mascot/sticker PNGs that sit above a V3 cutaway |
| V5 | spare | keep empty for one-offs |
| A1 | voice | linked section audio — untouched during the cut and assembly; the step-3 polish lands here right after the cut (see Audio polish below) |
| A2 | SFX, primary role | step 6 ([`sfx.md`](sfx.md) § The law, 6, owns what lands on which layer); the title-card whoosh at every section boundary lands here too |
| A3 | SFX, layer 2 role | the second sound on a hit |
| A4 | SFX, layer 3 role | a third layer on the same hit; rare |
| A5 | music role | optional flat bed, opt-in only (`background-music` rules) |

**The audio rows are ROLES on this map** — primary / layer 2 / layer 3 / music. A lane whose audio
tracks are laid out differently maps by role; `sfx.json`'s `tracks` block carries the same pairing.

**Media pool layout:** section mp4s + title cards + timeline in the root, `graphics/` (the alpha
movs), `broll/`, `sfx/` (the bundled SFX library, imported wholesale from `assets/sfx/`), `Archive/`.

## Section structure

```
cold open (proof clip, ~7s) → intro (graphics-heavy, basic tier)
→ [ title card → section body ] × N → outro
```

- **A normal long-form cut is a plain rough cut: one video track, clips in dialogue order (2026-09-19).**
  The cold open is what the creator filmed. A "Coming up…" preview montage built from later footage, or a
  facecam cam-cut layer over a walkthrough, is one video's move, never added unasked.

- **Title card:** 3.0s (90 frames at 30), opaque mp4 on V1 between sections. Built by
  [`titles/`](titles/) (below). Placing the cards on V1 at the section boundaries is per-lane
  ([`LANES.md`](../../../LANES.md) § step 5; scripted on some lanes, hand-dropped on others); the
  card and whoosh timings here are the contract.
- **Whoosh:** `assets/sfx/Genius Intro Sound.wav` on A2, placed with each card, ~3.5s used,
  ~1s crossfade-out tail so it ducks under the section's first line.
- **Chapters:** the title-card timeline positions ARE the YouTube chapter timestamps — read them
  off the timeline at export time, no separate bookkeeping.
- **Sections are separate rough-cut sub-jobs** (`sections/<name>/`, raw symlinked, own transcript)
  — one WhisperX run each, replayed onto the assembly by EDL.
- ⚠️ **Sections are a MULTI-TAKE structure, not a requirement.** They exist when the video was
  filmed as separate takes. **A single continuous raw is ONE section** — no title cards, no
  chapter boundaries, no cold-open split — and the structure above collapses to
  `intro → body → outro`. Do not invent section boundaries (and therefore title cards) inside one
  continuous take; if the script clearly wants chapters, that is a one-line ask at plan time, not
  an assumption. The shipped `your-job` intro is the single-raw case: no title cards.
- **Outro:** keep the right side + bottom band clear during the last ~20s — YouTube end-screen
  cards snap there.

## Opening zoom-out — every video starts with it (2026-08-29; re-dialled 2026-09-10)

**THE MOVE (universal):** the first clip on the spine opens punched in and settles to
100% — **scale 115 → 100 over 18 frames, QUARTIC ease-out (`quart`, 1 − (1 − t)⁴), about the frame
centre**, starting on the clip's first frame. Fast off the mark, slower and slower into 100: 94% of the
travel is done by the midpoint and the last nine frames creep the final 1% (the same settle feel as the
text animations). Every video opens on it, at the very first frame, because that snap is what hooks the
viewer in (2026-09-10). The first lock was 107 → 100 over 10 frames, cubic (you cut it from
2.5s to a snap, 2026-08-29); on the your-job refinement pass you asked for more drama, a
deeper start, a longer settle and then a sharper curve, graphed cubic against quart and picked quart
(2026-09-10). The verify is the curve's own signature: frame 9 of 18 reads exactly **100.94**
(a cubic bake reads 101.88 there, a linear one 107.50). Overlays on the
graphics track do NOT inherit it: they hold still while the footage settles.

**HOW:** per-lane, via [`LANES.md`](../../../LANES.md) § step 5 → that app's skill. On any lane
with no recipe it is two keyframes and an ease done by hand — scale 115 → 100 across the first 18
frames, quartic ease-out (1 − (1 − t)⁴). Nothing here needs scripting to be correct.

## Emphasis push-in — the default zoom-IN (2026-08-31)

**THE MOVE (universal):** when you vocally emphasize a phrase on camera, the footage pushes in —
scale **100 → 115 over 18 frames, cubic ease-IN-OUT (the S), about the frame centre**, beginning
~2 frames before the emphasized word and held to the clip's end (the next cut resets it). Paired
with a text animation of the phrase — when to reach for it: [`creative-moves.md`](creative-moves.md)
move 5. **It is the zoom-out's distance and length with the OTHER shape (2026-09-10):** the
opening zoom-out snaps and settles (quart ease-out), the push-in eases in, accelerates through the
middle and eases out — `t < 0.5 ? 4t³ : 1 − (2 − 2t)³ / 2`, the bridge's `inout`. Dialled on
your-job's 1:03 push-in in three steps (matched to the zoom-out's quart first, then
"the zoom in should have a different curve than the zoom out, an S shape eased on both ends"),
approved on that one, then baked into all seven. The first lock (2026-08-31) was 100 → 108 over
12 frames, cubic ease-out, itself dialled live off the shipped intro (*"a little longer and zoom
in a tad bit farther, but keep the eased smooth motion"*, replacing 6% over 8 frames).

**HOW:** per-lane, via [`LANES.md`](../../../LANES.md) § step 5 → that app's skill (Premiere:
`premiere-bridge.mjs zoom … "ease":"inout"`). On a lane with no recipe it is two keyframes on clip
scale with a cubic ease-in-out, by hand; the numbers above are the whole spec.

**Verify anywhere:** frame 9 of 18 must read exactly **107.50** (half the travel — the in-out
signature; the quart zoom-out reads 100.94 there on its way down, a linear bake 107.50 too, so
also check frame 4 = **100.66** and frame 14 = **114.34**: linear reads 103.33 / 111.67). The
check is app-independent.

## In / out animations → [`animations.md`](animations.md) — THE REGISTRY

🔒 **Every entrance and exit is one of the presets there; never author a bespoke one.**
Two families: the SCALE family (**`pop`** · **`slam`** · **`flash`**) for free-standing OBJECTS,
and the TRAVEL family — **`riseIn` / `riseOut`** (the nudge, and the everyday default for type,
cards and panels) and **`slideIn(from)` / `slideOut(to)`** (OFF SCREEN — a rise is not a slide).
The default exit is `riseOut`. Every number, the frame-0 and near-full-frame rules, the variation
principle and the 12 fps `flash` ban are [`animations.md`](animations.md)'s.
`draw-on` (arrows, tangent-computed heads) is a reveal, not a move. Hold life is THE
FLOAT, not an entrance — see creative-moves.md move 2.

## Full-screen backgrounds → [`backgrounds/`](backgrounds/)

The two standard fields behind any full-screen graphic: **`bg-light`** (light-gray
gradient, feathered navy vignette, film grain baked in) and **`bg-dark`** (deep navy,
faint 100px brand grid, edge fade). Locked 2026-08-29; specs, knobs, and the
vignette-measurement lesson in [`backgrounds/README.md`](backgrounds/README.md).
Renders are regenerable cache (`./render.sh`, ~90s each) — comps are the truth.

## Section title cards → [`titles/`](titles/)

The kinetic Inter riser (per-letter rise on an exponential curve, stepped to 12 fps, sampled
motion blur). Usage:

```
cp -R presets/youtube/default/titles projects/<job>/hf-graphics/titles
cd projects/<job>/hf-graphics/titles
cp titles.json.example titles.json   # edit ids + copy
./render.sh                          # → renders/<id>.mp4 (card) + <id>-alpha.mov (overlay)
```

The opaque card uses `renders/grid-bg.mp4` (the navy brand-grid backdrop) when present (drop your own backdrop loop at `titles/renders/grid-bg.mp4` — the branded one does not ship), and falls back to the solid navy field when it isn't. The V1 timeline only ever
places the opaque card; the alpha variant exists for overlay use. That backdrop is a committed
brand SOURCE asset with no generator — the one exception to "renders are regenerable cache", and
it does not ship to clients. The look itself: [`titles/titles-style.md`](titles/titles-style.md).

## Emphasis text animations → [`text-animation/`](text-animation/)

Word-synced emphasis text for a phrase or a dead stretch — each word rises in and settles (`power3.out`), timed to the spoken word with an 80 ms lead. **The
lock is the animation + the font** (Helvetica Bold, lowercase, tight tracking, no fade-in,
faint black glow); the one power word in a phrase gets the emphasis font — **Playfair
Display Italic w700** (the two-font system, full recipe in the style doc), and the
builder carries the LAYOUT LAW (low block, width-solved sizes, balanced lines); placement /
color / glow flex per animation. Spec + knobs:
[`text-animation/text-animation-style.md`](text-animation/text-animation-style.md). Same usage shape as `titles/`:
copy the folder into `projects/<job>/hf-graphics/`, write `text.json`, `./render.sh`, place
the alpha movs on the graphics track at the printed times.

## 🔒 Grade (pipeline step 4 — BEFORE graphics, and underneath them)

**THE TARGET (universal):** the footage carries a consistent look, and **the graphics carry none
of it.** One treatment across the whole timeline, applied to the footage layer only, established
before a single graphic is placed. The short-form Talking Head Explainer points here for the same house
grade on its camera footage ([its README § Grade](../../instagram/talking-head-explainer/README.md#grade-step-4-default-on-this-format)).

**Footage-only is the requirement, not a preference.** Every colour in this preset is a locked
hex — accent royal, the prop glow, card fills, the two full-screen backgrounds — chosen to read
over footage and against each other. A grade sitting on top of the graphics shifts all of them,
and it shifts them invisibly, because a graded card still looks like a card.

### Why it runs before graphics (two independent reasons)

1. **Track mechanics** — lane-dependent, and the reason is cheap to undo. On a lane where the
   separation IS a track (an adjustment layer affects every track below it, so the layer lives
   *between* footage and graphics), that track is free at project setup and awkward to insert
   under clips already placed. Recoverable, so this reason alone would not fix the order; reason 2
   does. On a lane where the separation is a grouping rather than a track (a color group) this
   reason does not apply at all — reason 2 still does.
2. **Measurement validity.** The step-5c defect loop measures real numbers off program renders:
   prop-glow lift outside a prop's box, low-band legibility, card contrast over the shot. Grade
   afterward and every one of those measurements was taken against a picture that does not ship.

**Clip transforms are a non-issue.** The opening zoom-out and every emphasis push-in are
clip-level Motion/Transform on V1, applied *before* the adjustment layer sees the composite. The
grade lands on the already-transformed image, and re-baking a move later never disturbs it.

### 🔒 THE LOOK: `Autumn-Rec709.cube` as a Creative Look (2026-09-01)

The house LUT is [`assets/luts/rec709/Autumn-Rec709.cube`](../../../assets/luts/rec709/Autumn-Rec709.cube)
(the bundled Rec709 LUT, 33³), replayed from the `Autumn-Rec709.lookparams` beside it. The whole
library lives under `assets/luts/`; [`assets/luts/README.md`](../../../assets/luts/README.md)
inventories it and names the per-lane replay tool ([`LANES.md`](../../../LANES.md) § step 4). It is applied on the grade layer as a **Look** (the cube renders AFTER any
correction dials, so one colour effect holds everything). **The locked preset (2026-09-14; 70/115 from 2026-09-01 until then): Look Intensity 80, Creative > Adjustments > Saturation 120, everything else at
default.** Same settings for every job regardless of footage. This preset is the single
source: every long-form `youtube/default` job inherits Autumn-Rec709 from here, and each lane's
replay tool reads it as its own default; a job never picks its own. (London-Rec709 was the first pick the same day, tried in the Input LUT slot;
Autumn was chosen over it. Its `.lutparams` is kept in this repo beside its cube as a working
input-slot example (the params file is not part of the client package); nothing uses it.)

⚠️ **The cube is universal; the two dial values are Lumetri's.** "Look Intensity 80 / Creative
Saturation 120" names Premiere controls, so another app hits the same appearance with its own
equivalents — the cube at reduced strength plus a small saturation lift — and **verifies by
measuring a frame, not by matching numbers.** Never report the dial values as applied on a lane
that has no Lumetri.

No per-machine install is needed: the cube data is embedded in the params file, so the replay
carries it. Minting params for a NEW LUT is the only time the file is browsed to by hand.

**Any cube in the library can become the look.** It takes ONE hand-application, ever, to capture a
cube's params; from then on it replays on any job by name, on any machine. That is a lane mechanic,
not a look decision. The default never moves unless someone changes it deliberately.

### 🔧 How each lane gets there

**The step is TWO things and no more: the layer, and the Look on it.** Nothing about them is a
per-job decision. Which lanes have a scripted recipe, which are unvalidated, and where each recipe
lives: [`LANES.md`](../../../LANES.md) § step 4. On a lane with no recipe, put an adjustment or
effects layer between the footage and the graphics track (or apply the cube to the footage clips
directly) and set the look by eye to the intensity and saturation above; the contract is only that
the footage is graded and the graphics are not.

⚠️ **Verify from a program render with the layer toggled, never from an effect readback.** The tell
is the MAX channel delta between the two frames (or its p99), in the tens. The mean delta depends on the
footage and is not the tell: a dim, purple-lit set measured a mean of 6–8 per channel against a max of 73
with the look plainly on (2026-09-27). A delta of 0 does not mean "the LUT
failed" — on every lane it can equally mean the track's output is off, so read the track's mute
state before drawing any conclusion.

### 🔒 There is no colour-correction step (2026-09-01)

The grade is the grade layer plus the Look. Nothing measures or corrects the footage first.
Properly shot footage needs no correction (an auto-correct pressed on the actual footage moved
nothing worth keeping), and an algorithm that fixes badly shot footage is a project of its own,
parked. If a clip needs a correction it is a manual call, made before the Look, and any dials
you settle on ride inside the captured `.lookparams`.

A measured "auto-correct" solver was built and deleted the same day (2026-09-01): every reference
frame it was calibrated against was the wrong thing, including an app's Auto pressed on the
adjustment layer itself, which analyses the layer's own blank media rather than the footage. The
full story and the two measurement lessons (never gray-world a lit set; pick the measurement mask
once, on the uncorrected frame) live with the Premiere grading doc, where the experiment ran:
[`lanes/premiere/premiere-grading.md`](../../../lanes/premiere/premiere-grading.md).

### One consequence to carry

**Generated b-roll placed above the grade stays ungraded.** For a Higgsfield clip that is usually
right (it was never camera footage), but it is a choice — drop it on V1 instead if it should take
the same look.

**A screen-recording section is not graded (2026-09-14).** This is screen-recording FOOTAGE
(§ Screen-recording footage stays bare, below). The Look is for camera footage.
Over a screen capture it tints the UI, the page and the camera PiP. So the grade layer ends where
the camera footage ends, and a later section that is a screen recording stays off it. On one
job the grade was extended over a closing screen-recording section, the creator trimmed it back to the
intro, and a later pass re-extended it by mistake. Your note: *"why did you put the
grade back over the screen recording."*

## Screen-recording footage stays bare (2026-09-19)

Two different things share the words "screen recording", and only one of them is covered here:

- **Screen-recording FOOTAGE** is raw footage: you and your screen, a walkthrough or a demo you
  filmed. It sits on V1 as part of the cut.
- **A screen-recording GRAPHIC** is a supporting visual the editor records (a `screen-rec` /
  `screenshot` cell, [`creative-moves.md`](creative-moves.md) moves 7 and 8). It is a graphic like
  any other and follows the graphics rules.

**Screen-recording FOOTAGE carries no graphics and no grade, by default and without being asked.**
The screen is already the visual. Graphics and the Look go on the camera sections only, the plan
records the camera ranges as `graphics_scope` (`graphics-plan` § the plan contract) so the density
numbers are held to them, and the grade layer stops where the camera footage stops (§ Grade above).
A graphic over the footage is opt-in, named by you for that spot.

## Graphics (step 5)

- **The default vocabulary = [`creative-moves.md`](creative-moves.md) (2026-08-29 —
  apply UNPROMPTED):** text animations liberally (the default sprinkle), punch cut-to-graphic at
  key claims (a SCENE, not a card — creative-moves 2), scene slides, self-made
  vector props entering on the house pop, emphasis push-ins paired with the text animation of the phrase. Entrances follow
  [`animations.md`](animations.md) and the variation principle; hold life is the no-rotation
  **float** (creative-moves 2). The bg choice drives locked render flags — see
  [`backgrounds/README.md`](backgrounds/README.md).
- **Cards:** [`default-overlay-style.md`](default-overlay-style.md) (blue UI cards over the
  footage) remains the language for informational beats. Its accent furniture carries
  **THE PROP GLOW** (bars, dots, chips, meters bloom in their own colour; type is default-off — it may glow where the subject itself emits light). Decorative extended takeovers / bespoke art /
  other looks stay opt-in by name at plan time, never inferred.
- **Evidence and readable sources are DEFAULT work, not a tier upgrade:** a beat whose evidence is
  a real thing on screen gets a real capture (`graphics-plan` § THE CAPTURE GATE); a beat whose
  content is written text gets that source rebuilt verbatim, full-screen, with the discussed
  clause highlighted on its spoken words ([`creative-moves.md`](creative-moves.md) § 4d).
- **Build:** per-job `hf-graphics/` generated build, part-by-part renders
  (the `graphics-build` skill).
- Plan with `graphics-plan`, build with `graphics-build`, place on the graphics track (V3 in the
  map above; the placement mechanics per lane are the app skill's, indexed by
  [`LANES.md`](../../../LANES.md) § step 5), then converge with `edit-review`.

## Definition of Done — the autonomous quality bar (2026-08-29)

The your-job intro's first clip (pop → punch graphic with slide + props → push-in
+ pop) IS the bar. A default pass is not finished until it hits that level, unprompted:

- Every text/graphic beat **word-synced** off the canonical transcript, nothing bleeding across a
  V1 cut — [`creative-moves.md`](creative-moves.md) move 1.
- **Layout is measured, never eyeballed** —
  [`text-animation/text-animation-style.md`](text-animation/text-animation-style.md) § THE LAYOUT LAW.
- **Every under-the-face overlay inside THE LOW BAND**, re-derived for the shoot —
  [`default-overlay-style.md`](default-overlay-style.md) § THE LOW BAND.
- **Every accent prop glowing; type glow default-off** —
  [`default-overlay-style.md`](default-overlay-style.md) § THE PROP GLOW.
- **Every entrance and exit is a REGISTRY preset, varied by ROLE**, never improvised —
  [`animations.md`](animations.md).
- **Hold life is THE FLOAT** — [`creative-moves.md`](creative-moves.md) move 2.
- **Action beats are SCENES, not cards**, and nothing is decoration shaped like data —
  [`default-overlay-style.md`](default-overlay-style.md) § CARDS NAME, SCENES ENACT.
- **Every arrowhead COMPUTED from its path's end tangent** —
  [`animations.md`](animations.md) § The arrow.
- **A READABLE graphic HOLDS its complete content** —
  [`creative-moves.md`](creative-moves.md) 4d.
- **Every comp probed before rendering, every placement verified from the app's program output**
  and read back off the track — the `graphics-build` skill.
- **Rhythm law held** — the cadence to plan to is
  [`creative-moves.md`](creative-moves.md) § THE DENSITY NUMBERS.
- Emphasis font sprinkled where it earns its place; grain on every full-screen graphic.
- **The process (2026-08-29): plan → build one graphic at a time, converging EACH to
  right before the next** (simple pop = verify and move on; complex/full-screen = as many
  rounds as it takes, ~10 min working budget) → all placed → **the step-5c `edit-review` loop:
  `uv run workflows/graphics-qa.py projects/<job>` green as the precondition, then review rounds
  until the first CLEAN round, hard cap 3.** Don't park a known defect for the loop.

## Audio polish (pipeline step 3 — right after the cut lands)

**The target, the measured gain and the limiter are universal, and they live with the per-lane
mechanics: [`LANES.md`](../../../LANES.md) § step 3.** Nothing about the audio finish is
long-form-specific; what this preset fixes is WHEN it runs.

- **Never touch levels during the rough cut or assembly** — one pass over the whole timeline,
  run immediately after the EDL replay lands (pipeline step 3, you 2026-08-28). A timeline
  rebuild discards clip effects, so re-apply after any re-replay.

## Captions (none on long-form)

- **No burned-in captions.** YouTube CC serves long-form.
- **No thumbnail either (2026-09-01).** A thumbnail is a publishing asset, not an edit, and
  this preset finishes at the exported file; the generator lives in the publishing repo (2026-09-04).

## Export (step 8) — the lock

**THE NUMBERS (researched and set by Claude on your delegation, 2026-09-26; sources and proof:
the engineering archive).**
One MP4 straight to `projects/<job>/outputs/<job>.final.mp4`:

- **3840×2160 for a 4K timeline AND a 1080 one.** YouTube makes renditions only up to the upload's size, and its
  1440p/2160p ones carry several times the bitrate of any 1080p one, so a 1080 timeline is uploaded at 2160p
  (scaled by the lane at export, no extra file size at the house bitrate). This replaces the native-1080 file.
- **H.264 High, 4:2:0, progressive, BT.709** (primaries, transfer and matrix tagged, limited range), level 5.1
  (5.2 above 30 fps; Premiere's preset says 5.2 throughout, which is legal).
- **The SEQUENCE's frame rate**, never resampled.
- **CBR 50 Mbps at 24–30 fps; CBR 80 Mbps at 48–60 fps.** YouTube asks 35–45 and 53–68 VBR; the house sits above
  each band at the measured VMAF ceiling (50 and 65 scored identically at 2160p30), and CBR because VideoToolbox
  VBR treats the target as a ceiling (a VBR 50 export landed at 17.6 Mbps).
- **Closed GOP of half the frame rate, 2 B-frames** where the encoder takes it (the ffmpeg lanes); Premiere's
  hardware encoder writes a 1 s GOP whatever the preset says, which YouTube accepts.
- **AAC-LC 320 kbps, 48 kHz stereo** (YouTube asks 384k; Premiere's AAC tops out at 320k, YouTube re-encodes
  audio anyway, and the repo never drops below 256k). **moov at the front**, no edit lists. No HDR.

**Verify the finished FILE with ffprobe** — never trust the app's own reported settings. The encoder settings each
app needs to reach that target are per-lane: [`LANES.md`](../../../LANES.md) § step 8. An app not listed just
needs to hit the same numbers; the preset does not care which encoder dialog produced them.

Then `./finalize.sh <job> --apply` for promotion + the `~/Downloads` export copy — lane-agnostic,
it only looks at the files in `outputs/`.

⚠️ **Every scripted lane's export runs only on the creator's go** ([`LANES.md`](../../../LANES.md)
§ step 8): the run pauses at step 7, and the settings above are what the lane exporter (or a hand
render) must hit. `finalize.sh` runs once a final file exists in `outputs/`; never render one to
satisfy the step.
