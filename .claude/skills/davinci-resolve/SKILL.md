---
name: davinci-resolve
description: "The DaVinci Resolve finishing lane, counterpart to premiere-pro for Resolve users. Replays the rough-cut EDL (cuts.json) as separate trimmable clips on a real Resolve timeline via the davinci-resolve MCP, then keeps working through Resolve's official scripting API: silence-ripple auto cuts, AI subtitles + transcript-based cut proposals, Fusion node graphs, custom DCTL color shaders, in-app Python, vision metadata, native renders. Triggers: send to resolve, open in resolve, finish in resolve, davinci, edit this in resolve, resolve timeline."
---

# To DaVinci Resolve: Rough Cut Handoff + API Editing

The Resolve counterpart to the `premiere-pro` skill. Same job: get the cut **onto a Resolve timeline as separate, trimmable clips** by replaying the EDL (`transcript/cuts.json`) against the raw footage, then keep working there. Unlike Premiere there is **no bridge panel**: the `davinci-resolve` MCP talks to Resolve's official first-party scripting API in-process, which reaches four apps in one (Edit, Fusion, Color, Fairlight). Resolve must be RUNNING; `resolve_control launch` (community engine, headless supported) or `launch_resolve` (official engine) starts it; several AI features are GUI-only, noted below. Two engines answer to that MCP name: § Wiring says which one this machine has, § Two engines maps every call between them.

## 🔒 STEP INDEX — what this lane does at each pipeline step

**This skill carries HOW, never WHAT.** The look, the numbers and the definition of done for every
step live in the format's preset ([`presets/youtube/default/README.md`](../../../presets/youtube/default/README.md)
for long-form). Read the preset for the target, then the row below for the mechanics.
Cross-lane status: [`LANES.md`](../../../LANES.md).

