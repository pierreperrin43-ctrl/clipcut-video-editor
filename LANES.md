# LANES — which app can do which step, and where the recipe lives

**The law this file enforces: the PRESET says WHAT, the APP SKILL says HOW.**

A preset is a LOOK. Every number in it (a frame count, a scale percentage, a hex, a dB, a
duration) means the same thing in every editor, and every graphic it specifies is rendered by
HyperFrames into a file any NLE can take. So the preset never carries app mechanics, and an app
skill never carries look decisions. That split is what makes ONE preset produce the SAME video on
any lane.

It is also why the mechanics live with the app and not with the preset: placing an alpha mov at a
timecode is identical whether the job is `youtube/default` or `instagram/talking-head-explainer`. Written into
each preset it would be re-written once per preset per app. Written into the app skill it is
written once, and a new preset inherits every lane for free.

**This file is the third piece: the index that connects them.** At step N on lane L, read the
preset's § step N for the target, then this file's row N for where lane L's mechanics are.

## Where the lanes live

**Every app-specific file is under [`lanes/`](lanes/README.md), one folder per finish surface: `lanes/premiere/`, `lanes/resolve/`, `lanes/capcut/`, `lanes/chat-only/`, `lanes/finalcut/`** (since 2026-09-03; Final Cut 2026-09-25). Scripts, templates, lane sheets and each lane's `lab-notes.md` (the locks true only on that app). The app skill in `.claude/skills/` is the HOW doc for the lane and points into its folder; `workflows/` at the root holds only universal utilities. So the two questions have two homes: "is step N defined and done" is answered by `CLAUDE.md` § The Pipeline and `projects/<job>/RUN.md`; "does app X have a scripted recipe for step N" is answered here and in `lanes/<app>/`. Never let the second question's answer leak into the first (the chat-only lane having no grade stage is a lane fact, not a pipeline fact).

## How to read a cell

| | |
|---|---|
| ✅ | **Scripted and validated.** A command or an API call exists and has been run on a real job. |
| ✋ | **Manual, by design.** Nothing to script, or the creator owns it. Do it by hand from the preset's numbers. |
| ⚠️ | **Unvalidated recipe.** The mechanism is documented and consistent with what is known, but no job has run it. Treat the first run as a test: verify by measurement, then upgrade this cell. |
| ⛔ | **Gap.** No recipe. Do it by hand from the preset's numbers and **say so out loud** — see below. |
| — | **Nothing lane-specific.** The step is universal; the lane changes nothing about it. |

**If an app skill's STEP INDEX disagrees with this matrix, this matrix wins.**

**TikTok/raw carries only step 5, captions included:** a LOOK for the graphics step (the hook card and
its caption layer); every other step takes the universal target stated in this file's step rows. **The
Talking Head Explainer (`instagram/talking-head-explainer`) reaches further**, and its
[README](presets/instagram/talking-head-explainer/README.md) § Where each step lives is the index: step 2
taste ([`story-and-cut.md`](presets/instagram/talking-head-explainer/story-and-cut.md)), a step-3 addendum
(the second-voice lift), step 4 (the grade on its camera footage), the step-5 footage layout keys (row 5′
below), its own step-6 map ([`sfx.json`](presets/instagram/talking-head-explainer/sfx.json)) and a music
level. Its WHAT stays in the preset; the HOW per lane stays here.

## The matrix

