---
name: after-effects
description: "Build animation, motion graphics and cards NATIVELY in Adobe After Effects by script: real layers, real keyframes, an editable .aep, rendered to ProRes and placed on the Premiere timeline. Use when the editor asks for a graphic or animation made in After Effects instead of the bundled HTML render engine, or supplies a reference .aep or reference clip to match. Triggers: do it in after effects, build this in AE, native after effects, animate this in AE, make an aep, match this aep, after effects graphics, check after effects."
---

# After Effects — graphics built natively, by script

**What this is.** The editor's default graphics engine renders HTML (`graphics-plan` → `graphics-build`).
This skill is the other route: the graphic is BUILT inside After Effects from an ExtendScript file, so the
result is a normal `.aep` an editor can open, retime and restyle by hand. When an editor asks for a graphic
in After Effects, this skill replaces the HyperFrames render for that graphic; the plan (what goes where,
when) and the placement on the timeline are unchanged, and RUN.md records that the graphic is an AE build.

**HOW only.** The look comes from the reference the editor gives (a `.aep`, a clip, a still) and from the
client's brand guideline. Copy the reference's easing and timing; never invent a house style here.

## 1. Before the first build on a machine

    bash lanes/aftereffects/check-ae.sh --fonts "<the job's font families, comma-separated>"

It reports, and fixes nothing: After Effects installed, **Settings > Scripting & Expressions > Allow
Scripts to Write Files and Access Network** ticked (the editor ticks it once, then restarts After
Effects), the script bridge answering, the job's fonts present. A font it cannot find on disk may be an
Adobe Fonts activation: confirm it in After Effects' font menu. On macOS the first bridge call raises one
system prompt, "allow … to control After Effects": the editor answers Allow.

After Effects must already be OPEN, with the project to build into. Nothing here launches it.

**Windows.** `ae-run.sh` and `check-ae.sh` carry a Windows path (`AfterFX.exe -r`, from Git Bash) written
from Adobe's documentation and **not yet run on a Windows machine**. On the first Windows build, run the
check, say plainly that this path is unproven, and report exactly what it printed.

## 2. Running a script

    bash lanes/aftereffects/ae-run.sh <script.jsx> [--timeout <seconds>]

One file per call. It prints `OK <last value>` (exit 0) or `ERROR <message> @line <n>` (exit 1); exit 3
means After Effects did not answer (a dialog is open in it: ask the editor to close it, never retry in a
loop), exit 4 that it is not running. The runner evaluates the file inside a try/catch, which is the whole
point: **an uncaught ExtendScript error raises a modal alert that blocks every later script, and it cannot
be dismissed from the shell.** Never send a script to After Effects any other way.

## 3. Writing a builder

One `build_<piece>.jsx` per graphic, kept in the job at `projects/<job>/ae/`, so the graphic can be rebuilt.

- **Load the kit first:** `$.evalFile(new File(ROOT + "/lanes/aftereffects/kit/build_lib.jsx"));` It gives
  the property shorthands (`P` `S` `O` `A` `R`), `K(prop, [[t, v], …], mode)` for keys shaped by an ease
  family (`lin`, `hold`, `s33`, `s66`, `card`, `out`, `expo`, `trim`), `pop`, `fadeIn`, `slideIn`,
  `overshoot`, `wordsIn` (word-by-word text animator), shape helpers (`rectG`, `ellG`, `pathG`, `addTrim`),
  `textLayer`, and `glow` / `blur` / `matte`. Its `FPS` is 30: set it to the sequence's rate before any key.
- **Paths come from the script's own location**, never a typed user folder:
  `var HERE = new File($.fileName).parent;` then walk up to the job and the project root. A builder that
  names `/Users/<someone>/…` runs on one machine only.
- **Build into the project that is open.** Add comps; never close, replace or save the editor's project
  without being asked. Before a builder touches a project that already holds the editor's work, copy the
  `.aep` beside itself first and say where the copy is.
- **Log to a file** (`projects/<job>/ae/build_<piece>.log`), rewritten at each stage, so a build that
  stops halfway says where. Set `file.lineFeed = "Unix"` or ExtendScript writes `\r` line ends.
- **Name every layer and comp** for what it is. The editor will open this file.

### Traps (each one cost a build)

- ExtendScript mis-parses mixed `||` / `&&` and nested ternaries: parenthesise every one.
- With the kit loaded, never name a variable `R`, `S`, `P`, `O`, `A` or `K`: they are its helpers.
- Shape layers: a group added LATER draws UNDER the earlier ones (add the details first, the body last).
  A reference to a group or property goes stale once another group is added to the same layer: fetch it
  again by name.
- `comp.saveFrameToPng()` returns before the file exists (it lands a few seconds later): poll for the
  file, and never delete a temporary layer on the assumption that the PNG is already written.
- A third-party effect the reference uses may not load on this machine (After Effects lists them at
  launch). Rebuild it from native effects and say so: the kit's `glow()` is two stacked native Glows
  standing in for Deep Glow.
- `node lanes/premiere/premiere-bridge.mjs es --timeout N` executes but can print nothing: read the state
  back with a second call instead of trusting the silence.

## 4. Check, render, place

1. **Look before rendering.** Save a frame per phase (`saveFrameToPng`, polled) into
   `projects/<job>/review/` and read them against the reference.
2. **Render from After Effects' render queue to ProRes:** output module template `High Quality` for an
   opaque piece (ProRes 422), `High Quality with Alpha` for an overlay (ProRes 4444), audio off, into
   `projects/<job>/ae/renders/`. There is no shipped render script yet: add the comp to the queue from a
   builder, apply the template, render, and prove the file with `ffprobe` (size, rate, frame count, and an
   alpha pixel format on an overlay).
3. **A re-render is a NEW file name** (`_v2`, `_v3`), a fresh import and a swap on the timeline: Premiere
   keeps showing the old pixels of a file replaced under the same name.
4. **Place it on the Premiere timeline** through the `premiere-pro` skill, like any other rendered
   graphic, interpreted at the sequence's frame rate so one source frame is one sequence frame. A scripted
   Premiere edit is not in the undo stack: back the `.prproj` up first.
