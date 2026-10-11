# CLAUDE.md — Video Editor

Your **video production & editing department** — and **only** that. Raw filmed footage comes in, a
finished exported cut goes out: point it at a raw clip and it takes that clip from **raw → fully
edited → exported.** What happens afterward (posting, scheduling) is out of scope. Not a traditional
code repo — a content system where **Claude IS the editor**, one skill per stage in `.claude/skills/`.

> **Updating an editor the user already has? Start here.** If this folder is a new version the user
> just downloaded or unzipped, and they already work in another video-editor folder: do not copy or
> unzip anything into that folder, and do not run setup here. Your session is IN this download → run
> `uv run update.py` here: it finds their project and updates it from this folder (if it lists several,
> ask which, then `uv run update.py --project "<their folder>"`). Your session is in THEIR folder → run
> `uv run update.py "<this folder>"` (a folder from before updates has no update.py: then
> `uv run "<this folder>/update.py" "<this folder>"`). Either way it sets their folder up for updates if
> it never was and merges this version in; their presets, brand kit, rules, jobs and app wiring stay
> theirs. Then § Updating, and afterwards they work in their own folder.

---

## 🪟 On Windows? One check first

This system runs natively on **macOS, Windows, and Linux** — no virtual machine. On Windows the
`.sh` scripts run through **Git Bash** (installed with **Git for Windows**), the same shell Claude
Code itself uses. Run `uname -s`: `Darwin` / `Linux` / `MINGW…` / `MSYS…` → you're set, go to **FIRST
RUN**. A command-not-found or PowerShell-looking answer (`C:\…` paths) → Git for Windows is missing:
run `winget install --exact --id Git.Git` yourself if you have a PowerShell tool (else the user runs it
in PowerShell), restart Claude Code, re-check.

> Windows notes: installs go through **winget**, which `./setup.sh` runs for you (an install may raise
> a "Do you want to allow this app to make changes?" prompt the user clicks Yes on; it can open behind
> other windows), then one Claude Code restart so PATH updates. Python there is
> `python`, never `python3` (a fake Store stub — the scripts handle it). Apple's hardware encoder is
> a Mac-only speed perk; Windows and Linux render in software, same result, and an NVIDIA GPU is
> auto-detected for transcription. Keep the project folder OUT of Documents, Desktop, Pictures,
> Videos, Music and OneDrive: Controlled Folder Access blocks writes there for Git Bash, node and
> python, and the error reads "No such file or directory", not "permission denied". `./setup.sh`
> checks this first and prints the fix (move the folder, or allow the four apps). Keep the folder's path
> at most 100 characters (e.g. `C:\Users\<you>\video-editor`): Windows stops a path at 259 characters and
> the editor installs files up to 145 characters deep inside its folder, so `./setup.sh` refuses a
> deeper folder before installing anything.

---

## 🚦 FIRST RUN — onboarding gate (read this before doing anything else)

**The first thing to handle when the project opens.** A SessionStart hook
(`.claude/hooks/setup-check.sh`) nags for as long as setup is incomplete. Trigger this flow on **"set
this up (on my machine)"** / **"run the setup"** / **"set me up"** / **"install this"** / **"continue
setup"**, **or** on any request to edit a video while the tools are missing (an edit cannot run without
ffmpeg). The hook also says when this folder is a NEW DOWNLOAD of an editor the machine already has
(then the user wants an update: see the box at the top), and when an update stopped on conflicts.