Steps are the pipeline in CLAUDE.md § The Pipeline. Lanes are the five finish surfaces. **Premiere and CapCut run on macOS and Windows** (every lane script and helper, `premiere-up.sh` / `premiere-pid.sh` / `premiere-dismiss.sh` and the CapCut bridge's live lane included, since the Windows port of 2026-09-27; the Windows backends are `lanes/premiere/premiere_win.py` and `lanes/capcut/capcut_win.py`), **Resolve and chat-only on macOS, Windows and Linux**, and **Final Cut (macOS)** runs through SpliceKit, installed by
`./setup-finalcut.sh` (ships at the client package root; in the author's repo: `packaging/overlay/setup-finalcut.sh`): a fresh job's whole timeline is built from its pipeline files by `lanes/finalcut/replay.py`,
proven 2026-09-25 on a Talking Head Explainer and a long-form with a section, each clip for clip against its Premiere
project and in Final Cut, and exported with no clicks; what the files do not carry (a hand-laid patch, a hand Motion)
it cannot rebuild, so the run says so.

| # | Step | Premiere | Resolve | CapCut | chat-only | Final Cut |
|---|------|----------|---------|--------|-----------|-----------|
| 1 | Intake | — | — | — | — | — |
| 2 | Rough cut → replay | ✅ | ✅ | ✅ | — | ✅ |
| 3 | Audio polish | ✅ | ✅ | ✅ baked | — baked by splice | ✅ baked |
| 4 | Color grade (long-form + Talking Head Explainer) | ✅ | ⚠️ | ⛔ | ⛔ | ✅ |
| 5 | Graphics | ✅ | ✅ | ✅ | ✅ | ✅ |
| 5′ | Footage layout keys (Talking Head Explainer) | ⚠️ | ⛔ | ✅ | ⚠️ | ✅ |
| 6 | SFX | ✅ | ⚠️ 21.1+ | ⛔ plan only | ⚠️ | ✅ |
| 7 | Review | ✋ | ✋ | ✋ | ✋ | ✋ |
| 8 | Export | ✅ on the creator's go | ✅ | ⚠️ | — the render IS the file | ✅ |
| + | Background music (opt-in) | ✅ | ⚠️ 21.1+ | ✋ audio track | ✅ | ✅ |

### Where each cell's recipe lives

**Step 1 — Intake.** Universal: copy (never move) into `projects/<job>/raw/`. No lane involvement.

**Step 2 — Rough cut, then the EDL replay.** The cut itself is universal (`rough-cut`: WhisperX,
kill, splice `RENDER=0`). Only the replay is per-lane, and all four apps rebuild the same
`transcript/cuts.json` as separate trimmable clips. **On long-form the main sections are
colour-labelled at the replay, every time (2026-09-19)** (intro, each body section, outro),
and every clip laid later carries its section's colour: the labels are how he reads the timeline.
Premiere mechanics: `premiere-pro` § Colour labels.

- Premiere ✅ `node lanes/premiere/premiere-bridge.mjs replay …` — `premiere-pro` § Step 2. Every cut gets `uv run workflows/cut-audit.py <job> --grid <sequence rate>` BEFORE the replay and `--live` after it (a mixed-rate source, e.g. a 30 fps screen recording on 23.976, is why: Premiere floors twice), and the cut is done only when `uv run lanes/premiere/cut-proof.py <job>` exits 0 (the bounced timeline transcribes to the script) — `rough-cut` § Audit the cut on the finish surface's grid · § The proof
- Resolve ✅ `uv run workflows/cut-audit.py <job> --grid <timeline rate>` before the replay, then community engine: `media_pool create_timeline_from_clips`, one call; official engine (`ResolveMCP`): `AppendToTimeline` in `run_script`, one call per track — `davinci-resolve` § Step 2
- CapCut ✅ `uv run workflows/cut-audit.py <job> --grid <draft rate>` before the replay, then `uv run lanes/capcut/capcut-bridge.py replay <job>` — `capcut` § Procedure 2
- Final Cut ✅ `uv run workflows/cut-audit.py <job> --grid <timeline rate>` before the replay, then `uv run lanes/finalcut/replay.py projects/<job>` builds the whole timeline from the job's (and its sections') pipeline files as FCPXML, every cut a spine clip on the timeline's frame grid with the dialogue ON it (an `audio_lead` as a split edit), then `import.py` imports it through Final Cut and `verify.py` proves the live project clip by clip — `final-cut-pro` § Procedure. A rebuild is a new library (`<job>-v2`), so a hand edit in the old one stays. A finished Premiere sequence ports instead with `lanes/finalcut/prproj-read.py` → `lanes/finalcut/port-premiere.py`
- chat-only — no replay; `splice.sh` renders the flat cut, on the SECOND splice after `polish-boundaries.py` (the first runs `RENDER=0` on every lane) — `rough-cut` § Polish the boundaries

**Step 3 — Audio polish. This section is the ONE home of the universal audio target.** One static
pass over the whole timeline, never dynamic loudnorm, never per-segment gain, re-applied after any
timeline rebuild (a rebuild discards clip effects). The house chain:

    gain = round(−17 − measured)  →  hard limiter at −6 dBFS

`uv run workflows/voice-gain.py projects/<job>` measures the raw's KEPT speech ranges
(`transcript/cuts.json`, ebur128 — never the whole take, dead air drags the number down) and returns
the whole-dB gain onto **−17 LUFS integrated pre-limiter**; a quiet shoot gets more, a hot shoot
less. The limiter is FIXED at **−6 dBFS**, so peaks land about 8 dB over the ceiling and it works
every stressed syllable — that saturation is the point (2026-09-03, calibrated on
`your-job`).

**A NAMED gain is the user's call and nothing else (2026-09-19).** `--gain` on `audio-polish.py` and
`AMPLIFY_DB` on `splice.sh` override the locked measurement, so a measurement that FAILS is fixed at
`voice-gain.py`, never worked around with a number — and any named gain is stated in the report and
written into RUN.md as a deviation. `voice-gain.py` builds its kept-range `aselect` as a BALANCED
tree (a flat `a+b+…` past about 100 terms aborts ffmpeg with "Cannot allocate memory", which is how a
193-range walkthrough measured nothing) and now exits with the ffmpeg code and stderr tail instead of
a regex `AttributeError`. **ffmpeg 8.0.x's `aselect` keeps every frame** (fixed upstream after 8.0.1): there the
measurement read the whole raw and every second-voice gap 0.0 dB (winget's 8.0.1, 2026-09-27), so `voice-gain.py`
probes `aselect` once per run and, where it passes everything, cuts the kept ranges with `atrim` + `concat` instead.

- Premiere ✅ `uv run lanes/premiere/audio-polish.py projects/<job> --apply` (`--verify` reads it back): the measured Amplify + Hard Limiter as clip effects on every A1 clip — `premiere-pro` § Step 3. Every successful `--apply` records its gain, source (`named` or `measured: …`) and `--range` in `projects/<job>/premiere/audio-polish.json`, and a bare `--verify` holds each A1 clip to the latest record over it, so a named gain or per-section gains verify without being retyped and a mismatch names the record it was held to; `--verify --gain N` still means every clip at N. (The named gain is still a RUN.md deviation.)
- Resolve ✅ the same chain, baked into the media (its API has no limiter; 21.1's clip `AudioVolume` is a gain, not the chain): `workflows/normalize-sections.sh` takes the `voice-gain.py` gain and the −6 dBFS limiter to each source file, then `replace-clips.py` swaps the copies under the locked timeline — [`lanes/resolve/resolve-audio-polish/`](lanes/resolve/resolve-audio-polish/README.md). (Unified with the house numbers 2026-09-04, the user's call; before that the lane normalized to −16 LUFS / −1 dBFS.)
- CapCut ✅ baked into the SOURCE, the Resolve route: `workflows/normalize-sections.sh projects/<job>` (the measured gain into the house limiter, video stream-copied, its drift gate), then `replay <job> --media projects/<job>/audio-normalized` (a folder stands in for every raw by name; a file for a single-raw EDL). Proven on Windows 2026-09-27 (export −17.8 LUFS, peak −5.5) — `capcut` § Step 3
- Final Cut ✅ baked, the Resolve route: `workflows/normalize-sections.sh` → `audio-normalized/` (a section's raw with the section's own gain), and `replay.py` points the FCPXML at the copies, a mono clip given back the 6 dB Final Cut's mono split takes (`lanes/finalcut/lab-notes.md` § 16) (no FCPXML IDs captured yet for Final Cut's own audio FX). The Talking Head Explainer's second-voice lift: `replay.py` asks `voice-gain.py --second-voice` and writes it as volume keys on the dialogue, after the baked limiter (`--lift N` names it)
- chat-only — `splice.sh` already bakes the identical chain into the render

**The second-voice lift (the Talking Head Explainer's step-3 addendum; WHAT: its [README](presets/instagram/talking-head-explainer/README.md) § Audio).** Premiere ⚠️ `uv run lanes/premiere/audio-polish.py projects/<job> --lift auto` (after `--apply`; `voice-gain.py --second-voice` decides at the recorded gain, capped at −1 dBTP; the lift is a second Amplify AFTER the Hard Limiter, never Volume > Level, which Premiere runs before the limiter; a bare `--verify` reads the keys back, `--bounce` proves the level); Resolve / CapCut / chat-only ✋ by hand, a level ride AFTER the limiter on the `transcript/voices.json` spans. The Premiere lift is proven live on a stereo and a mono clip in a throwaway project, the ramps, their 20 ms lead and `--bounce`'s two-bounce proof included (2026-09-24); it becomes ✅ after its first real job. A timeline rebuild drops the lift: re-apply and prove it.

**Step 4 — Color grade (long-form and the Talking Head Explainer's camera footage).** Target (universal): the footage carries the look and **the
graphics carry none of it**, established before a single graphic is placed. The cube and the dial
values are the preset's: [`presets/youtube/default/README.md`](presets/youtube/default/README.md)
§ Grade. Only WHERE the separation lives is per-lane — a track on one app, a grouping on another.

- Premiere ✅ [`lanes/premiere/premiere-grading.md`](lanes/premiere/premiere-grading.md) — `grade-layer` builds the V2 adjustment layer, `grade-lut.py apply` writes the Look. Fully hands-off, except that a later screen-recording section needs the `GRADE` clip trimmed back to the camera footage (`premiere-grading.md` § 1).
- Resolve ⚠️ the SEPARATION needs no track shuffle (a color group covers only its members, so the footage joins it and the graphics track does not), and the house look goes on the group's post-clip node as ONE cube with the two Lumetri dials folded in (`fold-look.py`; measured within 1–2 / 255 of Lumetri on the Resolve lane test, 2026-09-25, ✅ after its first real job) — `davinci-resolve` § Step 4, mechanism playbook in [`lanes/resolve/resolve-grading/`](lanes/resolve/resolve-grading/README.md)
- CapCut ⛔ no LUT surface in the bridge. Hand-apply a filter in the app, or accept an ungraded cut and say so.
- Final Cut ✅ no adjustment layer exists: every footage clip carries Custom LUT → the folded house cube (`workflows/fold-look.py`, installed in `ProApps/Custom LUTs/`), the graphics lanes carry nothing; the LUT choice is a captured template (`lanes/finalcut/lab-notes.md` § 6). `replay.py` grades the plan's `graphics_scope` ranges, or `--grade-ranges` (camera footage only), else all of V1
- chat-only ⛔ the ffmpeg assemble lane has no grade stage.

**Step 5 — Graphics.** The graphics themselves are universal in the strongest sense: they are
rendered by HyperFrames into files (alpha ProRes 4444 for overlays, opaque mp4 for full-screens)
before any lane is involved. Plan with `graphics-plan`, build with `graphics-build`, converge with
`edit-review` — none of those three is lane-aware. Only PLACING a file and BAKING a footage move
are per-lane.

**The caption layer is part of this step (2026-09-04).** On the short-form presets the plan carries a `captions` cell and the preset's caption builder emits a straight-alpha ProRes 4444 (`hf-graphics/captions/renders/captions-alpha.mov`, no flat render needed); the lane's placer lays it on the top graphics track like any other overlay, spanning the whole cut (Premiere: V5, provisioned by `place-graphics.py`; Resolve: the highest video track, `AppendToTimeline` like any overlay; CapCut: `add-overlay` on the top layer, **premultiplied first** like every CapCut-bound alpha mov; chat-only: the last overlay in the assemble). Nothing burns captions after the render, on any lane. Long-form has no caption layer. **The short-form track map on Premiere:** V1 footage (the Talking Head Explainer's layout keys ride its Motion) · V2 grade (the Talking Head Explainer; empty on TikTok/raw) · V3 graphics · V4 overlaps and privacy patches · V5 captions.

- Premiere ✅ `uv run lanes/premiere/place-graphics.py projects/<job> --apply` (`--plan --write` first, which also syncs the plan; then `--verify` / `--remove <id>` / `--reconcile [--apply]` / `--sync-plan`) + the bridge `zoom` command for baked footage moves; 5c evidence: `uv run lanes/premiere/review-frames.py projects/<job> --round <N>` — `premiere-pro` § Step 5. A second deliverable: `--variant ad --sequence "<job> AD"` (its plan is `graphics-plan.ad.json`, else graphics-plan.json's `variants.ad` composed by the preset's `layout.py`; QA it with `workflows/graphics-qa-short.py projects/<job> --variant ad`). A still region blur over screen-recording media: `lanes/premiere/place-blur.py` (never a tracked patch on reframed, graded camera footage: the Talking Head Explainer's `captures.md` § 11 recipe).
- Resolve ✅ `uv run workflows/placement.py projects/<job> --write` (the rows, and the plan's half-frame snap sync), then `AppendToTimeline` with `clipInfo` from those rows + a Fusion Transform comp for moves (`TimelineItem` has no keyframe API) — `davinci-resolve` § Step 5
- CapCut ✅ `uv run workflows/placement.py projects/<job> --write`, then `capcut-bridge.py graphics <draft> <job>` lays those rows, premultiplying each alpha mov first (`add-overlay` + `keyframe` for a one-off) — ⚠️ **every CapCut-bound alpha mov is premultiplied**; Premiere and Resolve both want STRAIGHT alpha — `capcut` § Procedure 4-6
- chat-only ✅ ffmpeg overlay assemble — [`lanes/chat-only/incremental-graphics.md`](lanes/chat-only/incremental-graphics.md)
- Final Cut ✅ `uv run workflows/placement.py projects/<job> --write`, then `replay.py` lays `hf-graphics/placement.json` (each section's at its `timeline_offset`) as connected clips on lanes 1.., straight alpha as rendered, conform fit, a full-screen mp4's own sound muted; it refuses a stale `cut_rev` and an orphaned row as `place-graphics.py` does. The long-form opening zoom-out and every `push_in` beat are linear scale keys on the V1 clip matched to how Premiere renders its `zoom` (a 360° shutter: half a frame on, Final Cut's Zoom blur keyed to the move; `lanes/finalcut/lab-notes.md` § 15). ⚠️ organic only: no ad variant (`--variant` is Premiere-only)

**Step 5′ — Footage layout keys (the Talking Head Explainer).** Target (universal): the plan's `layout` map
(S split / T tight / W wide; F and O keep W's footage) as HOLD keys on the footage, one hard switch per
layout change, V1 never razored, a hand-set Motion never overwritten. The transforms are face-frame.json
`modes`, lane-neutral ([`layout.md`](presets/instagram/talking-head-explainer/layout.md) § 2). Run after the
replay and the grade, and again after any re-cut or V1 rebuild.

- Premiere ⚠️ `uv run lanes/premiere/layout-keys.py projects/<job> --apply`, then `--verify` (`--dry` is the offline default; `--variant ad --sequence "<job> AD"` for the second deliverable) — `premiere-pro` § Step 5. Proven live on a throwaway project (2026-09-24: every planned mode on its program grab, a re-apply writes nothing; `lanes/premiere/lab-notes.md` § UNPROVEN LIVE); becomes ✅ after its first real job.
- Resolve ⛔ no keyframe API on a timeline item: key a Fusion Transform per V1 clip from face-frame.json `modes` (unproven), or by hand. V1 pieces with static Pan/Tilt/Zoom reproduce the picture exactly (2026-09-25) but razor V1, a deviation to announce — `davinci-resolve` § Step 5.
- CapCut ✅ `uv run lanes/capcut/capcut-bridge.py layout <draft> <job> [--hand a-b:MODE=scale,cx,cy]`: the plan's spans (the preset's `layout.py`) and `face-frame.json` modes as static values or hold-key pairs on the main track. Proven on Windows 2026-09-27: every switch on the same frame as the Premiere final — `capcut` § Procedure 4
- chat-only ⚠️ `uv run lanes/chat-only/assemble.py projects/<job>`: the base cut is cut FRAME-exact at the layout edges, each span laid at its footage transform (a row's own `frame` over its mode's, through the preset's `layout.footage_spans()`), then every overlay and the caption layer on top — [`lanes/chat-only/incremental-graphics.md`](lanes/chat-only/incremental-graphics.md) § The assemble script. Proven on the Windows test job and on demo-project (macOS, 2026-09-27: flash-scan PASS, 0.0 % duplicate frames); becomes ✅ after its first real job.
- Final Cut ✅ `replay.py` reads the plan's `layout` map through face-frame.json `modes`: a clip with no switch inside it gets its mode as a static transform, a switch inside one a 1-frame linear key pair (Premiere's hold), V1 never razored

**Step 6 — SFX.** Target (universal): [`presets/youtube/default/sfx.md`](presets/youtube/default/sfx.md).
The plan is universal: `uv run workflows/sfx-plan.py projects/<job>` reads the placed graphics and
writes `hf-graphics/sfx-plan.{json,md}` on the first run (one row per sound: timeline time, library file, source
slice, clip level in dB, track). Only PLACING the rows is per-lane. Built 2026-09-03 from a hand-placed reference intro, validated on two jobs. **Every format (2026-09-04):** any
job whose graphics carry motion events gets its sounds. `sfx-plan.py` reads the map of the plan's
`preset`: the Talking Head Explainer ships its own ([`sfx.md`](presets/instagram/talking-head-explainer/sfx.md)
+ `sfx.json`), and its face-to-graphic cut-ins come from the plan's layout map; any other preset without
one reads the `youtube/default` map and the report says so. A `fade_out_s` event (the calling bed) reaches
the cut sheet, and its fade is laid BY HAND on every lane (⚠️: Premiere, a Constant Power transition on the
clip's tail).

- Premiere ✅ `uv run lanes/premiere/place-sfx.py projects/<job> --apply` (`--verify`, `--remove`, `--remove-extra`, `--diff`, `--adopt`; `--plan` / `--sequence` / `--until` for a variant cut): imports each file once into an `sfx` bin, provisions A2–A4 with QE `addTracks`, sets the item in/out to the slice, `overwriteClip` at the row's frame, writes Volume > Level, reads everything back; `--diff` reports the creator's hand edits (moved / removed / re-leveled / re-sliced / added) against the plan, which is how they become rules, and `--adopt` makes the creator's accepted timeline the plan — `premiere-pro` § Step 6
- Resolve ⚠️ Resolve 21.1+: audio-only `AppendToTimeline` places the rows and the clip `AudioVolume` property writes their levels (103 sounds proven on the Resolve lane test, 2026-09-25); no placer reads `sfx-plan.json` yet, so script it per job from the plan and read every level back — `davinci-resolve` § Step 6. Before 21.1: hand-place the rows from `hf-graphics/sfx-plan.md` and say so.
- CapCut ⛔ plan only: the universal plan is written; no audio-clip surface in the bridge. Hand-place its rows from `hf-graphics/sfx-plan.md` and say so.
- chat-only ⚠️ `uv run lanes/chat-only/mix-sfx.py projects/<job> <assemble.mp4> <out.mp4>`: every row of `sfx-plan.json` cut to its slice, levelled, its `fade_out_s` applied, delayed to its second and summed onto the dialogue (`amix normalize=0`), video copied, AAC 320k. Proven on the Windows test job and on demo-project (macOS: every single cue within 0.2 ms of its planned second).
- Final Cut ✅ `replay.py` lays `hf-graphics/sfx-plan.json` on connected audio lanes −1.. (plan track 1 = A2), each slice to the sample, cut where the next sound on its track starts (as Premiere's overwrite lays it), `level_db` as `adjust-volume`, `fade_out_s` as a fade, each file's embedded timecode honoured (a timecoded WAV written from `0s` is DROPPED on import: `lanes/finalcut/lab-notes.md` § 4)

**Step 7 — Review.** The creator's, on every lane. The run pauses here.

**Step 8 — Export.** Target (universal): one clip into `projects/<job>/outputs/<job>.final.mp4`,
**verified with ffprobe on the finished file** rather than the app's own reported settings. The
encode numbers are per format: long-form = [`presets/youtube/default/README.md`](presets/youtube/default/README.md)
§ Export; short-form = [`presets/instagram/talking-head-explainer/README.md`](presets/instagram/talking-head-explainer/README.md) § Export (the one home of
the Reels numbers; captions are already on the timeline as a step-5 overlay, so nothing burns after the render). Only the encoder
dialog that reaches them is per-lane. A lane whose own encoder cannot reach a number renders a ProRes master and encodes it
with `uv run workflows/deliver.py <master> <out.mp4> [--shorts]` (the numbers, lane-neutral; Final Cut always, Premiere
for the 4K Shorts file). A 4K vertical job has a second file, the 2160×3840 one for YouTube Shorts, in `outputs/shorts/`,
finalized with `--variant shorts`. Then
`./finalize.sh <job> --apply`, which is lane-agnostic (it only reads `outputs/`). Flags: `--keep-drafts` is the agent-safe form (promote plus export copy, nothing in `outputs/` deleted; the previous final is kept as `<job>.draft-prev.mp4`). `--variant NAME` handles a second deliverable in `outputs/NAME/`, e.g. the ad cut: deliverable `outputs/ad/<job>.ad.final.mp4`, export copy `<job>.ad.final.mp4`, family `<job>.ad*` / `<job>-ad*`, drafts such as `<job>.ad-draft-N.mp4` retired. An app export written onto `outputs/<job>.mp4` (the base cut's name) is never promoted: finalize warns and `--apply` refuses while it is the newest file, so export to `outputs/<job>-final.mp4` (or `outputs/ad/<job>.ad.mp4` for the ad).

- Premiere ✅ scripted on the creator's go: `uv run lanes/premiere/export.py projects/<job>` (`--draft` for a numbered draft finalize never promotes; `--sequence "<job> AD"` for a variant sequence → `outputs/<variant>/<job>.<variant>.mp4`; `--shorts` on a 2160×3840 sequence → `outputs/shorts/<job>.shorts.mp4`). It picks the FORMAT's preset from the sequence: portrait 1080×1920 / 2160×3840 at any rate → `instagram-1080x1920-h264-cbr14-23976.epr` (1080×1920; a piece past 2:48 gets its duration's lower bitrate, minted; a short is NEVER exported through a landscape preset, 2026-09-22); 3840×2160 AND 1920×1080 → `youtube-2160p-h264-cbr50.epr` (`-2997` at 29.97; a 1080 timeline goes up at 2160p, the preset README § Export), and above 30 fps `youtube-2160p-h264-cbr80.epr`; any other size refuses, naming `--preset`. Non-tracked presets are minted on first use by `lanes/premiere/premiere-templates/mint-export-preset.py` (only frame size and bitrate change; regenerable, gitignored). `--shorts` renders a ProRes 422 HQ master through the installed Premiere's own system preset and encodes it with `workflows/deliver.py`, because Premiere's H.264 caps the frame at 4096×2304 (a 2160×3840 preset wrote 1296×2304) and its HEVC exporter refuses `exportAsMediaDirect` (−1); the master is deleted once the file is proven. It runs `exportAsMediaDirect` with a timeout that outlives the export, waits until `lsof` shows the file closed and its size holds, then ffprobes it: moov, the preset's frame size, the sequence's rate, a frame count equal to the timeline's (the later of `seq.end` and the latest clip end), and ≤ 300 MB on the Reels preset. It exits non-zero on any failed check and keeps the file. It writes `outputs/<job>-final.mp4`, never `outputs/<job>.mp4`. AME stays banned. The run still pauses at step 7 until the creator says export — `premiere-pro` § Step 8. Proven live 2026-09-26 on every cell (16:9 at 23.976 / 29.97 / 59.94 and 1080→2160, 9:16 at 1080 and 4K, and the Shorts file).
- Resolve ✅ the native render queue — [`lanes/resolve/resolve-export.md`](lanes/resolve/resolve-export.md) (21.1: `VideoQuality` is the bitrate in kb/s and lands only with `MultiPassEncode`, `FormatWidth`/`Height` the preset's frame, so a 1080 long-form renders at 3840×2160 and a 4K vertical at 1080×1920; the Shorts file is a second render at 2160×3840). Proven live 2026-09-26.
- CapCut ⚠️ `uv run lanes/capcut/capcut-bridge.py export --to projects/<job>/outputs` drives the real dialog, then verifies the file against the open draft (H.264; the format's frame for the draft's canvas: 3840×2160 for any landscape draft, 1080×1920 for a vertical one, and 2160×3840 too for a 4K vertical's Shorts file; the draft's frame rate, the frame count, ≤ 300 MB at 1080×1920; exit non-zero on a miss, the file kept). On macOS the bridge does not set the dialog's encode settings yet: the creator sets them by hand (H.264, never the dialog's default HEVC; the format's resolution, which is 4K for any long-form and 1080p for any vertical file; the sequence rate; the format's bitrate); ⚠️ the 2026-09-26 numbers are not proven on a macOS CapCut export. On Windows the bridge sets them all (H.264; the timeline's own rate, `--fps` overrides, since another rate relabels its frames; a 50 Mbps master plus the Audio section's WAV of the mix) and `workflows/deliver.py` encodes the presets' numbers from the pair (High, CBR 14 vertical / 4K CBR 50 landscape, AAC 320k), then holds the file to the draft the same way: proven 2026-09-28 on a 29.97 vertical draft. Rename the file `<job>-final.mp4` so finalize promotes it — `capcut` § Procedure 8
- chat-only — the assemble render IS the deliverable
- Final Cut ✅ scripted on the creator's go: `uv run lanes/finalcut/export.py projects/<job>` has Final Cut render the project to a ProRes master through its own share sheet with no clicks (`share.py`: the save panel is completed from inside Final Cut, `lanes/finalcut/lab-notes.md` § 14), proves its frame count against the timeline, then encodes the format's deliverable with `workflows/deliver.py` (a 1080 landscape master goes up at 3840×2160, a 2160×3840 one gives the 1080×1920 file and, with `--shorts`, the Shorts file) and proves it — `final-cut-pro` § Procedure. Proven live 2026-09-26 on every cell. ⚠️ organic only: no ad variant (`--variant` is Premiere-only); `export.py --variant NAME` only files an export under `outputs/NAME/` for `finalize.sh --variant`

**Background music (conditional, opt-in).** WHAT (the bed level, the onset rule, the tail, the
opt-in ducking): the `background-music` skill. Only placing the track is per-lane.

- chat-only ✅ `mix-music.sh` on the near-final render (onset + tail built in)
- Premiere ✅ `uv run lanes/premiere/place-music.py projects/<job> --apply`, then `--bounce` for the proof (a music-only WAV bounce, no AME): the newest file in `audio/` onto A5, onset-trimmed, level written through the keyframe, 2 s tail — `premiere-pro` § Background music
- Resolve ⚠️ Resolve 21.1+: audio-only `AppendToTimeline` at the measured onset, `AudioVolume` = the preset's level, `SetFades` for the 2 s tail (proven on the Resolve lane test, 2026-09-25) — `davinci-resolve` § Step 6. Before 21.1, by hand as CapCut below.
- Final Cut ✅ `uv run workflows/music-onset.py <track> --write-plan projects/<job>` writes `hf-graphics/music-plan.json`, and `replay.py` reads it: one connected clip from 0 at `source_in`, `bed_db` held to a −96 dB key over the tail, to the end of the job's own timeline (its sections excluded unless the plan names an `end`)
- CapCut ✋ place the track on the music track (A5 on the `youtube/default` map) by hand: source in-point at the measured onset, the preset's level (house −20 dB; the Talking Head Explainer sets it from the track's own loudness, its README § Music), 2 s tail fade

## When you hit a ⛔ or a ⚠️

**An undocumented lane is not a blocked lane.** Every step's target is a set of numbers in the
preset, and the numbers are executable by hand in any editor. So:

1. **Do the step by hand** from the preset's spec. A footage move is two keyframes and an ease. A
   graphic is a file to drop on an overlay track.
2. **Say so out loud** in the run report, and record it in `projects/<job>/RUN.md` — same rule as a
   skipped step. A step done by hand on a lane that has no recipe is a normal outcome; a step
   quietly done differently from the preset is not.
3. **If it becomes routine, write the recipe into that app's skill** under its step heading, and
   flip this cell. Never write it into the preset.

**Never substitute another lane's mechanics.** The failure this file exists to prevent is a Resolve
job running the Premiere recipe: an adjustment layer where a color group belongs, Motion Scale 200
on a timeline that already auto-conformed, a premultiplied alpha mov on a lane that wants straight.
Each of those looks plausible and ships broken.

## Adding a lane

Three touchpoints, no new machinery:

1. A column in the matrix above, honest about what is ⛔ on day one.
2. A skill for the app, headed by the same step numbers as every other app skill, carrying only
   HOW.
3. Nothing in any preset. If a preset needs to change to support a new app, the split above has
   been broken somewhere. **One deliberate exception:**
   [`presets/youtube/vox-collage/premiere-lane.md`](presets/youtube/vox-collage/premiere-lane.md)
   is app mechanics kept inside its look's folder on purpose, so that look's inverted stack (grade
   ABOVE the graphics) cannot leak into a default job — 2026-08-31.