| # | Step | On this lane | Where |
|---|------|--------------|-------|
| 1 | Intake | — universal, no Resolve involvement | CLAUDE.md § Pipeline |
| 2 | Rough cut → replay | ✅ scripted — ONE call rebuilds the EDL as trimmable clips | § Step 2 below |
| 3 | Audio polish | ✅ scripted — ffmpeg per source file + `ReplaceClip` (the API has no limiter and no FX insertion; 21.1 adds a clip level and fades, nothing more) | § Step 3 below → [`lanes/resolve/resolve-audio-polish/`](../../../lanes/resolve/resolve-audio-polish/README.md) (the bake: `workflows/normalize-sections.sh`) |
| 4 | Color grade | ⚠️ colour group + the house look folded into ONE `.cube`, frame-measured against Lumetri on the lane test (2026-09-25); ✅ after its first real job — read the section before assuming | § Step 4 below → [`lanes/resolve/resolve-grading/`](../../../lanes/resolve/resolve-grading/README.md) |
| 5 | Graphics | ✅ scripted — `AppendToTimeline` + Fusion Transform for moves (the Talking Head Explainer's layout keys: ⛔, § Step 5) | § Step 5 below |
| 6 | SFX | ⚠️ Resolve 21.1+: placement + level scripted (`AppendToTimeline` audio-only + `AudioVolume`), proven on the lane test; no placer reads `sfx-plan.json` yet | § Step 6 below · [`LANES.md`](../../../LANES.md) § step 6 |
| 7 | Review | ✋ the creator's. The run pauses here. | — |
| 8 | Export | ✅ scripted — the native render queue | § Step 8 below → [`lanes/resolve/resolve-export.md`](../../../lanes/resolve/resolve-export.md) |

⚠️ **Never carry a Premiere habit across.** The three that have actually shipped damage here:
hand-scaling a 1080 asset on a 4K timeline (Resolve already conformed it — Motion Scale 200 doubles
it to 400% and crops), premultiplying an alpha mov (Resolve wants STRAIGHT and auto-detects it), and
reaching for an adjustment layer (a color group is this lane's equivalent and needs no track shuffle).

## Wiring

- **Two engines answer to the name `davinci-resolve`, one per machine: read `.mcp.json` to know which.** Its `davinci-resolve` command is `…/Contents/Applications/ResolveMCP` = the **official** engine (Studio 21.1+: wired by hand on macOS, entry below, the author's own setup since 2026-09-25; on Windows `setup-resolve.sh` wires `ResolveMCP.exe` itself when it detects Studio 21.1+, 2026-09-27), or the vendored venv python = the **community** engine (what `setup-resolve.sh` installs everywhere else, the fallback it keeps installed on Windows Studio, and the only route for the free edition; `--community` or `VE_RESOLVE_MCP=community` forces it). Which call is which on each engine: § Two engines.
- Community engine = pinned clone at `vendor/davinci-resolve-mcp/` ([samuelgursky/davinci-resolve-mcp](https://github.com/samuelgursky/davinci-resolve-mcp) v2.72.0, commit `a9fd831`, update checks off; bump the pin deliberately). Compound server (`src/server.py`, 34 grouped tools; `--full` = 341 granular). Venv built by `python -m venv` plus `pip` (`mcp[cli]>=1.29,<2`, then `requirements.txt`), then `install.py --clients manual` (it finds the venv ready and skips its own pip, which Windows Smart App Control blocked); Python 3.10+.
- Fresh CLIENT machine: `./setup-resolve.sh` (ships at the root of the client package) clones the pin, builds the venv, and writes the `.mcp.json` entry with the three env vars (`RESOLVE_SCRIPT_API` / `RESOLVE_SCRIPT_LIB` / `PYTHONPATH`). (The author's working repo has no `./setup-resolve.sh` at its root; it lives in `packaging/overlay/`.)
- Resolve side: nothing to configure in the normal case: **External scripting = Local is Resolve's shipped default** (verified on multiple installs, 2026-08-13; don't tell users to go set it). Only if the MCP can't connect after a Claude Code restart, verify Preferences → System → General → External scripting = Local as a troubleshooting step. External scripting is a Studio feature; **the free edition runs through the MCP's in-app bridge, and `setup-resolve.sh` decides that at install time (2026-09-07):** it detects the edition, runs the vendored `scripts/install_resolve_bridge.py` (needs `PYTHONUTF8=1` on Windows; the script exports it), seeds the project root into the bridge's allow-lists, and bakes `DAVINCI_RESOLVE_BRIDGE=1` into the venv as a `.pth` (a flag added to `.mcp.json`'s `env` mid-session never reaches a server Claude Code respawns from its session-start snapshot). On a free-edition machine (the `.mcp.json` entry carries that flag) the user runs **Workspace → Scripts → resolve_bridge** after every Resolve start, with a project open; `BRIDGE_UNAVAILABLE` means it isn't running, and retrying cannot start it. The entry also caps every call at 10 minutes (`"timeout": 600000`), because a free edition wired the Studio way hung its first call for Claude Code's 30-minute idle timeout.
- **Official engine = Resolve 21.1's `ResolveMCP`, wired as the `davinci-resolve` entry** in `.mcp.json` (macOS command = `/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Applications/ResolveMCP`, no args: the same command Resolve's File > Setup AI Assistants writes into `~/.claude.json`), plus `"enabledMcpjsonServers": ["davinci-resolve"]` in `.claude/settings.local.json` so the terminal CLI does not hold it pending; restart Claude Code after. Studio only. What it can and cannot do: [`lanes/resolve/lab-notes.md`](../../../lanes/resolve/lab-notes.md).
- Second server, NOT wired: `resolve-advanced/` (18 Node tools) edits `.drp`/`.drt`/`.drx` with Resolve closed. Its `.prproj` conform bridge extracted 0 editorial events from a real Premiere project, so don't rely on it.

## Two engines: the call map

Every recipe below is the RAW scripting API; the engines differ only in how a script reaches it.
**Community** wraps many calls in named tools; **official** (`ResolveMCP`, Studio 21.1+) runs the raw
calls in `run_script`. Proven end to end on the official engine by the Resolve lane test of 2026-09-25
(a delivered short rebuilt, 42.9 dB mean PSNR against its Premiere master; record in
[`lanes/resolve/lab-notes.md`](../../../lanes/resolve/lab-notes.md)).

| Operation | Community engine | Official engine |
|---|---|---|
| start Resolve | `resolve_control launch` | `launch_resolve` · `get_resolve_status` |
| arbitrary API Python | `script_plugin run_inline` (`resolve`/`project`/`fusion` bound) | `run_script` (`resolve`/`project` bound; no `os`/`open`) · `run_script_unsafe` (full OS access) |
| replay the EDL | `media_pool create_timeline_from_clips` | `mp.CreateEmptyTimeline` + `mp.AppendToTimeline([clipInfo…])` (§ Step 2) |
| read items back | `timeline get_items_in_track` | `tl.GetItemListInTrack(kind, i)` → `GetStart`/`GetDuration`/`GetLeftOffset` |
| save | `project_manager save` (can return false while it worked) | `resolve.GetProjectManager().SaveProject()` |
| DCTL / LUT files | `dctl install` → `graph set_lut` (staging trap, grading README) | `update_dctl` (compiles first) · `generate_lut` · then `SetLUT(1, 'MCP/<file>')` |
| render | `render prepare_render_job` / `render start` | `SetRenderSettings` + `AddRenderJob` + `StartRendering`, poll `GetRenderJobStatus` (§ Step 8) |
| API reference | the wrapper's own tool docs | `search_scripting_api` · `get_scripting_api` · `get_scripting_docs` · `get_whats_new` |

**Windows (2026-09-27): trust no launch call's word, prove it.** On the first Windows run `resolve_control launch` answered "could not be started" and `launch_resolve` answered "running" with no Resolve.exe up (three orphaned ResolveMCP.exe servers were resident); on the re-test `launch_resolve` started Resolve and answered truly. Either way: call `launch_resolve` (or start `C:\Program Files\Blackmagic Design\DaVinci Resolve\Resolve.exe` directly, PowerShell `Start-Process`), then poll `get_resolve_status` until it reads `running: true` (about 20-25 s on the test PC) before the first call, and confirm Resolve.exe in `tasklist`. The 'Running DaVinci Resolve' line in `%APPDATA%\Blackmagic Design\DaVinci Resolve\Support\logs\davinci_resolve.log` lands about 2 s after the start, well before scripting answers: it proves the launch, not readiness.

Official-engine rules, each learned on the proof job:
- **60 s hard cap per call** (`timeout` max 60): split a build into per-track scripts; start a render in one call and poll it in the next.
- `run_script` cannot read files, so **embed job data as a JSON literal** in the script (a 180-item plan ran as one 40 KB script), or read it in `run_script_unsafe`. Pass Resolve ABSOLUTE paths.
- Look media pool items up by `GetClipProperty('File Path')`, never by name.
- In-process readbacks (`GetLUT`, `GetProperty`, `GetLeftOffset`) are Resolve's own state, not a wrapper record; the verify-from-a-render rules below still stand.

## Project setup: MATCH THE SOURCE FPS, and never ask for a click

**Step zero of every Resolve job: `ffprobe` the raw and read its real frame rate.** The project must match the footage: 24 fps source gets a 24 fps project, 30 gets 30. Do not assume, and do not default to whatever the last job used.

**After import, put every clip on the raw's NOMINAL rate: `SetClipProperty('FPS', '29.97')` (the iPhone VFR trap, measured 2026-08-13; fixed 2026-09-27).** iPhone `.MOV` footage is variable frame rate: ffprobe's `r_frame_rate` reports `30000/1001` (29.97) while Resolve ingests the same clip at **30.00 native** (macOS and Windows, 21.1). Built at 30, a Resolve finish could never share a frame grid with the 29.97 plan, renders and Premiere lane: a 195-frame graphic ended a frame before its V1 cut (the Windows lane test). So: ffprobe the raw, clone the template at THAT rate (`1080p2997.drp` for a 30000/1001 take), import, and on every clip whose `GetClipProperty('FPS')` differs from it by more than 0.01 (Resolve reports a float: a 23.976 camera clip is already on its rate), `SetClipProperty('FPS', '<nominal>')` and read it back BEFORE the clip goes on a timeline; then the EDL seconds→source frames math runs at the nominal rate. Proven on macOS 21.1 (IMG_0036, r 30000/1001, ingested 30.0): the property took and read back 29.97 with its 322 frames unchanged, and a timeline from the same EDL rendered all 159 frames onto exactly the raw frames the Premiere export shows (each mapped back to its source frame). If a build ever refuses the property, the plan for a Resolve finish carries Resolve's rate instead (render the graphics at it). **Read `GetClipProperty('FPS')` BEFORE setting it and keep it: that NATIVE rate is the picture's time base for good (the Windows re-test, 2026-09-27).** After the property changes, Resolve plays the clip at the nominal rate and lays its SOUND by the new rate's time, but still decodes source frame f as the picture at f / native (30.0 on an iPhone take: its 4501 frames are 150.015 s x 30). So a V1 laid from `round(start x 29.97)` showed the picture 1 frame early 34 s into a 150 s take and 3-4 frames early at 127 s, behind its own sound, which read 0.0 ms against the timestamp-exact splice; the Mac proof's 10.7 s clip drifts under a third of a frame and never showed it. The replay lays V1 from `round(start x native)` and A1 from `round(start x nominal)`, and runs each V1 item at native/nominal speed (100.1%) so a long segment does not slide within itself (§ Step 2's recipe): measured against the splice, lag 0 in 5 of 7 segments and one frame at most on Windows, and on macOS 28 of 42 segments exact and none past one frame, a 60 s segment included, sound exact. A clip already set with no native rate recorded: re-import it. **Diagnostic signature:** a uniform ÷1.001 (or ×1.001) pattern across every item's duration/left-offset readback means the fps model is wrong: rebuild, never nudge individual frames. (`splice.sh` conforms the flat render to the same nominal grid, `fps=` before each trim.)

**Then clone a template `.drp` at that fps. Do NOT use `create_project` + `set_setting`.** A new project defaults to 3840x2160 / **24 fps**, and `timelinePlaybackFrameRate` (a *separate* setting from `timelineFrameRate`) cannot be written by the API at all (re-tested on 21.1, 2026-09-25: `SetSetting` still returns False and it reads back 24). A 30 fps timeline left playing back at 24 produces **chopped, glitchy audio**. Importing a `.drp` restores fps + resolution wholesale, bypassing `SetSetting` entirely (verified 2026-08-04).

The block below runs as-is in `run_script` on the official engine (or `script_plugin run_inline` on the community one); give `ImportProject` an ABSOLUTE path. **Never `SaveProject()` while the current project is "Untitled Project"**: Resolve opens its Save Current Project name dialog and the script hangs to its cap (2026-09-25). Check `GetName()` first and skip the save for an untitled one. Resolution is writable after the import (`timelineResolutionWidth` / `Height` → a 2160x3840 vertical read back exact).

```python
pm = resolve.GetProjectManager()
cur = pm.GetCurrentProject()
if cur and cur.GetName() != 'Untitled Project':
    pm.SaveProject()                                 # outgoing project, or a GUI modal blocks everything
pm.ImportProject('<abs>/lanes/resolve/resolve-templates/1080p30.drp', '<Project Name>')
pm.LoadProject('<Project Name>')
p = pm.GetCurrentProject(); mp = p.GetMediaPool(); root = mp.GetRootFolder()
mp.SetCurrentFolder(root)
tls = [p.GetTimelineByIndex(i) for i in range(1, p.GetTimelineCount()+1)]
if tls: mp.DeleteTimelines(tls)                      # strip inherited content
if root.GetClipList(): mp.DeleteClips(root.GetClipList())
```

**Always read `timelinePlaybackFrameRate` AND `timelineFrameRate` back** before building the timeline.

**One template per frame rate: a template cannot be re-pitched** (once a project carries a playback fps, `timelineFrameRate` goes read-only too). But minting a template at ANY rate is **fully scripted, zero clicks** (2026-08-04) — paths are taken as given, so pass them repo-relative:

```bash
uv run lanes/resolve/resolve-templates/mint-template.py \
  lanes/resolve/resolve-templates/1080p30.drp <fps> \
  lanes/resolve/resolve-templates/<out>.drp
```

Available now: 1080p30, 1080p2997 (both in [`lanes/resolve/resolve-templates/`](../../../lanes/resolve/resolve-templates/) — how the settings blob is patched, the verified rate-enum table and the anonymity check live in its README). Always import + read back both fps keys before trusting a fresh mint (a 23.976 mint read back 23.976 / 23.976 on 21.1, 2026-09-25). 24 fps needs no template (a stock `create_project` is already 24/24, just set the resolution).

## Vertical (9:16) framing

A clip dropped on a 1080×1920 timeline arrives LETTERBOXED (project Input Scaling defaults to fit, and that setting is UI-only from the API). The fix is one property write, resolution-agnostic, no math:

```
item.SetProperty('Scaling', 3)   # 3 = scale full frame with crop = FILL at Zoom 1.0
```

Values: 0 = fit, 1 = center-crop-at-native, 2 = fit, 3 = FILL. Zoom math (`tl_h / (tl_w * src_h / src_w)`) is quality-identical (Resolve concatenates sizing transforms and resamples once), so prefer Scaling=3 for simplicity. 16:9 → 9:16 is a ~1.78x upscale from a 1080p source, inherent to the crop; shoot 4K for vertical (downscale instead). `SetClipProperty('Super Scale', N)` takes **bare ints only** (1=off, 2=2x, 3=3x); every string form returns False.

**Mixed-resolution assets: let Resolve conform, NEVER hand-scale (2026-08-05).** The project setting `timelineInputResMismatchBehavior` defaults to `scaleToFit`, so a 1080p asset (title card, alpha overlay, older footage) already fills a 4K frame on drop. The Premiere habit (Motion Scale 200) doubles that to 400% and crops the middle out, plausibly enough to ship: a title card lost its first and last letters. Leave `ZoomX`/`ZoomY` at 1.0, check the setting before scaling anything, and verify with a real render (clip-level readback reports whatever zoom it was told and hides the crop). Upside of the same conform: mixed fps lands frame-for-frame (a 29.97 clip on a 30.000 timeline keeps its frame count), so frame-indexed graphics and same-rate overlays stay in sync with no re-render.

## Step 2 — EDL replay: one call

Run the splice `RENDER=0` first (same rule as the Premiere path: never render the flat cut for an app finish). Then the whole rebuild is a single call:

1. **Create the project from a matching template (see § Project setup above). Never `create_project` + `set_setting`.** Match the template to the raw's `r_frame_rate`, and after import put any clip Resolve ingested at another rate (every iPhone take: 30.0 for 29.97) back on it with `SetClipProperty('FPS', …)` (trap in § Project setup above).
2. **Community:** `media_pool create_timeline_from_clips` with `clip_infos` = `{clip_id, start_frame, end_frame, record_frame}` in **SOURCE frames at the clip's `GetClipProperty('FPS')`**, the nominal rate once § Project setup has set it (the iPhone VFR trap). `end_frame` is **EXCLUSIVE** (dur = end − start; matched a real EDL 8/8 to the frame). `record_frame` is timeline-relative. Linked audio comes along automatically.
   **Official** (`run_script`, the EDL embedded as a JSON literal): the same frames, but `recordFrame` is **ABSOLUTE** (`tl.GetStartFrame()` + the timeline-relative frame) and `mediaType` picks the half: `1` video-only, `2` audio-only, omitted = linked A/V. A J-cut (audio edit point ≠ video edit point) therefore replays as separate video-only and audio-only items. Proven 2026-09-25: 22 V1 + 22 A1 (a J-cut included) + 136 more items in one call per track, 180/180 exact on start, duration and source in.
   ```python
   mp = project.GetMediaPool()
   def walk(f): return (f.GetClipList() or []) + [c for s in (f.GetSubFolderList() or []) for c in walk(s)]
   by = {c.GetClipProperty('File Path'): c for c in walk(mp.GetRootFolder())}   # root too: ImportMedia lands in the current folder, root after § Project setup
   tl = mp.CreateEmptyTimeline('<name>'); project.SetCurrentTimeline(tl)
   while tl.GetTrackCount('audio') < 2: tl.AddTrack('audio', 'stereo')
   T0 = tl.GetStartFrame()
   # SEGS: src0/src1 = round(seconds x NOMINAL), the sound and every duration; v0 = round(start x NATIVE), NATIVE = the
   # FPS Resolve reported for the clip BEFORE SetClipProperty('FPS') (§ Project setup): the picture stays on that time base.
   # Each SEGS row also carries 'native' and 'nominal', that clip's two rates as floats (30.0 and 30000/1001 on an iPhone take)
   mp.AppendToTimeline([{'mediaPoolItem': by[s['path']], 'startFrame': s['v0'], 'endFrame': s['v0'] + s['src1'] - s['src0'],
                         'recordFrame': T0 + s['rec'], 'trackIndex': 1, 'mediaType': 1} for s in SEGS])   # V1
   mp.AppendToTimeline([{'mediaPoolItem': by[s['path']], 'startFrame': s['src0'], 'endFrame': s['src1'],
                         'recordFrame': T0 + s['rec'], 'trackIndex': 1, 'mediaType': 2} for s in SEGS])   # A1
   # A clip whose NATIVE rate differs from its NOMINAL one plays one native frame per timeline frame, 0.1% slow against
   # its sound: each V1 item runs at native/nominal speed (100.1%) so a long segment never slides. Without ripple the
   # item keeps its duration and reads further into the source; nearest-frame retime, never a blend.
   for vi, s in zip(sorted(tl.GetItemListInTrack('video', 1), key=lambda i: i.GetStart()), SEGS):
       if abs(s['native'] - s['nominal']) > 0.01:   # never ==: a 23.976 camera clip reads 23.976 against 24000/1001
           vi.SetProperty('RetimeProcess', resolve.RETIME_NEAREST)
           assert vi.SetSpeed({'Percentage': 100.0 * s['native'] / s['nominal'], 'RippleTimeline': False})
   ```
   On a clip Resolve ingested at its nominal rate, `v0 == src0` and no speed is set: the two calls lay the same frames.
   **The speed step is what holds a LONG segment (macOS 21.1, 2026-09-27).** Without it the picture of one continuous
   segment slides a frame behind its sound about every 33 s (0 → −2 frames across a 60 s segment, on a 29.977 and a
   30.004 average take alike), because frame f is the picture at f / native while the timeline steps at the nominal rate.
   With it: every V1 duration exact (42 of 42 segments, and the 60 s one), no gap frame, the picture within one frame of
   the splice on every segment (28 of 42 exact; the rest the beat between the 30 and 29.97 grids), the sound exact.
   Leaving the clip at its native rate instead is NOT an option: Resolve rounds each segment down, 38 of 42 came out a
   frame short (a black frame at nearly every cut). `SetSpeed` is the official engine's (`run_script`); on the
   community engine, run the same lines as in-app Python.
3. Verify with a readback (community `timeline get_items_in_track`; official `tl.GetItemListInTrack` → `GetStart() - T0`, `GetDuration()`, `GetLeftOffset()`): starts sit on the timeline's start-frame offset (108000 = 01:00:00:00 at 30 fps, 86400 at 24 and 23.976).
   **When clip fps ≠ timeline fps, `GetLeftOffset()` reads back in CONFORMED (timeline) frames while `start_frame` is consumed as NATIVE source frames**: a 29.97 clip on a 30 fps timeline reads back `native × 1.001`, which looks like a growing drift (up to 4 frames over 2.5 min) and is NOT one. Durations and `record_frame` read back exact, so verify those and don't "fix" the offsets. Resolve conforms by TIME, not 1:1 frames (measured: a 4612-native-frame span occupies 4616 timeline frames at 30 fps); that one probe settles the domain question in a single call.
4. Save **immediately** (community `project_manager save`; official `pm.SaveProject()` in the same script). GUI mode + unsaved project = a modal no script can dismiss. (The community `save` wrapper can return false while the raw call works; verify via `run_inline`, where `pm.SaveProject()` returns True.)

### Do we still need WhisperX?

Yes, for the rough cut. Measured on the same clip: Resolve gives phrase-level cues (median ~1.9s / 6 words, timing only at cue edges, ~6x fewer anchors than WhisperX's per-word timestamps), and cue starts sit inside the very error band `refine-cuts.py` exists to fix. Keep the locked WhisperX rough-cut for cutting; Resolve's transcription is useful for long-form CC and machines without the venv.

## Step 3 — audio polish: ffmpeg on the source files + `ReplaceClip`, NOT the API

**The scripting API cannot build the house chain: no limiter, no EQ, no track fader, no bus access, no FX insertion, on any version to date (don't re-litigate that half).** What 21.1 DID add is a clip-level `AudioVolume` (−100..+30 dB), `AudioPan` and `SetFades`/`GetFades` (frames), used for SFX and music levels (§ Step 6), never for the voice chain: a gain with no limiter behind it clips. (The community wrapper's `get_audio`/`set_audio` query keys Resolve doesn't have.) So this lane polishes the SOURCE FILES with ffmpeg and swaps the media under the locked timeline, rather than applying effects. The four independent corroborations and the ruled-out routes: the engineering archive.

**Run it immediately after the replay verifies — pipeline step 3 (2026-08-28), never per-section during the cut.** The pass is [`lanes/resolve/resolve-audio-polish/`](../../../lanes/resolve/resolve-audio-polish/README.md) (`workflows/normalize-sections.sh` then `replace-clips.py`), validated 2026-08-06 on 9 sections / 210 clips with zero clips moved. **Read that README before running one** — the chain, the drift gate and the `ReplaceClip` traps all live there. It swaps media, not clips, so every later hand edit rides on it; only a timeline REBUILD from re-imported raw needs the swap re-run.

`replace-clips.py` runs unchanged on both engines: community `script_plugin run_inline` as its docstring shows; official `run_script_unsafe` (it needs the filesystem) with `import io; JOB='<abs job>'; exec(io.open('<abs>/lanes/resolve/resolve-audio-polish/replace-clips.py', encoding='utf-8').read())` (proven 2026-09-25: every track UNCHANGED). On a timeline built fresh, importing the normalized copies AS the footage media before the replay is equivalent and skips the swap (the proof job did that).

Normalized files go in `audio/` or `audio-normalized/`, never `raw/`: `transcribe.sh` globs `raw/*.mov` and would transcribe them as extra clips on a `--force` re-run.

**To READ an audio pass someone made by hand, bounce and measure; the mix state is unreadable.** Before 21.1 `get_audio`/`get_property` returned nulls on audio items; 21.1's `GetProperty('AudioVolume')` reads back a clip's level, but nothing reads a Fairlight FX chain, a fader or a bus, and a `.drp` export hides mix state in opaque zstd blobs (per-item `EffectFiltersBA` are byte-identical defaults regardless of the mix). Instead render (community `render prepare_render_job`; official the § Step 8 recipe at a small size) a throwaway 480x270 mp4 (a 55s timeline rendered in 2.2s) and `volumedetect` each segment against the same source range in the raw: a uniform peak ceiling across every segment plus a gain delta that shrinks as the source gets louder = gain-into-limiter, and the numbers tell you the settings. Gotcha: `ExportVideo: false` produces a job with an empty VideoCodec and `StartRendering` then just returns False: render tiny video, not none. Clean up with `delete_all_jobs` (official `project.DeleteAllRenderJobs()`) + re-set format/codec (`GetRenderSettings` does not exist in the API, 21.1 stub included, so nothing can snapshot "before"; track what you changed yourself).

## Step 4 — color grade (mechanism validated 2026-08-06: 9 clips, one shader; the house look folded 2026-09-25)

**The mechanics are [`lanes/resolve/resolve-grading/`](../../../lanes/resolve/resolve-grading/README.md) — how a colour group is built and assigned, the DCTL dialect that compiles, the `install` vs `set_lut` staging trap, the teardown sweep, plus a reference shader and a numpy previewer. Read it before any grading work on this lane.** What follows is only what the preset asks for and which half of it is proven here.

### What the preset asks for, and what is proven here

**The universal contract is the SEPARATION: the footage carries the look, the graphics carry none of
it, established before a single graphic is placed.** On this lane that half is free and validated —
a colour group covers only its members. **The other half, the house look, is reached by FOLDING it
into one node** (validated once, 2026-09-25).

| Half of the step | Status here |
|---|---|
| Footage graded, graphics untouched | ✅ a color group covers only its members. Join the footage clips; leave the graphics track out. No track shuffle, no adjustment layer, no reordering. |
| A shared look across every footage clip | ✅ one node on the group's **post-clip** graph, `SetLUT(1, …)`. Proven with a DCTL (2026-08-06) and with a generated `.cube` (2026-09-25). |
| Autumn + Look Intensity 80 + Creative Saturation 120 | ⚠️ **folded into ONE `.cube`** (proven on the lane test; ✅ after its first real job): `out = sat(lerp(x, Autumn(x), 0.80), 1.20)`, saturation about Rec709 luma, clamped. Lumetri's dials have no API equivalent (`Graph` exposes LUT, label, enable and cache mode, no colour parameters), so the blend and the lift are baked into the cube. Measured against the Premiere master of the same cut: footage mean RGB within 1–2 / 255 on four frames. |

**How to build and apply the folded cube, on either engine: [`lanes/resolve/resolve-grading/`](../../../lanes/resolve/resolve-grading/README.md#the-house-look-folded-into-one-cube).** `uv run workflows/fold-look.py assets/luts/rec709/Autumn-Rec709.cube --install autumn80-sat120` writes it straight
into Resolve's master `LUT/MCP/` for the OS (the Windows folder is unverified) and prints the path `SetLUT` takes; then, in-process (official `run_script`, community `run_inline`):

```python
project.RefreshLUTList()
grp = project.AddColorGroup('Footage Look')
for it in tl.GetItemListInTrack('video', 1): it.AssignToColorGroup(grp)
grp.GetPostClipNodeGraph().SetLUT(1, 'MCP/autumn80-sat120.cube')    # GetLUT(1) reads it back
```

The fallback if a fold ever misbehaves: **cube on the node, dials by hand** in the Color page, once,
then saved as a group grade.

**Whichever route: verify with a real render, and say in the run report that the grade was
established by a different mechanism than the preset's Premiere recipe** ("Autumn folded at 0.80 / 1.20,
measured"). Never report "Autumn at 80/120 applied" on this lane unless you measured a frame — the
numbers are Lumetri's, and a `.cube` on a Resolve node is not the same signal chain.

⚠️ **A readback proves nothing on its own: verify from a real render.** On the community engine
`graph get_lut` reports the wrapper's own record, not Resolve's state (it returned a LUT name for a
node where in-process `GetLUT(1)` read `None`, and the matching `set_lut` had also reported success).
The official engine's `GetLUT(1)` is Resolve's own answer, but a node that compile-fails still passes
the picture through ungraded.

## Step 5 — graphics on the timeline (validated 2026-08-05, 9 overlays on V2)

On a short-form preset the caption layer (`hf-graphics/captions/renders/captions-alpha.mov`, the
plan's `captions` cell) is one more straight-alpha overlay: append it on the highest video track,
spanning the whole cut, above every card ([`LANES.md`](../../../LANES.md) § step 5).

- **HyperFrames alpha ProRes 4444 drops in with ZERO alpha config: Resolve auto-detects `Alpha mode: Straight`**, exactly what hyperframes writes. **NEVER premultiply a Resolve-bound render.** Premultiply is the CapCut lane's fix; here it would blow out every soft pixel (motion blur, glows, fades).
- Placement is `AppendToTimeline` with `clipInfo` `{mediaPoolItem, startFrame: 0, endFrame: <frame count>, recordFrame: 108000 + start, trackIndex: 2, mediaType: 1}`. `endFrame` is **EXCLUSIVE**, `recordFrame` is **ABSOLUTE**. Script it idempotent and readback-verified. It is the raw API, so it runs as-is in the official engine's `run_script` (2026-09-25: 23 graphics + the privacy patch + the caption layer, frame counts = slots, on a 2160x3840 timeline with 1080x1920 renders conformed by `scaleToFit`).
- **The Talking Head Explainer's layout keys** ([`LANES.md`](../../../LANES.md) § Step 5′; the target is HOLD keys, V1 never razored, because a razor costs the creator his trim points). The transform numbers: `SetProperty('Pan'|'Tilt'|'ZoomX'|'ZoomY', v)` reads back exact, and from Premiere-normalised Motion values (`face-frame.py --modes`, or a .prproj's Position (x, y) and Scale) `Pan = (x − 0.5) · W`, `Tilt = −(y − 0.5) · H`, `Zoom = Scale / 100`, W × H the timeline size. `TimelineItem` has no keyframe API, so the target-conformant route is a Fusion Transform with hold keys on each V1 clip (below): unproven. What IS proven (2026-09-25): split V1 at every layout change and give each piece its own static transform (22 hold-keyed Premiere clips → 29 pieces, the framing identical to the Premiere master by frame). That razors V1, so it is a DEVIATION from the target: announce it and record it in RUN.md.
- **`TimelineItem` has NO keyframe API** (only static `SetProperty` plus the Fusion methods), so an animated footage move is a Fusion comp on the clip: `AddFusionComp` → `add_tool Transform` → connect MediaIn→Transform→MediaOut → `add_keyframe` on `Size` (verified interpolating: 1.0→1.07 reads 1.035 mid-clip, community `fusion_comp` wrappers). On the official engine the same comp is raw Fusion API in `run_script` (`item.AddFusionComp()`, `comp.AddTool('Transform')`, `ConnectInput`, `SetKeyFrame`): not yet run there, so verify it on its first job.
- Resolve's embedded Python opens files as **ASCII**: `io.open(..., encoding='utf-8')` everywhere, and keep em dashes out of timeline names (either one kills the script).
- Verify compositing from a real render.

## Step 6 — SFX and the music bed (Resolve 21.1+)

WHAT to place: the preset's `sfx.md` and `workflows/sfx-plan.py`'s reviewed cut sheet; the music bed:
`background-music`. HOW, on 21.1 (either engine, raw API):

- Lay each sound audio-only: `AppendToTimeline` with `mediaType: 2` and `trackIndex` = its audio track
  (add stereo tracks first: `tl.AddTrack('audio', 'stereo')`). An imported audio file ingests at the
  PROJECT frame rate, so `startFrame` / `endFrame` are the source in/out in timeline frames.
- Level: `item.SetProperty('AudioVolume', <dB>)` (−100..+30); only write non-zero levels, read back with
  `GetProperty('AudioVolume')`. A fade or a one-sided crossfade: `item.SetFades({'FadeOut': <frames>})`.
  Music: the bed's dB as `AudioVolume`, its tail as `FadeOut`.
- Reading levels out of a Premiere project (rebuilding a Premiere job here): the .prproj stores the clip
  Volume Level as linear gain with 0 dB at 0.177828, so `dB = 20·log10(v) + 15`; a clip with no volume
  component is 0 dB.
- Proven 2026-09-25: 103 hand-placed sounds on three tracks plus the bed (−21 dB, 48-frame fade), every
  level read back; the render landed −17.5 LUFS against the Premiere master's −17.7. No placer reads
  `sfx-plan.json` yet: script the placement per job.
- ⚠️ Nothing limits the master here: Resolve's sum ran about 0.3 dB hotter than Premiere's on the loudest
  hits of the same levels (sample peak +0.03 vs −0.27 dBFS). Check the render's peak and report a hit;
  the levels are the creator's call.

## Step 8 — export: the native render queue

**Read [`lanes/resolve/resolve-export.md`](../../../lanes/resolve/resolve-export.md) before scripting a
DELIVERY render** — it owns the settings truth table. Target (the presets' § Export, 2026-09-26): H.264 MP4 at
the FILE's frame (3840×2160 for any long-form, a 1080 timeline too; 1080×1920 for any vertical file; a 4K vertical
timeline's Shorts file a second job at 2160×3840), `VideoQuality` = the preset's bitrate in kb/s WITH
`MultiPassEncode: True` (without it the number is only a cap), AAC 48 kHz, straight to `projects/<job>/outputs/`.

**Set the render keys one call each and read every return** (the export doc's `set_each`): Resolve 21.1 on Windows
refused `VideoQuality` for every value and a dict holding it dropped every other key too (H.264 Main at 52.6 Mbps,
2026-09-27). A refused bitrate means a ProRes 422 HQ master and `uv run workflows/deliver.py` for the deliverable.

Three facts to have before you open it: `SelectAllFrames` must be a real bool; MarkIn/MarkOut are
ABSOLUTE timeline frames (a 01:00:00:00 start means frame 86400 at 24 fps, not 0); and
`GetRenderSettings` does not exist in the API, so **verify the finished file with ffprobe**,
never a settings readback.

Community: `render prepare_render_job` → `render start` (the wrapper's false is not a failure, below).
Official (`run_script`, two calls because of the 60 s cap), the proof job's short-form delivery:

```python
project.SetCurrentTimeline(tl)                       # the timeline found BY NAME
project.SetCurrentRenderFormatAndCodec('mp4', 'H264')
project.SetRenderSettings({'TargetDir': '<abs>/projects/<job>/outputs', 'CustomName': '<job>-render',
    'SelectAllFrames': True, 'FormatWidth': 1080, 'FormatHeight': 1920, 'FrameRate': 23.976,
    'VideoQuality': 14000, 'MultiPassEncode': True, 'EncodingProfile': 'High', 'AudioCodec': 'aac', 'AudioSampleRate': 48000,
    'ExportVideo': True, 'ExportAudio': True, 'NetworkOptimization': True})
project.DeleteAllRenderJobs(); jid = project.AddRenderJob(); project.StartRendering([jid])
# next call: project.GetRenderJobStatus(jid) until JobStatus == 'Complete'
```

That rendered 2872 frames of 1080x1920 in 19 s at 13.96 Mbps with AAC at 320 kb/s (without multi-pass; on easier
footage the same cap landed at 10.9, so multi-pass is on since 2026-09-26). On 21.1 `VideoQuality: <int>` is a
bitrate in kb/s (the export doc has the version split).

Then `./finalize.sh <job> --apply` for promotion + the `~/Downloads` copy (lane-agnostic).

## What the API can do (all readback-verified)

**(community)** marks a wrapper feature that exists only in the community engine; everything else is the
raw API, so the official engine reaches it through `run_script` under the raw name given.

- **(community)** **Auto rough-cut in-app: `edit_engine plan_silence_ripple` → `execute_silence_ripple`.** Validated end to end (75 lifts, 548.5s → 397.4s, mirrored audio items, original timeline untouched: it assembles a named VARIANT). Also reports keep-ranges too short to dissolve. **This is the working cut path; never `apply_cuts` (below).** For frame-exact word-level cuts, the house WhisperX rough-cut still wins (see below).
- **Text-based editing, read half:** `timeline_ai create_subtitles` (raw `tl.CreateSubtitlesFromAudio()`; GUI only, ~57s for 9 min) → **(community)** `timeline get_transcript` → `timeline propose_cuts` (dry-run proposals with kind/span/confidence/rationale for stammers, repeats, long pauses).
- **Fusion node graphs from the API:** `fusion_comp` add_tool / connect / set_input / add_keyframe, plus **(community)** `bulk_set_expressions` for procedural animation. Scope arg must be nested: `timeline_item: {track_type, track_index, item_index}`, NOT flat. Raw: `item.AddFusionComp()` and the Fusion comp API (`fusion_api.pyi` via the official `get_scripting_api`).
- **Custom GPU color shaders + multi-clip grading:** author a DCTL (official: `update_dctl`, compiled before it is written), put it on a **color group's post-clip node**, and every member clip inherits it. Full playbook + gotchas: [`lanes/resolve/resolve-grading/`](../../../lanes/resolve/resolve-grading/README.md) — read it before any grading work. Short version: § Step 4 above.
- **Arbitrary Python inside Resolve:** community `script_plugin run_inline` with `resolve` / `project` / `fusion` pre-bound; official `run_script` (sandboxed) and `run_script_unsafe` (filesystem, subprocess) with `resolve` / `project`. Hard 60s timeout on both; long ops go through the tool wrappers or split scripts.
- **(community)** **`timeline_versioning`** auto-archives before destructive ops (`<name>_archived_vNN` in Master/Archive) with rollback + diff. Rollback restores into a NEW `<name>_rolled_back_<hhmmss>` timeline. Official engine: `tl.DuplicateTimeline('<name> backup')` by hand before anything destructive.
- **(community)** **Vision loop:** `media_analysis analyze_clip` extracts frames → Claude reads them → `commit_vision` writes Description/Comments/Keywords onto the clip + builds a SQLite FTS index.
- **Voice Isolation** writes at the TRACK level (`timeline set_voice_isolation_state`, raw `tl.SetVoiceIsolationState`); the timeline_item version returns false.
- **Frame QA per clip only:** `timeline_markers get_thumbnail_image` (raw `tl.GetCurrentClipThumbnailImage()`) returns the CURRENT CLIP's graded frame inline (GUI + Color page only), NOT the program composite: over a graphics track it shows the overlay on black and proves nothing. Fine for a single-track frame check; compositing and multi-track grades need a real render.
- Bin organization (`folder` / `media_pool`), markers, color groups, layout + keyboard presets, project settings: all live.

## Broken or dangerous: do not build on these

- **(community)** **`timeline apply_cuts` DESTROYS the timeline while reporting success.** A "lift" deletes whole timeline ITEMS intersecting the span (it does not razor at boundaries); on a single-clip timeline the first lift deleted the entire clip, yet the tool reported `success: true, applied: 19`. Its claimed auto-archive did NOT happen (`_versioning.archived: false`). If it ever runs: never trust the applied count, read `results[].deleted` per cut, verify item counts after, and recover via `timeline_versioning rollback`. Use `execute_silence_ripple` or razor-based edits instead.
- **`SmartReframe`: the feature works, the API call does not.** The Inspector button fills the frame; the API call returns `success: true` and changes nothing, and there is no getter to even verify a UI reframe. Keep using `workflows/face-frame.py` for the measured 9:16 crop.
- `create_magic_mask` / `RegenerateMagicMask` return False in every mode, GUI included.
- `Stabilize` returns True but exposes no property to verify. Unverifiable through the API.
- **(community)** `gallery_stills grab_and_export` **crashes the MCP server.** Use the two-step path: `timeline_ai grab_still` → `gallery_stills export_stills` (also drops a `.drx` of the grade); raw `tl.GrabStill()` → the album's `ExportStills(...)`.
- `Graph` has no AddNode: you can set LUTs/labels/enable on existing nodes but cannot create serial nodes. Workarounds: `ApplyGradeFromDRX` (a .drx carries a whole node tree, built once by hand or grabbed off a graded clip), a Fusion comp (`AddFusionComp` + `add_tool` — node creation IS exposed there), or fold the look into one DCTL.
- **(community)** **`graph get_lut` reports the wrapper's own record, not Resolve's state (2026-08-06).** It returned a LUT name for a node where `GetLUT(1)` in-process read `None`; the matching `set_lut` had also reported success. Any grading readback must go through `script_plugin run_inline` (official: `run_script`) against the real API objects, then be confirmed by a render.
- **(community)** **`render start` returns `success: false` while the render runs fine.** `project.StartRendering([job_id])` returns `True` and produces the file — don't retry on the wrapper's false.
- **(community)** `resolve_control` has **`open_page`, not `set_page`** (raw: `resolve.OpenPage('edit')`); `resolve.RefreshLUTList()` doesn't exist (it's `project.RefreshLUTList()`).
- **`pm.SaveProject()` on "Untitled Project" opens the GUI's Save Current Project dialog** and the script hangs to its cap (official engine, 2026-09-25; § Project setup has the guard). The dialog is a hand-click or a background accessibility click on Cancel.
- The scripting API cannot switch the Color page's node-graph level (Clip / Group Pre / Group Post / Timeline). Its whole UI surface is page switching + layout presets, so a session can build a group grade but cannot show it on screen — that dropdown is a hand-click.
- **(community)** Bundled whisper.cpp transcription produced 0 segments; Resolve's own subtitle engine is the working path. Slate-clap sync detection false-positives on speech.

## Discipline

- **Target timelines by NAME, never `GetCurrentTimeline`,** whenever the user has the GUI open. They switch timelines while you work, and two writes have landed on the wrong timeline that way. Loop `GetTimelineByIndex` and match `GetName()`.
- **Read back after every write** (same rule as the Premiere bridge): property writes return success generously; the readback is the truth.
- Getting the cut onto the timeline is where the handoff ends unless asked for more. The user's own editing happens in the app.