**Is setup done?** One deterministic check: the marker file **`.setup-complete`**, one line,
`lane=<premiere|resolve|capcut|finalcut|chat-only|pending>`, written by `./setup.sh` once every core tool
verifies. **Missing** ⇒ run the flow below. **`lane=pending`** ⇒ tools done, the which-app question
still open: ask it, then record the answer with `./setup.sh --lane <pick>`. **A real lane** ⇒ done,
skip this gate and work normally (on "continue setup", re-run `./setup.sh` once, verify the lane,
make step 3's offer). That `lane=` line is what every edit reads to know its finish surface.

**The goal: core editing working, fast, with near-zero effort from the user.** Personalization is
OPTIONAL and comes last. The presets ship with a neutral bundled look (Inter fonts, a generic
starter palette, no handles), so nobody else's brand can leak into a video.

1. **Tools: run `./setup.sh` yourself.** Don't ask first and don't hand over a command list; say
   what it's doing as it goes. It detects the OS (macOS → Homebrew, Windows → winget), installs every
   missing core tool, bootstraps the render engine (`npx hyperframes@0.8.16 browser ensure`; its npm
   and telemetry chatter is noise, and the version is pinned — never run `hyperframes upgrade`),
   verifies with `./check-setup.sh`, then probes for editing apps. **Run it with the Bash timeout at
   its maximum (600000 ms) or in the background:** a first run on a fresh machine can take 10-20
   minutes. It is **idempotent: re-run it after any interruption.** Its exits:
   - **exit 0:** done, `.setup-complete` says which lane → step 3, after following every `ACTION FOR
     CLAUDE` line it printed (several editing apps found → step 2; a folder in OneDrive → offer to move
     it). It ends by naming the editor folder: if your session's folder is not exactly that one, the
     user opens it in Claude Code first (Windows' Extract All nests it one level down).
   - **exit 2:** a restart is needed: this session can't see something just installed (Windows
     after winget, Homebrew's PATH on a Mac), or Claude Code is open on the wrong folder (the output
     names the right one: the user opens THAT folder). Restart, then re-run `./setup.sh`; it gives up on
     a third restart for the same thing and says what failed. **exit 3:** it wired a lane into
     `.mcp.json` — restart, then verify the lane.
   - **exit 1:** read the output. Homebrew missing → open Terminal with its installer already running
     yourself (`osascript -e 'tell application "Terminal" to do script "/bin/bash -c \"$(curl -fsSL
     https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""' -e 'tell application
     "Terminal" to activate'`), then tell the user: type your Mac password in that window (nothing
     shows as you type; the account must be an administrator), press Return when asked, and say when
     it finishes; then re-run `./setup.sh`. Tools still missing → `check-setup.sh` printed the exact
     command per tool: run the brew and winget ones yourself; only `apt install` (sudo) goes to the
     user. A winget install that failed is named, with its own words in `.setup-install.log`. A lane
     installer failed → fix it, then `./setup.sh --lane <that app>`. **This folder looks like a NEW VERSION
     of an install already set up** (the ACTION line names that install): ask the user in one line whether to
     update that install (run `uv run update.py` here: it updates their project from this download) or make
     a second, separate install (`./setup.sh --new-install`, then carry on with the flow).
   Loop until `./check-setup.sh` shows every core item ✓. (Manual per-OS list: `SETUP.md`.)
2. **Editing app lane: auto-detected, at most one question.** `setup.sh` probes for Premiere Pro,
   DaVinci Resolve, CapCut and Final Cut Pro (Final Cut is macOS only, CapCut macOS and Windows; Linux:
   resolve or chat-only) and records the outcome as the `lane=` line. **One app** →
   already settled: Premiere/Resolve/Final Cut ran their installer (`./setup-premiere.sh` /
   `./setup-resolve.sh` / `./setup-finalcut.sh`) and exited 3, CapCut needs no install. **Final Cut**
   needs ONE click from the user first: its installer opens SpliceKit, which makes a separate, patched
   copy of Final Cut that Claude can drive (the App Store app is never changed), and setup exits 1 with
   an ACTION line: relay it (quit Final Cut, click Continue in SpliceKit), and when they say it is done
   re-run `./setup.sh --lane finalcut`. The same click comes back after every Final Cut update. **Several**
   → ask ONE line ("Premiere, Resolve and CapCut are all here: which do you edit in?"), then run
   **`./setup.sh --lane <pick>`** yourself (`premiere` | `resolve` | `capcut` | `finalcut`); the pick is
   final, never switch unless asked. **None** → `lane=chat-only`: say so in one line, move on, never
   re-ask at edit time. **CapCut** needs no install, but macOS asks once, the first time Claude
   drives it, to let Claude Code control the computer (System Settings → Privacy & Security →
   Accessibility): say so when the first CapCut edit starts.

   **Verify a wired lane after the restart.** First the MCP: its tools must be present in the
   session. `setup.sh` pre-approves the lane's own server in `.claude/settings.local.json`, so Claude
   Code should not ask; if it does, the user answers **yes**, and a remembered "no" is undone with
   `claude mcp reset-project-choices` (run it yourself), one more restart, and a yes. Then the app: **Premiere** → run
   `./lanes/premiere/premiere-up.sh` and confirm `node lanes/premiere/premiere-bridge.mjs ping`
   answers (only if it fails, fall back to **Window → Extensions → MCP Bridge (CEP) → Start Bridge**).
   **Resolve** → ask the `davinci-resolve` MCP for the version, with Resolve running; don't send
   anyone into Preferences, External scripting = Local is its shipped default. **Free edition**
   (the `davinci-resolve` entry in `.mcp.json` carries `DAVINCI_RESOLVE_BRIDGE`): the user must
   first open a project and run **Workspace → Scripts → resolve_bridge** inside Resolve, and every
   Resolve restart needs it again, so say so before the first Resolve call of every session. A
   `BRIDGE_UNAVAILABLE` answer means it isn't running: ask for it, never retry in a loop.
   **Final Cut** → launch the PATCHED copy by its path, `open ~/Applications/SpliceKit/Final\ Cut\ Pro*.app`
   (never the App Store Final Cut or the Dock icon: they have no bridge), wait for it, then
   `uv run lanes/finalcut/sk.py system.version` must answer with the Final Cut and SpliceKit versions.
   `uv run lanes/finalcut/sk.py --dismiss` closes Final Cut's "notifications" sheet when it shows (it
   returns until the user answers macOS's notification question for that copy once).
3. **Brand kit: OPTIONAL. Offer once, never block.** Say the editor already works with the neutral
   bundled look, and that whenever they want captions and graphics to sound and look like them they
   can fill in [`brand-kit.md`](brand-kit.md) and say **"apply my brand kit"** (you then follow the
   file-by-file map in its Part B and render one test). Don't walk them through it unless asked.

**Restart walkthrough (be exact and friendly):** *"Quit Claude Code completely (Cmd+Q on Mac / close
the app on Windows), reopen it, open this same folder, and say **continue setup**."* After the Premiere
lane was wired, first: *"Quit Premiere Pro too if it's open; it loads the new panel when it starts."*
Never assume a restart loaded anything — verify it.

---

## 🔄 Updating to a new version

New versions ship often. When the user says **"update"** (or "I downloaded the new version", "update
the editor"), run it yourself from THIS folder, the one they already work in, with the Bash timeout at
600000 ms:

    uv run update.py

It finds the newest `video-editor*` download in Downloads by the version inside it (never by file
name: a second download is saved as `video-editor-client (1).zip`), runs that download's own updater,
and merges it in. Give it a path only when the user names one. No newer download → say so and ask them
to download the new zip. On Windows, ask the user first to close any file from this folder that is open
in another app (an app holding one stops the update, which then puts everything back).

This folder is a git repository with two lines of history: `upstream` holds every version exactly as
it shipped, the user's branch holds their project. The update commits what they changed, lays the new
version on `upstream` and merges it in, so a file only the new version changed is updated, a file only
they changed keeps their version, and a spot both changed stops as a conflict. `projects/`, `.env`,
`.mcp.json`, `vendor/` and large media are never touched. **Never copy files over from a download by
hand, never delete `.git`, and never pass `--force` unless the user asked to go back to an older
version.**

- **exit 0:** done. Relay the "What is new" lines in one short list, and any line about files it kept
  or moved aside, then run `./check-setup.sh` (only a ✗ line needs `./setup.sh`). Then tell the user to
  start a fresh Claude Code session (/clear, or quit and reopen) so the new instructions load.
- **exit 3:** it stopped on conflicts and printed how to read them. Resolve every block, keeping both
  the user's deliberate changes and the new version's fixes; ask the user about any block you cannot
  call; then `uv run update.py --continue`. `uv run update.py --abort` puts every file back.
- **exit 1:** nothing changed; the line says why (no newer download, a damaged or half-downloaded
  zip, a Downloads folder macOS would not let it read, a file open in another app). Fix that and run it
  again; the user can also just tell you where the zip is: `uv run update.py "<the zip>"`.
- **A conflict on a file with no markers** (a binary, or a file one side deleted): settle it with
  `uv run update.py --keep-mine <file>` (the project's copy) or `--take-new <file>` (the other side),
  then `--continue`.
- **A brand-kit line after an update:** follow it (fill each new `<<…>>` field from what the user
  already gave for the same role, then "apply my brand kit").
- **"Undo the update":** `uv run update.py --undo` takes the last update back out and keeps
  everything done since. Never `git reset`.

**Where the user's own work goes, so no update ever fights it:** their standing rules and their brand
identity in [`my-rules.md`](my-rules.md) (loaded below, never changed by an update), a new preset in its
own folder under `presets/<platform>/<name>/`, a new skill in its own `.claude/skills/<name>/`. Edits to
shipped files merge too; a separate file just never conflicts.

---

## Brand Kit

The editor's voice and look come **entirely from [`brand-kit.md`](brand-kit.md)** and the presets it
feeds ("apply my brand kit" writes the identity and voice into [`my-rules.md`](my-rules.md)); the short-form look (palette, type, backdrop) is locked in
[`presets/instagram/talking-head-explainer/graphics.md`](presets/instagram/talking-head-explainer/graphics.md),
the long-form one in the [`presets/youtube/default/`](presets/youtube/default/README.md) docs.
Apply them verbatim. Filling the kit in is optional — editing works before any personalization.

---

## The Pipeline — one linear flow, every time

Every job runs the **same eight steps, in order**, raw → done, each finished to its own definition of
done before the next starts. The run is owned by the **`edit-video`** skill, which keeps
`projects/<job>/RUN.md` so it survives a context compaction and resumes cold.

**The finish surface is your editing app by default:** a bare "rough cut" with no lane named means
the lane recorded in `.setup-complete`. A machine recorded as `lane=chat-only` is already on the chat
finish, so never re-ask; on a machine WITH an app, chat-only runs only on an explicit yes to "want
this done straight in chat?", never inferred from a job's content.

**The eight steps are the line for EVERY job on EVERY lane** — what changes per lane is only WHERE a
step happens (steps 3–7 on the app timeline, or in the bundled render engine + ffmpeg on the
chat-only lane). Format doesn't change the flow either: it changes how **Graphics (step 5)**
behaves (captions included: the short-form presets caption by default as a step-5 overlay; long-form never), and the Talking Head Explainer also reaches steps 2, 3, 4 and 6 through its own preset README. Run the line; branch only inside those steps.

🔒 **At every step the route is the same two reads: the PRESET for WHAT (the numbers, identical in
every editor), then [`LANES.md`](LANES.md) for HOW.** A step your app has no recipe for is done by
hand from the preset's numbers and **said out loud**, never with another app's mechanics.

| # | Step | Skill | What happens |
|---|------|-------|--------------|
| 1 | **Intake** | _(copy)_ | Point to a raw file (often in `~/Downloads`). **Copy** it into `projects/<job>/raw/` — never move, never touch the original, so the source survives a bad render. Name `<job>` after the content (see Job naming). |
| 2 | **Rough cut** | `rough-cut` | Always, every format. `transcribe.sh` (WhisperX large-v3 + word alignment) → kill filler and dead air (**the #1 filter: relevant ≠ necessary — good-to-know is fluff, only need-to-know-NOW survives**) → `splice.sh` stitches it frame-snapped, `polish-boundaries.py` sets every word edge → **fresh-eyes second pass** (two subagents on this session's model, never Fable: a Fable session passes `model: opus` explicitly; one tier down only when the user asks for it) → **a STATIC audio chain: the measured amplify from `workflows/voice-gain.py` (kept speech → −17 LUFS pre-limiter) into a −6 dBFS limiter**, never dynamic loudnorm. Produces the cut **and the finished script**, the source of truth downstream. On an app finish it runs `RENDER=0` and replays the EDL onto the timeline, and **every cut is proven**: `workflows/cut-audit.py` on the finish surface's frame grid (zero boundaries in speech), and on Premiere `lanes/premiere/cut-proof.py` bounces the laid dialogue and diffs it against the script; exit 0 is done. |
| 3 | **Audio polish** | _(in-app / baked by splice)_ | **Every job, immediately after the cut lands on its finish surface.** Same chain everywhere: the gain `workflows/voice-gain.py` measures (kept speech → −17 LUFS pre-limiter, so a quiet shoot gets more and a hot one less) into a −6 dBFS limiter. Premiere: ONE command, `uv run lanes/premiere/audio-polish.py projects/<job> --apply`, and **a timeline rebuild discards the effects, so re-apply after every re-replay**. Resolve: `lanes/resolve/resolve-audio-polish/`; Final Cut: baked by `workflows/normalize-sections.sh`, then laid by replay. Chat-only: `splice.sh` baked it in already. Per-lane: [`LANES.md`](LANES.md) § step 3. **The cut locks here.** Asked for the whole edit, the run does not wait: it finishes everything up to the export, and cut notes you give at review are a re-cut (`workflows/ripple-cut.py` re-times the downstream layers). Asked for just the rough cut, it stops here, and the next step (4 on long-form and the Talking Head Explainer, 5 on TikTok/raw) starts once you have watched the polished cut and said the cut is good. |
| 4 | **Color grade** | _(in-app)_ | **Long-form and the Talking Head Explainer (camera footage only), before graphics, and it lives UNDERNEATH them:** ONE adjustment layer spanning the timeline, above the footage and below the graphics (Premiere: V1 footage → V2 grade → V3 graphics). Footage-only is the point — the graphics already ship the colours the preset locks — and it runs first because the graphics QA measures off the shipping picture. **The look is locked: Autumn-Rec709 as a Creative Look at Look Intensity 80, Creative Saturation 120**, shipped captured, so `uv run lanes/premiere/grade-lut.py apply <job>.prproj` replays it hands-off on job one. There is NO colour-correction step. Numbers: [`presets/youtube/default/README.md`](presets/youtube/default/README.md) § Grade. Mechanics: [`LANES.md`](LANES.md) § step 4. |
| 5 | **Graphics** | `graphics-plan` → `graphics-build` → `edit-review` | **Default = the preset's own default vocabulary.** Long-form: the BASIC tier, its [`default-overlay-style.md`](presets/youtube/default/default-overlay-style.md) (4–7 face-clear UI cards plus required real captures and written-artifact walkthroughs, [`creative-moves.md`](presets/youtube/default/creative-moves.md) § 4d) plus the [creative-moves vocabulary](presets/youtube/default/creative-moves.md) unprompted. The Talking Head Explainer: one tier, its [README](presets/instagram/talking-head-explainer/README.md), [`layout.md`](presets/instagram/talking-head-explainer/layout.md) and [`graphics.md`](presets/instagram/talking-head-explainer/graphics.md) (the layout rotation, real captures, full-screens within its caps). TikTok/raw stays hook-card-only. Named alternate looks are opt-in. **(a)** `graphics-plan` storyboards every graphic and self-reviews, gated by `validate-plan.py`. **(b)** `graphics-build` owns comps, renders and placement (`workflows/placement.py --write` writes the rows on every lane; Premiere: `lanes/premiere/place-graphics.py`); the short-form caption layer is one of its graphics, and on the Talking Head Explainer it **measures the footage framing first**, `uv run workflows/face-frame.py projects/<job> --modes --collar --plan projects/<job>` (samples only the raw's kept spans, the collar on the layout's W/O/T spans; locked: hair top 100 px below the y960 seam in split, measured, never guessed), then lays the lane's layout keys. **(c)** `edit-review` converges it: `uv run workflows/graphics-qa.py projects/<job>` (a 9:16 job: `workflows/graphics-qa-short.py`) green is the precondition, then fresh-eyes subagent rounds on two dimensions drive the draft to ZERO objective defects before you ever see it — defects only, never taste, cap 3. **The mistakes the system can find, the system fixes.** |
| 6 | **SFX** | `workflows/sfx-plan.py` → lane placer | Sound design synced to the graphics. The PRESET says what: [`presets/youtube/default/sfx.md`](presets/youtube/default/sfx.md) + `sfx.json` (the Talking Head Explainer ships its own [`sfx.md`](presets/instagram/talking-head-explainer/sfx.md) + `sfx.json`, and its face-to-graphic cut-ins come from the plan's layout map) (motion event → sound class → library slice → target peak, three tracks by layer depth; entrances are events, exits and cuts back to the face are silent). `uv run workflows/sfx-plan.py projects/<job>` reads the PLACED graphics and writes a cut sheet with a measured level per slice; placement is per lane ([`LANES.md`](LANES.md) § step 6), Premiere `uv run lanes/premiere/place-sfx.py projects/<job> --apply` (`--diff` reports your hand edits first); Final Cut: `lanes/finalcut/replay.py` lays the cut sheet; Resolve 21.1+: scripted per job from the plan (LANES.md § step 6); CapCut and chat-only: hand-place from `hf-graphics/sfx-plan.md` and say so. Library: `assets/sfx/`. **After any graphic moves, read the timeline diff, then re-run the plan and re-place, verifying zero missing/extra/drifting cues.** |
| 7 | **Review** | _(manual)_ | You watch and call adjustments — cut this graphic, swap that one, move it, redo. The draft already has zero *objective* defects, so this pass is **taste**, and only taste. **Iterate incrementally:** re-render ONLY the changed part (chat-only mechanics: [`lanes/chat-only/incremental-graphics.md`](lanes/chat-only/incremental-graphics.md)). |
| 8 | **Export** | _(lane render → `finalize.sh`)_ | The final render is the lane's: Premiere `uv run lanes/premiere/export.py projects/<job>` on your go (never Adobe Media Encoder), Final Cut `lanes/finalcut/export.py projects/<job>`, Resolve and CapCut render natively; then **finalize**: `./finalize.sh <job>` (dry-run; `--apply` to act) promotes the latest render to the one canonical `outputs/<job>.final.mp4`, retires dead drafts and **drops an export copy in `~/Downloads/`** (`VE_EXPORT_DIR` overrides that target), keeping the base cut, transcript and `hf-graphics/` source so the job can be reopened. `--apply --keep-drafts` promotes and makes the Downloads copy but deletes nothing in `outputs/` (a replaced final is kept as `<job>.draft-prev.mp4`). A second deliverable, such as an ad cut, lives in `outputs/ad/` and is finalized with `./finalize.sh <job> --variant ad --apply`; a 4K vertical job's YouTube Shorts file (2160×3840, the export tool's `--shorts`) the same way in `outputs/shorts/` with `--variant shorts`. The export numbers (researched 2026-09-26): long-form 3840×2160 H.264 CBR 50 from a 4K or a 1080 timeline, every vertical file 1080×1920 CBR 14, AAC 320k — the presets' § Export. Never export onto `outputs/<job>.mp4`, the base cut's name: finalize warns and `--apply` refuses until it is renamed `<job>-final.mp4`. |

**One CONDITIONAL pass hangs off the line — opt-in, so it is not a numbered step.** It has a
fixed slot; run it there or say why it was skipped. (Captions are not a pass: on the short-form
presets they are the top layer of step 5, placed like any other graphic.)

| Pass | When | Slot | What happens |
|---|---|---|---|
| **Background music** | opt-in, format-agnostic (skip unless asked) | after 6, before 7 | `background-music` lays a **flat constant bed** by default: no ducking, no fade-in, −20 dB, the bed starting at the reviewed sustained musical entrance (sparse intro transients do not count), a 2 s tail fade-out only. Ducking and fade-in are **opt-in**. chat-only: a pure audio pass, video copied, no re-encode; Premiere: `lanes/premiere/place-music.py` onto A5, bounce-proved; Final Cut: `replay.py` lays `music-plan.json` (written by `workflows/music-onset.py <track> --write-plan projects/<job>`); Resolve 21.1+ and CapCut: per LANES.md. |

### Your finish surface

On an app finish, steps 3 through 7 happen on that app's timeline. The rough cut is **not** imported
as a flattened export: each lane **rebuilds it as separate, trimmable clips** by replaying the EDL
(`transcript/cuts.json`) against the raw footage, so every cut is a real edit point you can
ripple/slip/slide. That's why step 2 runs `RENDER=0` on an app lane.

**Switching apps** ("switch my editing app to X"): run `./setup.sh --lane <premiere|resolve|capcut|finalcut|chat-only>`
yourself, relay any ACTION line (Final Cut: the one SpliceKit click, then re-run the same command), then do the
restart and the lane verify from FIRST RUN step 2. The new `lane=` line is the finish surface from the next edit on.

- **Premiere Pro** (`premiere-pro` skill) — `node lanes/premiere/premiere-bridge.mjs replay
  <cuts.json> <clipName>`, the headless bridge, no MCP session needed. From there Claude works ON the
  timeline: alpha-ProRes graphics, baked footage moves, audio chains, section label colours, and the
  export via `exportAsMediaDirect` (never queue Adobe Media Encoder). Install: `./setup-premiere.sh`.
- **CapCut** (`capcut` skill, macOS and Windows) — no API, so `uv run lanes/capcut/capcut-bridge.py` works two
  lanes: it writes a whole draft straight from the EDL, and drives the running app (the accessibility tree on
  macOS, keyboard shortcuts and on-screen reading on Windows) for seeks, splits, deletes and its own verified export. The locks that keep it
  working (quit CapCut while the bridge writes, media hardlinked into the draft folder: under `~/Movies` on a Mac,
  `%LOCALAPPDATA%\CapCut` on Windows; never `replay`
  over a hand-edited draft) live in the skill.
- **DaVinci Resolve** (`davinci-resolve` skill) — `./setup-resolve.sh` wires the MCP onto Resolve's
  official scripting API. The EDL replay is one call, and from there: silence ripple, AI subtitles,
  Fusion graphs, DCTL shaders, native renders. The skill carries what's verified AND what's broken.
- **Final Cut Pro** (`final-cut-pro` skill, macOS) — a patched copy of Final Cut with a bridge inside
  (SpliceKit, installed by `./setup-finalcut.sh`). `uv run lanes/finalcut/replay.py projects/<job>` builds
  the whole timeline from the job's files (the cut, the baked audio, the grade, graphics and captions, the
  layout or push-ins, SFX, music), `lanes/finalcut/import.py` brings it in through Final Cut's own importer
  and proves it clip by clip, and `lanes/finalcut/export.py projects/<job>` has Final Cut render the
  master and the deliverable with no clicks. Every rebuild is a new library, so edits made by hand in
  Final Cut are never overwritten.

**Second entry path: long-form → clips (`clipper`).** The reverse of the line above: transcribe a
finished long-form once, select self-contained hook-and-payoff moments into a reviewed
`clips-plan.json`, then `make-clips.py --build` runs each approved clip through the locked engine
(splice → face-centered 9:16 reframe → TikTok/raw captions → `.final.mp4` + a `~/Downloads/` copy).
Each clip is a standard job folder under `projects/<parent>/clips/<name>/`.

### Format variants — step 5 changes (captions included); the Talking Head Explainer also reaches steps 2, 3, 4 and 6

**Format is AUTO-DETECTED from the raw footage, never asked.** **Vertical** (height > width) →
short-form; **horizontal** → long-form YouTube; a mixed folder is decided by the clips carrying the
substance (a landscape raw the ask calls a short is the Talking Head Explainer, filled to 9:16 once). Talking Head Explainer vs TikTok/raw is inferred from content. State the detected format in the report
so it can be overridden with a word — and do the same with the hook and takeaway, read out of the
transcript and stated for correction rather than asked for up front.

| Format | Aspect | Graphics (5) | Captions |
|---|---|---|---|
| **Short · Talking Head Explainer** (Reels · TikTok · Shorts) | 9:16 · 1080×1920 | the layout rotation (split / tight / wide / full / card) planned per sentence into graphics-plan.json `layout`; `face-frame.py --modes` first (`presets/instagram/talking-head-explainer/layout.md`, `graphics.md`; one tier) | mono caps in an 80 % box, on the seam in split, collar + 40 on the face — **locked** (`captions-style.md`) |
| **Short · TikTok/raw** (Reels · TikTok · Shorts) | 9:16 · 1080×1920 | **front hook card only** (`presets/tiktok/raw/tiktok-raw-style.md`), then raw | low, under face — **locked** |
| **Long-form** (YouTube) | 16:9 · 1920×1080 (no reframe) | `presets/youtube/default/` cards + creative moves (`youtube/liquid-glass/` and `youtube/vox-collage/` are opt-in by name) | none (YouTube CC) |

The 9:16 reframe happens at the top of Graphics, and safe zones live in each preset's own docs
— read the preset you're on before building (the Talking Head Explainer: its `README.md`, then
`layout.md` / `graphics.md` / `captures.md` / `captions-style.md`). Long-form has no platform safe bands: never cover the
face or important on-screen content, keep copy off the very edge, and leave the outro's right side
and bottom clear for end-screen cards.

**Short-form safe zones (always, never break):** no key visuals in the **top 200 px** or **bottom
300 px** — face, captions and every key graphic stay inside y `200 → 1620`. Those two bands are
background only (platform UI and device chrome sit there).

## Skills

- **`edit-video`** — **the orchestrator: the whole line, end to end.** "Edit this video" / "do the
  whole edit" routes here. It owns the ORDER, the STATE and the GATES only; each step's how-to stays
  in its own skill or preset. It keeps `projects/<job>/RUN.md`, rewritten at every step boundary, and
  reads it before assuming a fresh start. A step which cannot run is **announced as skipped, never
  passed over in silence**.
- **Core editing:** `rough-cut`, `graphics-plan`, `graphics-build`, `edit-review`, the locked caption
  presets (`presets/instagram/talking-head-explainer/captions-style.md` + its `captions.py`,
  `presets/tiktok/raw/tiktok-raw-style.md` + its `build.py`), `background-music`.
- **Finish lanes:** `premiere-pro`, `davinci-resolve`, `capcut`, `final-cut-pro` — the HOW docs for the four editing
  apps; [`LANES.md`](LANES.md) is the per-step index across them. **`clipper`** is the reverse entry
  path: a finished long-form in, short-form clips out.
- **HyperFrames suite (engine):** `hyperframes` (+ `-core`, `-cli`, `-animation`, `-audio`,
  `-creative`, `-registry`, `-keyframes`) and `media-use` — the HTML-based video toolkit that renders
  graphics and captions.
- **HyperFrames task workflows (advanced, optional):** `faceless-explainer`, `general-video`,
  `talking-head-recut`, `motion-graphics`, `pr-to-video`, `product-launch-video`,
  `remotion-to-hyperframes`, `slideshow` — vendored extras for one-off builds.

### HyperFrames video-authoring toolkit (vendored)

A general HTML-based video toolkit from `heygen-com/hyperframes`, pinned in `skills-lock.json` and
run via **`npx hyperframes`** on any machine with `node` — `./setup.sh` bootstraps it once
(`npx hyperframes@0.8.16 browser ensure`). **Update via the skills registry, not by hand-editing.**

## Folder Structure

The project root **is** the editing workspace — job folders live directly in `projects/`.

| Path | What's In It |
|------|--------------|
| `.claude/skills/` | The editing skills + the vendored HyperFrames toolkit. |
| [`LANES.md`](LANES.md) | **The routing index: one row per pipeline step, one column per app (Premiere · Resolve · CapCut · chat-only · Final Cut), each cell saying scripted / manual / unvalidated / gap and pointing at the recipe.** Read your step's row before any app-specific work. |
| `lanes/` | Everything app-specific, one folder per finish surface (`premiere/`, `resolve/`, `capcut/`, `chat-only/`, `finalcut/`): bridge and launch scripts, templates, lane sheets, and each app's own `lab-notes.md`. Start at [`lanes/README.md`](lanes/README.md). |
| `presets/` | **The looks — the WHAT half of every step, and app-independent.** One folder per preset under `presets/<platform>/<preset>/`: `youtube/default/` (long-form — read its `README.md` at the top of a long-form job and its `default-overlay-style.md`, the SCOPE contract, before any graphics pass), `instagram/talking-head-explainer/` (the Talking Head Explainer: `README.md` the index, `story-and-cut.md`, `layout.md` + `layout.py`, `graphics.md`, `captures.md`, `captions-style.md` + `captions.py`, `sfx.md` + `sfx.json`, `kit/`) and `tiktok/raw/` (short-form), `youtube/liquid-glass/` and `youtube/vox-collage/` (opt-in by name). A command or an app quirk belongs in `lanes/`. |
| `workflows/` | The universal utilities, identical whichever app you finish in: `voice-gain.py` (step 3), `sfx-plan.py` (step 6), `dead-air-qa.py` (the step-2 dialogue dead-air gate), `cut-audit.py` (proves every cut on the waveform, on the finish surface's grid), `music-onset.py` (the music pass's sustained-entrance measurement), `face-frame.py` + `chin-line.py`, `hero-frame.py` (casts a still of the creator for a graphic: every kept frame scored for eyes open / mouth closed / gaze / frontal, picked by eye off its sheet, proof written), `graphics-qa.py` (the 16:9 step-5 gate) + `graphics-qa-short.py` (the 9:16 one) + `render-diff.py` (its parity proof for any re-render), `flash-scan.py` (every exported file: no single-frame flash, no double cut), `change-events.py` (when a render visibly changes, and `--sync` holds each change to its anchor word), `framing-continuity.py` (proves a substituted clip does not jump the framing at its cuts), `hand-track.py`, `behind-text.py`, `bake-emoji.py`, `window-grab.sh`, `screen-record.sh` + `page-record.mjs` (record an app window / a web page for a planned `screen-rec` cell), `pii-scan.py` (sweeps the kept spans for a literal string that must not reach the screen), `lip-sync.py` (measures a second camera's lag against the voice, and its drift, before that angle is laid), `ripple-cut.py` (re-times the plan, the placement, the SFX and the text metas onto a changed EDL), `placement.py` (writes `hf-graphics/placement.json`, where each rendered graphic sits on the timeline, for the lanes that do not place their own), `deliver.py` (the export encode from a master to the presets' numbers, for a lane whose own encoder cannot reach them), `normalize-sections.sh` (the step-3 chain baked into copies of the raws, for the Resolve and Final Cut lanes) + `fold-look.py` (the house look folded into one `.cube`, for the same two lanes), `recycle-bin.sh` (a job you clear out on Windows, into the Recycle Bin: § Rules, clearing out an old job), `sync-so.py` (re-voices a re-recorded line through sync.so; key `SYNC_API_KEY` in `.env`; recipe in the Talking Head Explainer README and `premiere-pro` § Lip-sync a re-recorded line). A file whose whole job is one app's mechanics lives in `lanes/<app>/`. The `workflows/test_*.py` suites the docs name (holding a Values block equal to its doc, or guarding a fix) are the author's regression tests: they run before every release and are not in this package, so such a pointer says the value is held, never asks you to run it. |
| `projects/<job>/RUN.md` | **The run's state file**, written by `edit-video` at every step boundary: format, lane, preset, per-step status, what each step produced, and everything skipped with its reason. The first thing to read on a job in progress. |
| `projects/<job>/` | One folder per content piece: `raw/`, `audio/`, `assets/`, `broll/`, finals in `outputs/`. The graphics build lives **durably** in `hf-graphics/` (comps + `render.sh` + a `PROJECT.md` resume doc — never delete it, it's the real progress); only the regenerable cache is disposable, and **nothing lives solely in `/tmp`**. A section filmed later nests under `sections/<name>/` with its own transcript: pointed at the parent job, transcribe silently reuses the first section's `words.json` and `cuts.json`. |
| `finalize.sh` | Step 8: promotes the latest render, retires drafts and copies the deliverable to `~/Downloads/`. Dry-run by default. A job you are done with leaves `projects/` whole: § Rules, clearing out an old job. |
| `assets/` | `fonts/`, `logos/`, `sfx/` (the library step 6 draws from), `luts/` (the cubes plus the captured house look, Autumn-Rec709 — see its README), `models/`. **Personalize:** drop your own brand marks in `logos/`. |
| [`brand-kit.md`](brand-kit.md) | The one file you fill in — identity, voice, colours, fonts, hook style. Optional. |
| `transcript-corrections.json` | Upstream transcript fixes (brand and product names, recurring mishears), applied ONCE at step 2, so graphics, captions and long-form all inherit them. Per-job overrides: `projects/<job>/corrections.local.json`. |
| `skills-lock.json` · `check-setup.sh` | The pins for the vendored HyperFrames skills, and the report-only check of the system tools the skills need (ffmpeg, etc.). |
| `RELEASE.md` + `VERSION` | What changed in this build of the system, and which build you have. Check `VERSION` against the download page before reporting a problem. |
| `update.py` · `.shipped-blobs.json` · `.git/` | Updating (see § Updating to a new version): the updater, the fingerprints of every shipped file it checks a pre-update install against, and the repository it merges through. |
| [`my-rules.md`](my-rules.md) | The user's own standing rules, loaded with this file every session and never changed by an update. |

**Job naming:** name `<job>` after the video's content — a short kebab-case title (e.g.
`my-first-video`, `cold-dm-teardown`), **never** the camera file (`C1840.MP4`), a date, or a stage
suffix.

## Rules

- **One job: edit the best video possible.** Raw → fully edited → exported. No business or CTA logic
  lives here — captions and end screens carry no sales asks.
- **Surgical changes only.** Touch what's asked; don't "improve" adjacent renders or refactor working
  skills.
- **Fix the source, never stack a correction on a broken artifact.** A step's output is wrong →
  re-run that step from its durable inputs (`transcript/words.json`, `transcript/cuts.json`, the
  `hf-graphics/` comp source), never compensate downstream: a correction layered on a bad output
  accumulates error and hides the cause, and if a fix needs a fix the approach is wrong. The
  step-level instances are the locks below.
- **The PRESET says WHAT; the APP SKILL says HOW; [`LANES.md`](LANES.md) is the index between them.**
  A preset is a look — numbers and rendered files, identical in every editor — so no command, no
  argument quirk and no track index belongs in one.
- **Update HyperFrames via the registry,** not by hand — `skills-lock.json` tracks hashes.
- **Document, don't manufacture.** Authenticity outperforms.
- **Motion craft is the VOX craft layer, not a global one:**
  [`presets/youtube/vox-collage/motion-craft.md`](presets/youtube/vox-collage/motion-craft.md) is
  read ONLY when that look is invoked by name.
- **Repeated line across takes → use the LAST take.** Don't ask.
- **Clearing out an old job: an external drive first, the Trash second.** A job leaves `projects/`
  whole, never thinned in place, and is closed in the editing app first. A connected external drive
  (Mac: a volume under `/Volumes/` other than the system disk; Windows: another drive letter; Linux:
  `/media/` or `/mnt/`) is the default: copy `projects/<job>/` into a folder on it, prove the copy
  (every file present at the same size), then delete the local folder; ask which drive when there is
  more than one. No drive connected: move the whole job to the Trash and say plainly that it stays
  recoverable until the Trash is emptied and frees no disk space until then. On Windows that is the
  Recycle Bin, reached only through `bash workflows/recycle-bin.sh projects/<job>` (a dry run: it says
  whether the bin can take the job whole), then the same with `--apply`, which proves the job landed
  there. Never a move into a `~/.Trash` folder (Windows never empties it) and never another delete
  command: the others delete permanently when the job is too big for the bin or outside a desktop session.
- **Captions run the whole short-form video by default** — never suppress them under a hook or
  graphic unless told.

## Lab Notes — the locks

One lock per line, each pointing at the doc that OWNS the rule. Read the owner before re-working a
locked area; every one of these was found the hard way.

- **Transcribe ONCE per video.** WhisperX large-v3 → `projects/<job>/transcript/words.json`, reused
  forever (`--force` to redo); `splice.sh` derives the canonical `outputs/<job>.transcript.json`
  through `cuts.json` by pure arithmetic, and nothing downstream re-transcribes. Spelling and brand
  fixes from `transcript-corrections.json` are applied right there, so every consumer inherits them.
  Owner: `rough-cut`.
- **A voice the VAD drops is not a hole, it is INVENTED dialogue.** A second speaker well under the
  main one — a phone speaker, a call demo, a video playing in the room — can fall out of the
  transcript entirely, and the aligner then slides the main speaker's words into those windows, so
  cuts authored off `words.json` there are fiction. `uv run workflows/cut-audit.py <job> --coverage`
  finds the windows (a long gap that still holds sound, beside untrusted words), `--say <t0> <t1>`
  reads what is really in them, and `scripts/realign-spans.py` repairs just those spans. Any segment
  beside spoken digits or on a live call is checked against the raw before it ships. Owner:
  `rough-cut` § Gotchas.
- **Audio = STATIC chain, processed ONCE.** One lossless splice, then one polish: the measured gain
  (`workflows/voice-gain.py`, kept speech → −17 LUFS pre-limiter) into a −6 dBFS limiter, then AAC
  256k. Never dynamic loudnorm (it pumps), never per-segment effects (they click); later re-encodes
  stay ≥ 256k so nothing downstream degrades the voice.
- **A named gain never replaces a broken measurement.** `AMPLIFY_DB=<n>` on `splice.sh` and `--gain`
  on the lane's polish override the measured value, so a measurement that FAILS is fixed at
  `voice-gain.py` (read the ffmpeg error it prints), never worked around with a number — and a named
  gain you ask for is stated in the report and written into RUN.md as a deviation. Owner:
  [`LANES.md`](LANES.md) § step 3.
- **Splice = frame-snapped, J-cut joints, MEASURED boundaries.** Cuts snap to the frame grid
  (un-snapped, concat pads joints with silence until captions desync); joints are 15 ms equal-power
  crossfades over real room tone, never butt-splices, never fades to zero; `refine-cuts.py` and
  `polish-boundaries.py` move every boundary to the word's real acoustic edge and resolve joints
  pairwise (**a continuous split shares ONE boundary; overlapping segments stutter and `splice.sh`
  aborts**). Refinement is NOT idempotent — repair a shipped EDL with `--repair-only`.
- **Broken audio on a finished chat-only render = re-promote the assemble render, never realign.**
  `hf-graphics/renders/final.mp4` carries the in-sync track: [`lanes/chat-only/incremental-graphics.md`](lanes/chat-only/incremental-graphics.md) § Broken audio on a finished render.
- **Both caption presets are LOCKED** →
  [`presets/instagram/talking-head-explainer/captions-style.md`](presets/instagram/talking-head-explainer/captions-style.md)
  + its `captions.py` (mono caps in an 80 % box, on the seam in split or collar + 40 on the face; its gate
  fails on a dropped word, a line across a boundary or an off-band frame) and
  [`presets/tiktok/raw/tiktok-raw-style.md`](presets/tiktok/raw/tiktok-raw-style.md) + its `build.py`.
  Build ONLY from the canonical transcript. Captions are a step-5 graphic: the builder renders the
  caption layer as an alpha overlay under `hf-graphics/captions/`, the plan carries the `captions`
  cell, and the lane's placer lays it on the top graphics track like any other overlay. Both engines
  are PIL + ffmpeg (this ffmpeg has no drawtext, don't install one).
- **Talking Head Explainer face framing = LOCKED, measured.** Hair top 100 px under the y960 seam in
  split (the caption box straddles the seam). `uv run workflows/face-frame.py projects/<job> --modes`
  prints the S and T transforms (EDL mode, kept spans of the raw only); `--verify <program> --plan
  projects/<job>` on the split spans must PASS before review. Fallback when hair can't be measured:
  face-box centre → y1385. Owner: `presets/instagram/talking-head-explainer/layout.md` § 2.
- **The Talking Head Explainer is a LAYOUT ROTATION ON HARD CUTS**, planned per sentence into the
  plan's `layout` map; graphics enact, captures are real, the call to action never leaves split.
  Owner: `presets/instagram/talking-head-explainer/README.md`.
- **Its sound design is written so the first pass starts where a hand sound pass ends:** the literal
  object on visible events, cut-ins from the layout map, kit components writing their own cues.
  Owner: `presets/instagram/talking-head-explainer/sfx.md`.
- **A second voice on a speaker is lifted when the gap is over 3 dB, and announced;** its spans live
  in `transcript/voices.json`. Owner: `presets/instagram/talking-head-explainer/README.md` § Audio.
- **Graphics builds: one comp per graphic; long-form (youtube/default): an emitter only for
  split-part builds**, so a long graphic ships as short parts from ONE shared timeline and a tweak
  re-renders one part. The Talking Head Explainer's kit `build.py` is its data-driven emitter for
  every graphic, still one comp each (`presets/instagram/talking-head-explainer/graphics.md` § 15).
  The base rough cut is NEVER re-rendered. Gotchas: `graphics-build`.
- **THE GRADE GOES UNDER THE GRAPHICS, AND THEREFORE BEFORE THEM** (long-form and the Talking Head
  Explainer's camera footage) — footage graded, graphics untouched, look locked to Autumn-Rec709 at 80/120, no correction step. WHAT:
  [`presets/youtube/default/README.md`](presets/youtube/default/README.md) § Grade. HOW:
  [`LANES.md`](LANES.md) § step 4.
- **Screen-recording FOOTAGE stays bare: no graphics, no grade, unasked.** Footage = the raw walkthrough/demo on V1; a screen-recording GRAPHIC the editor captures is a normal step-5 cell. The plan carries the camera ranges as `graphics_scope`. Owner: [`presets/youtube/default/README.md`](presets/youtube/default/README.md) § Screen-recording footage stays bare.
- **The run is as long as the ask.** A named step runs that step and stops; only a whole-edit ask runs the line through SFX. Owner: `edit-video`.
- **A screen capture is a PLANNED cell, never improvised, and text is never captured.** A `screen-rec` / `screenshot` cell with no file carries `capture` and the build records it (a page: `workflows/page-record.mjs`, headless; a page behind a login is an `app` capture of the signed-in browser; an app: `screen-record.sh`, which fronts it for the take; stills: `window-grab.sh`); it applies when the thing on screen IS the evidence and cannot be re-typed (a folder, an app state, a click) — a prompt, command or quote is rebuilt verbatim as a graphic, a list of tool names is a card. The Talking Head Explainer captures a live product chat as evidence (`presets/instagram/talking-head-explainer/captures.md` § 1). Owner: `graphics-plan` § THE CAPTURE GATE; the look: each preset's own doc (long-form `default-overlay-style.md` § SCREEN-REC SCENES, the Talking Head Explainer `captures.md`).
- **A still of the creator inside a graphic is CAST, never grabbed.** A frame pulled where a beat starts is a mid-word face by construction (eyes half shut, the mouth between sounds). Any cell that shows a real frame of the video carries `hero_frame`, chosen off `workflows/hero-frame.py`'s scored contact sheet BY EYE and extracted by its `--pick` (the proof lands in `review/hero-frames/`); `plan-frames/` are planning evidence, never assets. `validate-plan.py` and `graphics-qa.py` gate it, `edit-review` class 1f reads the render. Owner: `graphics-plan` § THE HERO-FRAME GATE.
- **Centred means the COMPOSED row, never the type alone.** A prop beside a centred line is part of the line: words and prop are one inline box the browser centres, its slot reserved from frame 0, and the whole full-screen box sits on the frame's centre in both axes. `graphics-qa.py`'s `centre` check measures the box and every ink row on the render's fullest frame (the box's horizontal centre and a text punch-cut's rows fail past 40 px, a scene's rows warn); the Stage-4 probe reads the union rect first. Owner: `presets/youtube/default/creative-moves.md` move 2 § CENTRED MEANS THE COMPOSED ROW.
- **The craft rules are measured, not eyeballed:** density (long-form, youtube/default) is a cadence
  and a SPREAD (full-screens never 40 s of runtime apart), entrances and exits come from the registry in code (cards rise,
  objects pop, the default exit is `riseOut`, and type NEVER pops — it rises with scissors, or slams
  in Impact), slides and large movements render with motion blur, a full-screen graphic is a short
  SCENE and not a card (at least two phases, at least one visual that is not type, and a camera
  move), type over a scene RACKS THE SCENE OUT (a blur ladder of pre-blurred clones under a dim,
  never a filter tween), overlays sit in the low band and side callouts are MEASURED off the head
  (`uv run workflows/chin-line.py <raw>` prints the floor; add `--edl <cuts.json> --from <t> --to
  <t>` for the callout zone — 60 px off the ear, 80 px off the frame edge, the side with more room),
  accent props glow while type does not, a readable graphic holds 2–3s, and arrowheads are computed
  from the path's end tangent. Owners: [`creative-moves.md`](presets/youtube/default/creative-moves.md),
  [`animations.md`](presets/youtube/default/animations.md) and
  [`default-overlay-style.md`](presets/youtube/default/default-overlay-style.md). The Talking Head
  Explainer shares the registry (words rise, type never pops) and the 2–3 s readable hold
  (`presets/instagram/talking-head-explainer/graphics.md` § 13); its own: hard cuts between layouts
  (no opening zoom-out, no emphasis push-in) and at most 2 full-screens per 120 s
  (`presets/instagram/talking-head-explainer/layout.md` § 2 and § 5).
- **Completion is checked against your ORIGINAL REQUEST, not just the graphics plan.** A plan that
  omits a requirement cannot be its own proof of completion: RUN.md carries the coverage and the
  final handoff reconciles it against the saved timeline. Owner: `edit-video` § Request coverage.
- **Live app state is READ before a deictic is interpreted, on every lane.** "the section I marked",
  "the highlighted clip", "at the playhead" → query the finish surface's marks, selection and
  playhead first, then analyse; clear marks after acting. Owner: `edit-video` § Where the run STOPS
  on its own; the lane's calls live in its app skill.
- **Live state that disagrees with RUN.md is your hand edit, never a failed write.** A value on the
  timeline that differs from what the run last wrote is reported and left alone; a write is re-applied
  only when its own readback proved it failed. Owner: `edit-video` § THE FIRST THING, ALWAYS.
- **On-screen secrets are SWEPT, never spotted by eye.** A job with screen-recording or live-call
  footage lists what it must not show in `projects/<job>/pii.json` under three keys: `needles` (numbers
  and keys), `phrases` (words, matched from the start of a word, so 'cancell' covers cancelled and
  cancelling) and `any_number` (7 flags any phone-shaped number). `uv run workflows/pii-scan.py
  projects/<job>` sweeps the kept spans and writes `review/pii-scan.json` plus a contact sheet;
  `--raw <file> --all` sweeps a capture take or an exported draft into its own
  `review/pii-scan-<name>.json`. Record app windows with `workflows/screen-record.sh --preflight
  projects/<job>/pii.json`: it refuses a take (exit 4) while forbidden text is in the window or drawn
  over it. Confirm hits by eye before anything is blurred (a clean sweep only means the OCR read
  nothing), and re-run the sweep after any re-cut. Owner: `edit-video` § Step 0, item 9.
- **A cut change after step 3 is a declared RE-CUT.** The cut is locked once you have watched it, so
  a later fluff pass re-lays the timeline from the new EDL, re-applies the audio polish, and then
  `uv run workflows/ripple-cut.py projects/<job> --from <old EDL>` (dry run, then `--apply`) re-times
  the transcript clock, the plan rows, the placement, the SFX cues and the text metas THROUGH THE
  SOURCE; the lane's placers re-place afterwards and every ORPHANED / STRADDLING / RE-BAKE row it
  names is decided by hand. Owner: `edit-video` § Where the run STOPS on its own.
- **A second camera is lip-sync-MEASURED before it is laid, and the offset drifts.** A screen
  recorder's facecam is not in sync with its own mic and the error grows across a long take, which is
  invisible in a corner bubble and unmissable full frame: `uv run workflows/lip-sync.py <cam>
  --audio <mic-source> --mouth-crop <w:h:x:y>` fits the lag across the take and each camera clip's
  in-point slips later by its own lag. The crop is measured off one frame of the cam and is not
  optional: without it the tool answers UNMEASURED (exit 2) instead of guessing. Owner: `rough-cut`
  § Gotchas.
- **A video that claims it was edited in one pass is BUILT that way.** Nothing copied in from an
  earlier job (comps, renders, `graphics-plan.json`, harness files, assets); preset reference files,
  `assets/` and system fonts only, captures fetched fresh. Owner: `edit-video` § Step 0, item 8;
  recorded in RUN.md as a constraint.
- **Per-app locks live with the app**, in `lanes/<app>/lab-notes.md`. Read the one for your lane
  (Premiere's: its § Every step plus the section for your step); nothing in it applies to another app.
- **hyperframes is PINNED and bumped deliberately** (`hyperframes@0.8.16`, matching `setup.sh` and
  `SETUP.md`). Never `hyperframes upgrade`; update the vendored skills through the registry so
  `skills-lock.json` stays honest.

## Your rules

The user's own standing instructions, from [`my-rules.md`](my-rules.md) (an update never changes that
file). Where one conflicts with a rule above, theirs wins for their videos.

@my-rules.md
