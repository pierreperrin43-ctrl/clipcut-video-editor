---
name: rough-cut
description: "Rough-cuts videos from raw clips, every format (short-form reels and long-form YouTube alike, the universal step 2). Transcribes with WhisperX (large-v3 + wav2vec2 word-level alignment), kills filler + dead air, keeps only the essential lines, stitches with FFmpeg. No captions, no B-roll — just a tight rough cut ready for final polish. Triggers: rough cut, cut this video, trim this, chop this up, rough-cut, make a rough cut, tighten this cut. (Whole-line phrasings — 'edit this video', 'do the whole edit', 'edit the latest project' — belong to `edit-video`, the orchestrator: this skill is step 2 of that line.)"
---

# Rough Cut — Transcript-Driven Edits

Raw talking-head clips into a tight rough cut: you transcribe, you decide the cuts, FFmpeg stitches. The goal is the **shortest reel that still delivers the value.**

## How to Trigger
- **"rough cut [job name]"** → that job folder; **"rough cut"** / **"cut this reel"** with no job named → the newest job folder (a path picks that folder)

---

## Folder Contract

**This skill starts at transcription.** Creating the job folder, copying the raw into `projects/<job>/raw/` (never moving it) and naming the job are step 1, Intake, owned by `edit-video` (layout + naming: CLAUDE.md § Folder Structure and § Job naming). No job folder yet → do intake first; if the content isn't obvious before transcribing, use a provisional folder and rename it before the splice.

Three durable paths get written under `projects/<job>/`: `transcript/words.json` (the canonical transcript), `transcript/cuts.json` (the EDL), `outputs/<job>.transcript.json` (the cut-aligned caption transcript). Scratch lives in `/tmp/video-editor/<job-name>/`, which macOS clears — never depend on anything living solely in `/tmp`.

**Intent is derived, never asked.** If `intent.md` exists, read it. Otherwise read the FULL transcript first and work out the hook (the strongest curiosity/tension line, often filmed mid-take and re-orderable to the front) and the takeaway (the one thing the viewer should leave with), then cut to serve those. No usable dialogue? Sample frames (`ffmpeg -ss <t> -i <clip> -frames:v 1 <out.png>`) and infer the subject + arc from what's on screen. State your read in one line of the report.

---

## The Edit Philosophy (non-negotiable)

**Short and snappy, max value per second.**

Every cut decision runs through this filter: **does this line deliver value?** (if not, kill it) · **is this the tightest version?** (if not, use the shorter take) · **would a viewer skip past this?** (if yes, it's dead).

**RELEVANT IS NOT NECESSARY — the #1 filter (2026-08-28, after a first cut ran
3:32 that should have been 2:00):** "just because it's relevant doesn't mean that it's
necessary... stuff that's like okay, cool, good to know, instead of need to know right now,
is fluff." A line survives only if the viewer NEEDS it right now, for understanding or for the
flow of the script; good-to-know context, how-I'll-do-it teases, second statements of a point
already made and warm-up framing are all relevant and all dead, and a prerequisite aside that sends
the viewer off to do a step the video is about to show anyway — when the two lines around it join
cleanly without it, it goes. (This is not the same as a preamble that sets context or a setup clause
its own next line depends on: those stay.) **The kill rate is an OUTCOME,
never a target (2026-09-04):** emphasis-heavy multi-take footage has landed at 60-75%
killed, a take where the speaker nailed the script might lose 20-30%, and whatever total the
necessity question produces is the right cut. The red flag is a kept line that fails that
question, never "kept more than half". An intro especially is pure momentum
(claim → problem → rules → stakes → go) — every beat that doesn't advance it goes.

**Format is auto-detected from the raw footage, never asked** — resolved at `edit-video` Step 0 and written into RUN.md (on the Talking Head Explainer, read its [`story-and-cut.md`](../../../presets/instagram/talking-head-explainer/story-and-cut.md) before the kill pass); probe every clip only when this skill runs alone (`ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0 <clip>`): **vertical** (height > width) → short-form, **horizontal** → long-form YouTube. State the detected format in the report.

**Target length depends on that format:**
- **Short-form** (9:16 Reels/TikTok/Shorts) → aim **1–2 minutes**, the target *after* ruthless cutting, not permission to ramble. If the value fits in 40s, ship 40s.
- **Long-form** (16:9 YouTube) → **no length cap**, but no cap is not license: the necessity filter still governs. Cut for retention and structure, not to hit a number.

---

## Auto-Kill Rules (always apply)

When building `cuts.json`, automatically remove:

| Kill | Why |
|------|-----|
| Filler words: *um, uh, like, you know, so yeah, basically* — at a run's edge or in dead air | Dead weight. **Inside a flowing phrase a one-word filler STAYS (your 2026-09-13 hand pass):** you put back every mid-phrase filler kill I had made ("I said, *uh*, I was like", "*you know*, when it came to *like* the pricing", "about, *you know*, what the other team") and kept "finally, *uh*, before we wrap up" whole. Each mid-phrase kill costs a joint, and the joint is the bigger defect. A search PHRASE that carries its own pause ("let's see", "it seems to me", "how do I put this") is not a filler: it goes (rows below). |
| Stutters + false starts: *"I- I was gonna-"*, and a token that is a prefix or near-spelling of the NEXT word (a product name started, then said in full: *"Prem… Premiere Pro on max"*, 2026-09-13) | Breaks flow. `cut-audit.py` prints `⚠ possible false start` on the prefix case (2 hits in a 2,000-word section, one real). |
| Restarted takes | Keep the **last** take, kill the rest — you always want the latest take of a repeated line (warmest delivery). Don't compare takes. |
| Emphasis echoes: the same claim re-stated for punch (*"one prompt, one shot, one go... it was literally one prompt..."*) | Keep the STRONGEST single statement of each claim; every echo after it is fluff. A hook montage of restatements collapses to one claim + at most one punch ("One shot."). **The weaker line right BEFORE its stronger restatement is the echo** ("honestly, that part's a small thing. I'd much rather pay for the upgrade…" → the first dies, 2026-09-13). **Two things are NOT echoes (2026-09-13 hand pass):** the LANDING restatement that closes an argument — thesis ("I just prefer where this tool is going"), evidence, then "so overall I still prefer this one, and my gut says the same": the second is the payoff, keep the bookend — and a deliberate back-to-back repeat for emphasis ("it stopped right away. I hit the wall right away."), which is delivery.· the engineering archive. |
| A rhetorical question the speaker answers with no new claim: *"Is it perfect? I really don't think so."* | Filler in the shape of an argument (2026-09-13 hand pass). |
| A second hedge opening the sentence after a hedged one: *"To me, I feel like this one is overrated. It seems to me, there are two real options here…"* → kill "it seems to me" | A restart in different words; the thought already has its hedge. |
| A wrong connective: *"plug and play, but I also wrote the docs"* → kill "but" | The line stays, the hinge pointing the wrong way goes. |
| Reading-aloud searches on a screen recording: *"totaled about, let's see, 1,200 credits"* → kill "let's see" and the pause it sits in | The speaker is looking, not talking. |
| A second CTA in the outro: *"hope to see you in the next one if you want to stick around. If not, that's all good too."* | One CTA per video; the hedged repeat weakens the real one (2026-09-13 hand pass). The closure rule below still protects the sign-off around it. |
| Silences ≥ 0.65s (MEASURED on the envelope, AND read off the aligner's gaps then verified by ASR) | Dead air. `polish-boundaries.py` splits any interior quiet run ≥ 0.65s whatever the timestamps say — the aligner can stretch a low-probability word across a pause so no inter-word gap exists. Author the transcript-gap split anyway; the polish pass is the net. **A pin protects a segment's boundaries, not its interior (2026-09-13):** pinned segments are split too; `"keep_pauses": true` is the opt-out for a deliberate pause. **On a screen recording the envelope cannot see the pause:** breath and room noise sit above floor + 10 dB, so a 940 ms pause after "So" and 1.4 s inside a read-off-the-screen cost line shipped and you razored both out by hand. So `cut-audit.py` also takes every aligner gap ≥ 0.9 s between two kept words (0.9 on paper is about 0.65 heard: the aligner ends words early and starts them late, and the hand pass left eight 660–800 ms paper gaps alone), transcribes the gap, and splits only when nothing is heard in it — a gap with a word inside that the aligner skipped (a mumbled "like, the other one"; the "that" after "So") stays, with a `⚠ holds speech the aligner skipped` line: that word is a hidden false start or filler to kill by hand. **Known miss:** a pause the aligner has no words around (WhisperX misplaced the words while you read the screen; the 1.4 s pause sat in breath noise) is found by neither pass — a screen-recording passage where the speaker reads the screen is checked by ear on the bounce.§ mechanism (8) · the engineering archive. |
| Tangents + asides that don't serve the hook/takeaway | Viewer time |
| Throat-clears, "okay let me start over" | Production noise |
| Orphan low-prob word before a kept take | A lone low-confidence word (prob ≲ 0.3) with a ≥1s gap right before a kept take is a false start WhisperX half-missed. Kill the fragment and start the segment at the real take; never keep the orphan as its own segment. |
| Preamble before the hook lands | Every reel opens ON the hook |
| Trailing verbal tics after a landed point: *"...5X more usage, okay?"* → cut at "usage" | The point landed; the tic is a ~0.5s tax. Mid-sentence tics are rhythm — keep those. A trailing tag directly before the section's landing line stays too ("…still the best option. Right." → the landing line, 2026-09-13): it is the beat before the payoff. |
| Meta-signposts about the video's own structure: *"so now what I'm going to do is cover..."*, *"you can skip to the next section"*, and how-I'll-do-it teases: *"my plan is to build a preset"* | The content announces itself. All three die — preview, skip-ahead courtesy, AND method tease (2026-08-28: "it's just fluff... obviously I'm gonna explain how I do it later in the video"). **A signpost that turns a corner STAYS (2026-09-13 hand pass):** a section close ("that's my final thoughts on this", "yeah, that would be my breakdown on this video") or a numbered step ("firstly, let's start with the numbers", "finally, before we wrap up") carries the viewer across the cut; I had killed both closes and you put both back. What dies is the announcement that moves nothing. |
| Self-referential flexes: *"personally, I'm on the $200 a month plan"* | Status talk, not information. |

**The closing beat is content.** The VIDEO's own filmed closure and handoff — the sign-off, the goodbye, the handoff into whatever comes next — is not a disposable meta-signpost (the goodbyes inside an embedded demo call are not it: rule (c) below): keep it complete unless the user explicitly asks to remove it, and never reduce the closing passage to its final sign-off. Inside that passage the normal rules still apply: pauses, tics, false starts and retakes go, and a repeated sign-off collapses to the last take.

**Preserve the creator's cadence.** Don't surgical-kill every "like" — some are rhythm, some filler. Taste call.

**The keep/kill line (your 2026-07-29 hand pass): persuasion and personality are CONTENT — meta-narration is not.** Objection-handling ("can I do this on the free plan?"), the pitch, the value stretch, the walk-back for budget viewers, section preambles that set context — all of it stays, even in an "essentials only" cut. What dies is talk *about the video*, talk *about the creator's status*, and tics. Cut harder = tighten inside lines before deleting persuasion beats.

**A follow-along tutorial keeps what the viewer needs to keep their place (your 2026-09-19 hand pass on a walkthrough, where you put back 9 of my kills).** The viewer is DOING the build alongside, so these read like talk but are content: the step transition that says where we go next (*"So what we can do now is go to our…"*); the location answer inside a search (*"go to settings, I believe it's in, yeah, Settings and then API keys"*: the reading-aloud kill above is for a filler search phrase that locates nothing, never for the one that tells them where the thing is); the practical instruction even when it restates a line (*"so if you just click that link down in the description, it will be there for you"*); a short reaction that proves a claim about the tool (*"export, okay cool, that was really quick"*); the agent's reply read aloud as proof the setup took (*"53 tools, API key, default voice, Jarvis clone"*); the line that says WHY a step is done (*"that's like a clean voice sample"*). On a LIVE CALL inside a follow-along tutorial (the viewer is setting the call up alongside) the wait for the phone and about a second before and after the AI speaks stay: a call that snaps line to line reads staged. A demo call embedded in an explainer is the other case, cut to its proof beats: rule (c) below. What still goes on a walkthrough: a repeated *"there we go"*, a mid-phrase *"we're going to"* restart.

**Four more keep/kill rules, universal (the Talking Head Explainer's hand passes, 2026-09-20..22; its [`story-and-cut.md`](../../../presets/instagram/talking-head-explainer/story-and-cut.md) § 4.11-4.13 and § 5.6 carry the evidence):**

- **(a) Prosody decides a tail.** Never end a kept line on a rising mid-breath comma: the ear hears a sentence cut off, however clean the joint. A list tail said in the same breath ("et cetera", "and so on", "you name it") carries the sentence's falling melody, so it belongs to the sentence: keep it to where the voice falls and `pin_out` that OUT. Cut a tag only after a pause of 200 ms or more AND a terminal fall on the word before it. This is decided before the trailing-tic row above, which is for a point that has landed; a rising comma has not.
- **(b) Specific examples stay; a generic capability list goes.** A concrete use the viewer can picture is evidence and stays whole. A generic capability list tacked onto a claim after the proof ("…that can handle calls, tasks, anything, you name it") restates what was shown and dilutes the claim: it goes, the claim ends on its landing noun, and its graphic goes with it (a line is never kept to save a graphic).
- **(c) An embedded demo call (not the follow-along live call above) is cut to its proof beats:** the announcement, the other party's substantive lines, one reaction. The ring, the pickup, the greeting, direction asides to the agent and the goodbyes go: they are the mechanics of a phone call, the viewer needs the payoff, and the call ends the moment its proof lands. A call that IS the cold open keeps its greeting (without it the viewer is dropped into nothing).
- **(d) The other party's confirmation of an action is proof, not an echo:** keep it whole, to its own last word, with the question that set it up. The emphasis-echo row is for a speaker restating your own claim; a second party saying back what it will do is the beat where it is seen to understand and act.

---

## The Pipeline

### Transcribe

Find the job folder, then:

```bash
bash .claude/skills/rough-cut/scripts/transcribe.sh <job_dir>
```

WhisperX (large-v3 ASR + wav2vec2 forced alignment) writes true word-level timestamps to the canonical `projects/<job>/transcript/words.json` (plus a scratch mirror under `/tmp`).

**First run builds the venv** at `~/.cache/video-editor/whisperx-venv` (several GB, several minutes) plus the large-v3 + wav2vec2 weights; a `.deps-ok` sentinel rebuilds cleanly after an interrupted install. Later runs start in seconds.

**Hardware is auto-detected:** an NVIDIA GPU (Windows/Linux) runs CUDA float16 behind a fallback ladder (cuda float16 → cuda int8_float16 → cpu int8), so a broken CUDA stack warns and degrades instead of blocking; Apple Silicon stays CPU int8 (locked — GPU torch is flaky there). `WHISPERX_DEVICE=cpu|cuda` overrides. Details: the engineering archive.

**This is the ONE transcription for the entire pipeline — rough cut AND finishing captions.** The canonical `words.json` is **reused forever**: re-running `transcribe.sh` skips WhisperX (`--force` to redo). Nothing downstream transcribes this footage again — the locked caption presets and `graphics-plan` consume the derived `outputs/<job>.transcript.json` instead (see Splice + Handoff).

**Add `--diarize`** to label each word with a speaker: needs `HUGGINGFACE_TOKEN` in env and the pyannote/speaker-diarization-3.1 model accepted on HF.

**One file that is not a job's raw (a pickup re-record, a spliced audio): `bash .claude/skills/rough-cut/scripts/transcribe.sh --file <audio|video> --out <words.json>`.** Same venv, same CUDA/CPU ladder, same `words.json` shape (`{clips: [{clip, path, duration, words: [{w, start, end, prob}]}]}`), written to `--out`. It never reads or writes any job's `transcript/` and never reuses a transcript. Never word-align with an inline whisperx heredoc against the venv.

**A call on a phone speaker: transcribe with the defaults, then let `--coverage` find the drops.** Whisper loses a second voice that sits 8–10 dB under you, and wav2vec2 then fits your reply over that voice's audio. It is usually NOT the VAD: measured 2026-09-23 on all three reference phone-call jobs, the VAD scored the AI's lines 0.76–1.0 on your-job-pa and long-form, and Whisper dropped them inside its 30 s decode window. `transcribe.sh` has `--chunk-size N` and `--vad-onset X --vad-offset Y`, but every setting only moves WHERE the drop lands: on the 53-minute long-form `--chunk-size 20` fixed both repaired windows and dropped about ten AI lines the default kept; `--vad-onset 0.3 --vad-offset 0.2` brought back four lines the default had silently lost and dropped four others; windows under 20 s invented "Thank you." in room tone. So neither knob is a default or a whole-job fix. The repair stays `cut-audit.py --coverage` → `--say <t0> <t1> --boost --spans-out` → `realign-spans.py` (§ Gotchas). For a second opinion on one flagged window: cut the slice with ffmpeg, `transcribe.sh --file <slice.wav> --out <scratch.json> --chunk-size 20`, and add the slice's start to every time.

**Engine experiment (2026-09-13, not the default):** `scripts/transcribe-scribe.py <job>` transcribes with ElevenLabs Scribe v2 ($0.22/hr, `ELEVENLABS_API_KEY` in `.env`) into the same `words.json` shape as `words.scribe.json`; `scripts/compare-transcripts.py` diffs it against the WhisperX transcript on text and per-word timing and cuts listen-and-judge snippets. `--canonical` swaps it in so the rest of the line runs on it for a real A/B. **Measured on your-job (9.1 min, 2026-09-13): Scribe wins the WORDS (keyterms fixed both "clawed"→Claude, no low-prob words) and loses the word ENDS: every clause-final word's `end` runs to the next token, so pauses land inside words (silencedetect: speech on "accurate." stops at 390.38, WhisperX ends it at 390.45, Scribe at 393.02; 15 long-span flags vs 5; 13 of 85 pauses >0.5 s swallowed whole). Starts agree with WhisperX to 16 ms median. Not a drop-in: WhisperX stays the lock. ElevenLabs' Forced Alignment API on the Scribe text (`words.fa.json`, same day) fixed 3 of 7 verified sentence ends and left 4 at 1.4–1.7 s late with no loss-score warning, still swallowing 12 of 85 pauses, so it does not beat WhisperX either; both ElevenLabs engines beat wav2vec2 only on numerals ("$4,300" lands on the audio). The viable hybrid is Scribe text + ends re-derived from the audio (last speech frame inside the span).**

**Then check the transcript's COVERAGE, before a single cut is authored:**

```bash
uv run workflows/cut-audit.py <job_dir> --coverage
```

WhisperX drops a quiet passage (a second voice on a phone speaker, usually inside Whisper's decode
window rather than the VAD: the phone-speaker paragraph above), and wav2vec2 then force-fits the neighbouring text over
that window — it does not leave a hole, it INVENTS dialogue there (the bullet in § Gotchas). No
boundary check downstream can see it, because the aligner filled the span. This reads the transcript
against the raw waveform: every inter-word gap that still holds sustained sound, and `⚠ VAD DROP`
where the words beside such a gap are untrusted too (a cluster of p ≤ 0.35, or a numeral squeezed
into a time nobody could read it in). A gap alone is noise — 202 of them on one 53-minute take — so
only the compound tell is flagged, about a dozen lines to read. Hear any window with
`--say <t0> <t1>`, and repair a real drop at the source with `scripts/realign-spans.py` (§ Gotchas)
before authoring anything over it. Exit 1 means there are ⚠ lines to read, not that the take is bad.
**A ⚠-free run is not a covered transcript:** the tell is compound by necessity (a gap alone fires on
every quiet working stretch), so a drop whose neighbouring words happen to score high has nothing to
fire on and prints as a plain `·` candidate line. On a take with a second voice, a phone speaker or a
live call, read the `·` lines too — the only complete net is the bounce proof (§ The proof), and it
comes after the cut is laid. Each ⚠ gap is then slice-transcribed: when no word is heard it prints
`· sound, no speech heard` and is not counted (a voice far under the speaker can hide from a plain
pass, so check a suspect gap with `--say <t0> <t1> --boost`). Once a gap is checked by ear,
acknowledge it: `uv run workflows/cut-audit.py <job_dir> --ack <t0> <t1> --note "phone ringing"`
appends it to `transcript/coverage-ack.json`, and it then prints `· acknowledged: <note>` and is never
counted again (two ring-only gaps were re-flagged ⚠ on every run after their repair, 2026-09-20).

**A job with a second voice records its spans once the repair is verified:** `transcript/voices.json`,
`{"spans": [{"clip": "<raw file>", "start": <raw s>, "end": <raw s>, "voice": "phone"}]}`, on the RAW clock
(so it survives every re-cut), each span widened to the WHOLE reply the cut keeps (a reply kept longer in a
hand cut widens its span). The Talking Head Explainer's captions colour those lines from it, and the step-3
lift reads it (`workflows/voice-gain.py --second-voice`, Premiere `audio-polish.py --lift`).

**Run in background** over 3min of total clip length. Claude Code: `run_in_background: true` + Monitor. CPU timings: ~30s of clip = ~10-20s wall (first run slower, model downloads), ~5min = ~2min; CUDA is several times faster.

### Author the cuts

Read `projects/<job>/transcript/words.json`. Each clip has a `words` array of `{w, start, end, prob}` (plus `speaker` under `--diarize`).

Apply the auto-kill rules and the edit philosophy. Output `/tmp/video-editor/<job-name>/cuts.json` (on Windows Git Bash maps this to `%TEMP%\video-editor`; write `cuts.json` through the Bash tool with a heredoc, since a file tool may resolve `/tmp` to `C:\tmp`) — the path `splice.sh` reads, overwriting the job copy from it (see Gotchas) — in this shape:

```json
{
  "segments": [
    { "clip": "clip-02.mov", "start": 1.24, "end": 4.60, "transcript": "Are you still paying a VA three grand a month" },
    { "clip": "clip-01.mov", "start": 12.20, "end": 18.80, "transcript": "..." }
  ]
}
```

**Timestamp rules:**
- Trust WhisperX timestamps for WHICH words to keep, not for edges: word STARTS run ~50-100 ms late vs the real acoustic attack, word ENDS run early vs the decay. Exact boundaries are dialed by the refiner (below), not by you.
- **A low-probability boundary tail means the TIMESTAMP is fiction, not just soft (your-job, 2026-08-28).** When a boundary word or its 1-2 neighbors carry prob < 0.3, measure the real edge on the raw envelope with a WIDE window — up to the next raw word, NOT `word.end + 300 ms` — and require a sustained drop before cutting; a capped search lands mid-word and chops the line. Related: a mid-speech "graft" is only legitimate when the adjacent word is KEPT, so a graft against a KILLED region means the measurement failed. **Both are enforced by `polish-boundaries.py` — run it every job; its ⚠ lines are these cases surfacing.**
- **Merged repeats: an immediately repeated word ("However... However,") can collapse into ONE transcript entry spanning every utterance**, so a cut keeping it keeps the stutter. `transcribe.sh` flags long-span words (> 1.0s, and > 0.5s at p < 0.5); the refiner snaps a segment starting on one to the LAST utterance, trims one ending on it to the first, and warns on mid-segment ones (split the range at that word). **On screen-recording footage (OBS) the auto-fix fails SILENTLY** (1 caught of 4 real), so treat every ⚠ long-span word on a boundary as unverified there: measure the raw with a 10 ms RMS envelope, then pin the boundary as explicit start/end + `"no_refine": true`, or the refiner searches from the bogus word end and undoes it. Interior ⚠ words and quiet runs under ~0.3s are fine.§ mechanism (5).
- Start on the first word you want, usually `word.start - 0.03` to `0.08`; end after the last, usually `word.end + 0.04` to `0.10`.
- **Segments must never overlap in the source — a continuous split shares ONE boundary time.** Split a take with nothing removed between the halves and the pads point at each other: `word.end + 0.08` out and `next_word.start - 0.04` in put the SAME frames in both segments, played twice as a 1-15 frame stutter. Write `"end": T` on one and `"start": T` on the other, one shared value in the inter-word gap. Padding is for a real cut, where the pads open outward into different silences. `refine-cuts.py` repairs overlaps and `splice.sh` hard-aborts on survivors, naming YOUR segment numbers. **But adjacency in the WORD LIST is not continuity (your-job, 2026-09-18).** Two kept phrases can be neighbouring words and still have a long silence between them — a hold on a phone call, a wait for a render. That silence is a dead-air KILL, so the pair gets two normal padded edges (`w.end + tail` / `w.start − lead`) and the silence is cut. Share ONE boundary only when the inter-word gap is under the dead-air threshold (0.65 s): a shared boundary keeps every frame between the two words, so merging across a long gap silently ships the whole pause (51 s on one job, a 19.5-minute first cut that should have been 14.7). `refine-cuts.py` and `polish-boundaries.py` now gate continuity on that gap and print `⚠ adjacent words but N s of silence between them`; before that they classified the joint on adjacency alone, skipped measuring BOTH its edges, and only `dead-air-qa.py` caught it — after a splice, three cycles later. **And naming the joint is not repairing it:** on that one boundary the refiner's distance cap is waived too (the authored cut is legitimately seconds from its own word, so the cap rejected the very move the warning announced and `cuts.refined.json` still carried the whole pause). A warning must not name a repair the file did not get.§ mechanism (6).
- Don't cut mid-word; a clipped transition means adjust `cuts.json` and rerender. Segments CAN cross clips in any order.
- **The graft — splice restarts mid-sentence, don't cut at sentence boundaries.** When the speaker restarts a thought ("...we need Claude Code. Okay, we need Claude Code for it to..."), end segment A *through* the repeated phrase in take 1 and start segment B in take 2 *right after* the restated words (at "for it to..."): one continuous sentence, zero duplication. Prefer-last-take governs *full retakes*, the graft governs *mid-thought restarts*.
- **Orphaned connectives — when you kill a line, kill the words that answered it (you caught this on your-job, 2026-08-28).** Rebuttal/contrast frames ("But the reality is...", "That's why...", "So instead...") answer the PREVIOUS sentence, so keeping the counter while cutting the claim leaves a "but" contradicting whatever now sits before it. Re-read the cut sheet as one continuous script and check every segment's FIRST few words: does the connective still refer to something that survived? If not, start the segment after it. Same check on deictics. **And the reverse: a beat that only makes sense WITH its framing clause dies whole when the clause dies.** **The framing clause of a KEPT beat is part of the beat (2026-09-07):** "and after receiving a ton of feedback from my customers, my audience, my community" was killed as good-to-know credibility, and the next line, "I noticed one huge problem...", is its ANSWER, so "I noticed" hung off nothing ("that fucks up the flow"). Before killing any "after / because / from my ..." setup, read the line that follows: if it opens with noticed / found / realized / learned / saw, the setup stays. The necessity filter is for echoes, teases and warm-up, never for the cause half of a cause-and-effect sentence.
- **Tails are uniform (measured decay + 70 ms) EXCEPT at a landed line, which carries `"beat": true` and keeps up to 250 ms of the speaker's OWN pause (2026-09-13 hand pass; narrows the 2026-08-31 retirement of authored air).** What you retired on 08-31 was INVENTED air: pads typed into the EDL (`"air": 0.4`) that read as weird extra space; that field stays inert. What your 09-13 hand pass added is different and measurable: at 11 of 74 boundaries you lengthened the tail to 130–390 ms, every one at a verdict ("I feel like OpenAI is kind of evil."), a comparison set-up before its verdict ("$100 a month versus $200 a month," → "for me," → "I would much rather pay"), a section close ("that's my final thoughts on this now", "that would be my breakdown on this video"), or the section's last line ("Peace."); the other 63 you left at 70 ms, including every mid-argument sentence end that flows into its continuation. So mark exactly those segments `beat` (the last segment of a section always is), never a sentence end inside an argument; `polish-boundaries.py` and `cut-audit.py` cap the beat at the next word's onset, never manufacture silence, and a split part inherits the beat only on its last piece. If a later hand pass trims beats back, this bullet goes.§ mechanism (7) · the engineering archive.
- **The antecedent of a surviving connective is content, and so is the connective (2026-09-13 hand pass).** The reverse of the orphaned-connectives rule: "So I think you would need to be on a $100 per month plan" was killed as an echo of the next line, "because if you're on a $100 a month plan, you could probably do five of these a week", and the surviving "because" then answered nothing, so you put the line back. Before killing a line, read the NEXT surviving line's first words: *because / so / which is why / that's why / and also* point backwards. Sentence-initial *But / And / So* that answer the previous surviving line stay ("…about $92 in API cost. **But** I was on the $20 a month plan"), and a list marker survives even when the sentence restarts after it ("Claude output better. **And I also,** the video editor system is built on Claude conventions": the "also" tells the viewer a second reason is coming).
- **A reason for an earlier claim moves up next to the claim (the move).** "I think I was also running the edit on medium or maybe high… part of the reason why the edit didn't come out perfect" was filmed four minutes after "the project is more optimized for Claude… it probably could do a better job" and belongs beside it, before "I actually did run a second version"; it was moved in the authored cut and survived the hand pass untouched. Segments can cross the raw in any order: when a later passage answers an earlier point, move it, then check the connectives on both sides of the hole it leaves.
- **At a fused joint the dip's frame belongs to the killed word (2026-09-13 hand pass).** Where a killed word runs straight into a kept one, the boundary sits on the frame boundary at/before the envelope minimum for an OUT and at/after it for an IN; the outward frame plays the first 10–40 ms of the killed word ("benchmarks|okay": −31 dB on the outward frame against a −55 dB dip). `cut-audit.py --grid` snaps inward now; you had moved five OUTs and two INs by hand to exactly those frames.
- These pads are a starting point: `splice.sh` runs `refine-cuts.py` first, which measures each boundary word's acoustic onset/offset on the raw and nudges the cut just outside it (in = onset − 40 ms, out = offset + 50 ms), clamped inside the local gap and capped relative to its own word (250 ms lead, 300 ms tail); continuous splits get one shared boundary, joints resolve PAIRWISE. Watch the `[refine]` report — `cut was N ms INTO "word"` lines are clipped attacks it saved. `REFINE=0` disables the pass; `"no_refine": true` pins a segment (an overlap against a pinned side moves the UNPINNED side only). Mechanics: the engineering archive § mechanisms (4) and (6).
- **Refinement is NOT idempotent — repair a shipped EDL with `refine-cuts.py --repair-only`, never a second full pass.** The refiner measures from the authored cut, so a second pass re-measures from the moved boundaries and drifts tails further out (+0.4s observed). `--repair-only` runs ONLY the pairwise joint resolution with zero re-measurement, so only overlapping joints move.

Include the `transcript` field on every segment so the cut sheet reads on its own.

### Splice (EDL-only by default)

**The editing-app finish IS the default (2026-08-28): a bare "rough cut" with no lane named means EDL-only mode + automatic Premiere handoff — NEVER render:**

```bash
RENDER=0 bash .claude/skills/rough-cut/scripts/splice.sh <job_dir>
```

~8 seconds: boundary refine + frame-snap + persisted EDL + corrected canonical transcript, no ffmpeg encode. Nothing on an editing-app path reads the flat MP4. Go straight to the timeline (clients: `capcut` / `davinci-resolve`), then the **audio polish** (step 3, the house chain as clip effects — see `premiere-pro`). The full render below is **only** for the chat-only/HyperFrames lane, never inferred: it runs when a client with no editing app has explicitly said to do it in chat.

```bash
bash .claude/skills/rough-cut/scripts/splice.sh <job_dir>
```

Dials every boundary against the raw audio (`refine-cuts.py` — see Timestamp rules), then writes `outputs/<job-name>.mp4` in a **single FFmpeg filtergraph**: one `trim`/`atrim` per kept segment → `concat` → static gain → limiter, encoded once. Audio rides through **lossless (PCM in-graph)** and is polished **once** on the assembled track (measured amplify from `workflows/voice-gain.py`, kept speech → −17 LUFS pre-limiter → −6 dBFS hard limiter → AAC 256k), **never** per-segment (boundary click-pops). Video and audio trim from the same in/out, so A/V stay locked by construction.

**`splice.sh` runs `scripts/audio-qa.py` after every splice** (joint clicks, ambience continuity, silence gaps, limiter pressure) and never fails on it (`|| true`), so its ⚠ lines are easy to miss: read them. A limiter-pressure warning is acted on only when it is audible, and never by naming a gain (the measured-gain lock).

It also writes **`outputs/<job-name>.transcript.json`** — the cut-aligned caption transcript, the kept words remapped through `cuts.json` by `export-transcript.py`: timestamps rebased to the edited timeline, **zero re-transcription.** This is what finishing/captions/graphics consume.

**Spelling/brand fixes happen HERE, once.** `export-transcript.py` applies [`transcript-corrections.json`](../../../transcript-corrections.json) as it writes the canonical transcript: `auto` entries (non-word mishears + brand/name casing) swap silently, `flag` entries (real words that might be mishears, e.g. `cloud`) print for eyeballing. Because this is the one source of truth downstream reads, the fix propagates everywhere. The raw `words.json` is untouched; per-video one-offs go in `projects/<job>/corrections.local.json` (same `{auto,flag}` shape, merged on top). Watch the splice log for `auto-fixed:` and `⚠ REVIEW`. Rationale: the engineering archive.

**The full render runs 15-45s per 60s of output — background it.** `RENDER=0` is ~8s, foreground.

### Polish the boundaries (ALWAYS, every job — added 2026-08-28)

```bash
uv run .claude/skills/rough-cut/scripts/polish-boundaries.py <job_dir>
bash .claude/skills/rough-cut/scripts/splice.sh <job_dir>     # RENDER=0 on app-finish jobs
```

The refiner measures each boundary against its own word and its absolute thresholds clip soft decays
or count breaths as tails. (It no longer skips a dead-air kill between adjacent transcript words: it
names the joint, measures both edges and cuts the silence — § Author the cuts.) This
re-derives EVERY boundary peak-relative (local floor, threshold
`max(floor+10dB, peak−28dB)`, decay capped at word.end+300ms, uniform out = decay+70ms /
in = onset−40ms on every segment), widens the search on low-probability boundary words, sweeps every
segment's interior and splits any quiet run ≥ 0.65s, and pins everything. Run the FIRST splice with
`RENDER=0` on every lane, chat-only included — the real render belongs AFTER this step. Already
hand-pinned (`no_refine`) segments are left untouched, which makes the step idempotent. **Heed its ⚠
lines** — clipped words, merged repeats, possible flubbed takes; each gets verified (slice-ASR the
span — see § Fresh-eyes second pass — or fix the boundary by hand) before the cut ships. Then re-run
splice.sh to consume the pinned EDL.

**Three of its lines each mean a word to slice-ASR before the cut ships (2026-09-23).** `out:⚠ CLAMPED`
with "OUT: the next killed word '<w>' starts before '<kept>' decays: speech runs through the cut (fused
joint), verify / pin" means the OUT was clamped at the next killed word's start with less than one 5 ms
hop of tail: the kept word is still loud where the cut falls, so the cut is inside speech (before
2026-09-23 this showed only as `decay+-Nms`). It is not cut-audit's FUSED verdict, which is a clean cut on
the dip: slice-ASR the joint, then pin the OUT by hand or re-author the kill. When the interior dead-air
pass splits a segment, each part's `transcript` is rebuilt from the words the parent plays (every word
inside its final boundaries, or overlapping them by 30 ms or half the word), each word going to exactly
one part, so the parts always join to the parent's text (a part may carry empty text when the aligner
stretched its only word across the pause). "'<w>' ends N ms past the split OUT: the dead-air split may
clip it" means the text keeps the word, so cut-proof can no longer see a clipped tail; "'<w>' … lies
inside the removed dead air" means the aligner puts a word where the envelope hears quiet, and names the
part whose text now holds it.
§ mechanisms (7) and (8).

**Every `seg N` polish prints is an index into the `cuts.json` that same run writes**, with `@T` the
boundary the line is about — the interior dead-air pass renumbers, so a number read off an older log
is fiction (before this was fixed one boundary appeared as both `seg17` and `seg19` in one file, and
a reviewer re-keyed 81 of them against the cut sheet by hand). A per-segment status line carries both
notes, so when that pass splits the segment between them it prints `segN/M`: the `in:` note is N's,
the `out:` note is M's. `seg??` means the resolver could not key the line at all — a bug, never an
index to act on. **A hand pin is addressed by (clip,
time) AND asserted on the segment's transcript text:** `scripts/pin-boundary.py` — `pin(seg(S,
clip, 656.9, expect="MP3"), start=657.15)` — refuses and names both candidates instead of picking.
A nearest-time match with no text guard lands on the neighbouring segment where they sit 0.3-0.5 s
apart, and a fix applied to the wrong edit costs a full author → splice → polish → pin cycle from
clean (your-job, 2026-09-18).

<a id="audit-the-cut-on-the-finish-surfaces-grid-app-finishes-required-when-the-source-and-sequence-rates-differ"></a>

### Audit the cut on the finish surface's grid (every app-finish job; the grid matters most when source and sequence rates differ)

```bash
uv run workflows/cut-audit.py <job_dir> --grid 24000/1001 --promote --sheet <job_dir>/review/cut-audit-sheet.png
```

`polish-boundaries.py` measures once, off WhisperX anchors, and then the app quantizes every boundary
to ITS frame grid: on a 30 fps screen recording laid on a 23.976 sequence that quantization pulled every
in and out up to 41 ms early (a 30 fps screen-recording outro on a 23.976 sequence, 2026-09-13: 21 cuts inside speech, 22 tails under
the house 70 ms, and the creator heard it). `cut-audit.py` trusts only the waveform: a 5 ms RMS envelope, a
local floor, speech runs; per boundary it reports OK / CLIP (inside the kept word) / FUSED (a killed
word running into the kept one: the cut goes on the last prominent dip before the kept word's attack,
never the run's edge, which would resurrect the killed word) / BREATH
(a low-level inhale at the head, kept) · LONG (a tail over 70 + 80 ms, or a `beat` tail over 250 ms, is
trimmed on the grid to decay + 70 / 250 ms; a 390 ms tail passed as "ok" and then failed dead-air-qa at
the joint, 2026-09-20) · BREATH at an OUT: a run reaching more than 250 ms past the kept word's ALIGNER end in which the slice
ASR hears no word, whichever branch proposed the move (the run's end, or the last dip of a tail the ASR
calls non-speech). The cut stays, with a ⚠ verify; an OUT was once moved +667 ms into breath and room
tone. A cut INSIDE the kept word is never BREATH: it is capped at the aligner's end + TAIL, stays CLIP and
counted, with a ⚠ verify. Both the gate and the cap are measured from the aligner's end, never from the
slice ASR's, whose word ends stretch into the breath (an ASR end of 1.84 on a word the aligner ends at
1.45 once moved the OUT +617 ms). The audit moves ONLY defects and leads < 40 ms / tails < 70 ms, and picks
every value on the sequence grid (`--grid`), so the lane's replay lands it exactly. `--sheet` writes the
waveform contact sheet (red = current cut, green = repaired) — that is the proof, look at it. For every cut that sits inside a continuous run it also re-transcribes that run independently (mlx-whisper on macOS, the WhisperX venv's faster-whisper elsewhere through `workflows/asr_cli.py`, word timestamps; `--asr off` to skip, and it degrades to the envelope heuristics where neither engine exists) and uses the words ONLY to decide content: the run IS the kept word (a clipped attack, WhisperX had its start 380 ms late on "I would like") vs a killed word runs into it (fused, cut on the dip). Position never comes from ASR timestamps — both engines are ±100 ms on word edges and anchoring on them pulled cuts into "usage", "to" and "it"; the dip inside the WhisperX-bounded window is what matched every hand-verified joint. **The content gate runs on EVERY boundary, not only the ones inside a run (a "53" that shipped as "50", 2026-09-13):** a cut between two runs looks clean to a waveform even when the run after it is the kept word's own next syllable after a quiet fricative ("fif|ty-three" heard as "a 50"; "click|bait"), because WhisperX had labelled that syllable as the next word. So the audit transcribes the kept side up to the cut and again extended 400 ms across it (slices padded with silence on the cut side, or the decoder mis-hears a word it meets mid-attack): if the boundary word CHANGES the cut is inside it, and the true edge is bisected (CONTENT verdict); if a word is merely added, the cut is clean. **The content gate never extends into a killed word
(2026-09-20):** the extension is bounded by the SEGMENT's killed neighbour, the first word past the
segment's own last word by its aligner start (at an IN, the word before its first, by its aligner end);
when that bound sits at or before the cut, the envelope's verdict stands (a fused joint read as CONTENT
wanted +1043 ms and would have shipped a deliberately killed "et cetera, et cetera"). A kept word the cut
chops is in the segment, so the gate still restores it. **A CLIP at a word the WhisperX midpoint and the
transcript put on different sides is HELD:** it is measured on the transcript's reading, and when that
repair would move the cut, the cut stays CLIP, prints `⚠ HELD … would have moved to X` and is counted as
held in the summary: check it by ear, then pin it or move it (each reading alone moved real cuts the wrong
way: the midpoint cut away a kept "Okay,"; a transcript re-derived from the cut went +42 ms into a killed
"et"). After the verdicts, the proposed EDL runs through `dead-air-qa.py`'s own quiet-run gate (imported,
not re-typed), so a joint whose tail plus the next lead reach 0.65 s prints `⚠ segNN/segMM joint` before
the replay. After a
re-lay, run it again with `--live <readback json>` and expect `0 boundaries in speech`. `--promote` does
the replacement: it backs `transcript/cuts.json` up as `cuts.pre-audit-<YYYYmmdd-HHMMSS>.json`, writes the
audited EDL there and prints the `export-transcript.py` command to run next (never `splice.sh`, whose
frame-snap is to the SOURCE grid and would undo the placement); `--write <file>` still writes elsewhere.
The audit reads `--edl` (default `transcript/cuts.json`) and says so first (`[cut-audit] reading <path>`).
Both `--write` and `--promote` REFUSE (exit 2) a target that holds `pin_in` / `pin_out` the input lacks: a
pin set only in the `--write` target was overwritten in silence (2026-09-20). Pin the input, or pass
`--edl <target>`. Same-rate jobs still benefit (it catches the polish misses:
the "-bait" of clickbait, a "$92" payoff WhisperX had mis-aligned). The Premiere replay's own grid math:
`premiere-pro` § Step 2.

**A boundary a human decided is pinned for the AUDIT with `"pin_in"` / `"pin_out": true` on the
segment, not with `no_refine`.** They are different pins: `no_refine` holds BOTH of a segment's
boundaries against the refiner and the polish, and `cut-audit.py --write` stamps it on every segment
it writes, so the audit ignores it by design. `pin_in` / `pin_out` hold ONE edge, in the audit and,
since 2026-09-27, in `refine-cuts.py` and `polish-boundaries.py` too, which measure the other edge as
usual (the clipper pins only the edge that sits on its parent job's cut). A stutter trimmed out or a false start killed by hand is re-derived from
the envelope on the next pass and quietly undone otherwise — a "we're going to use, use this custom
voice" trim came back twice, 769.686 → 770.603 (your-job, 2026-09-18). A pinned boundary is reported
as `pinned, would have moved to X` and left alone. **And a `--live` readback that disagrees with the
EDL by more than a frame is the creator's hand edit, never a lane quantization:** it is reported
`HAND edit ±N ms off the EDL, left alone` and never moved (the repo law, root `CLAUDE.md` § live
state that disagrees with RUN.md). **A hand edit that is ALSO a cut inside speech keeps its
verdict** — it prints `CLIP*` / `CONTENT*`, stays in `boundaries in speech` and gets its
`--sheet` panel, and the summary counts how many of the hand edits sit in speech. Tagging it HAND
alone dropped a clipped word out of every counter, so the tool hid a defect on exactly the
boundaries a human had touched. Nothing moves either way: the repair is the creator's, by hand or by
dropping the trim. At a `--live` hand edit the EDL transcript is stale (the readback is paired with the
unchanged EDL), so `cut-audit.py` splits kept from killed there by the words the live span plays. A clean
trim on a dip reads HAND, never HELD or CLIP*. A trim inside a word still reads CLIP*.

Since the 2026-09-13 hand pass the audit also (a) splits interior dead air the envelope cannot see — every aligner gap ≥ 0.9 s between two kept words is transcribed and split when nothing is heard in it, pinned segments included (`"keep_pauses": true` opts out), and a gap the ASR hears a word in is flagged as a hidden false start / filler; (b) snaps a fused joint INWARD (the dip's frame belongs to the killed word); (c) honours `"beat": true` (tail up to 250 ms); (d) prints `⚠ possible false start` on a token that is a prefix of the next word.

### The proof: the laid cut is transcribed and diffed against the script (Premiere, the definition of done)

```bash
uv run lanes/premiere/cut-proof.py projects/<job>[/sections/<s>] [--from <start>] [--to <end>]
```

WhisperX is the map the cut was authored from, and it is not the territory: on a screen-recording outro section it collapsed three
stutters into one word each ("half as, half as", "let's use, let's use", "you know, what, what"), skipped fillers (a mumbled "like, the
other one" sat unlabelled inside what `dead-air-qa.py` called a 0.96 s pause, so the split kept it), and stretched a sentence-final word over
the "like, I hit" that followed it, so the kept segment carried a killed phrase. No boundary check can see any of that; only the
assembled audio can. The proof bounces the section's dialogue off the LIVE timeline (other tracks muted), transcribes the bounce
independently and diffs it word by word against the EDL's script: every stutter, doubled joint, chopped syllable or leaked
killed word is a line with its timeline position; notation differences ("$100" / "100 dollars", "oneshot" / "1 shot"), spellings and
contractions ("i am" / "im", "what is" / "whats") are tagged and ignored. **A rough cut on Premiere is done when this exits 0** (Resolve and CapCut have no bounce proof yet: `LANES.md` § step 2), after the replay and the audio
polish, and again after any hand edit. A stutter it finds is killed at the EDL (split the segment, first take dies) and the
whole chain runs again: audit → persist → re-lay → polish → proof.

**Both sides of the diff are canonicalised through [`transcript-corrections.json`](../../../transcript-corrections.json) + the job's `corrections.local.json` (2026-09-19).** The EDL carries what WhisperX heard and the bounce carries what mlx-whisper hears, so a brand the two engines spell differently was a permanent DEFECT until the proof read the repo's own equivalence map. It is never a defect now, and a mishear that is NOT in the dictionary yet belongs in it, which is the same fix `scan-transcript.py` asks for. A NUMBER is never a spelling, so a "53" heard as "50" stays a defect. **cut-proof.py needs no flags on a section:** `--from` defaults to the EDL's first frame on the timeline and `--to` to its last frame (the EDL's `_timeline` end, else edl_start + the EDL's length; the sequence end when that is within 0.5 s past it, or short of it). Both are printed before the bounce, so a no-flag proof of a middle section never bounces the later sections (proven live 2026-09-23). **A proof of part of a section** needs only `--from` / `--to`: the script is windowed to the segments the bounce actually covers, and the proof reads where the EDL's first frame sits on the timeline from the job (the EDL's `_timeline` readback, else the section's `graphics-plan.json` `timeline_offset`, else 0 for a top-level `projects/<job>`). A section sub-job at step 2, before either exists, has none of these: pass `--edl-start` (it warns ⚠ and assumes `--from`). Every run prints the window before the bounce as `[cut-proof] script window: EDL a-b s (edl_start x, from …)`: read it, and abort if it is wrong. Where a boundary segment is only partly covered by the bounce, its uncovered words are tagged `edge`. **Read the gate's exit code directly, never through `| tail`:** a pipe reports tail's status, which is how an argparse error once read as exit 0 (in zsh, `${pipestatus[1]}`). `--triage` re-transcribes a ±1.5 s slice of the bounce under every defect, so a transcription slip identifies itself instead of costing a hand pass, and each run prints the defects it INTRODUCED first (`NEW`) with the rest counted as carried, keyed on the words rather than a timeline position that every re-lay moves. A proof run after a hand edit is only meaningful once the EDL has been re-derived from the live timeline. **Before every bounce it checks each segment's `transcript` against words.json** (`--check-text` runs that alone, offline): text that omits a word wholly inside its segment, or carries one no word there holds, is a false DEFECT, so fix the text to the kept audio first (two boundary edits left "with" and "actually" out of their text on the Windows proof, 2026-09-27). **A defect `--triage` proves is an ASR false positive** (a reduced "with" every engine, the raw included, hears as "for") is accepted in `review/cut-proof.accepted.json` as `{script, heard, t, cut_rev, reason}`: same words, within ±0.5 s of `t` (timeline seconds, as printed), on the `cut_rev` the summary prints. It is then reported `accepted` and no longer fails the gate; a row without a reason is refused, and one from another cut_rev is ignored, so a re-cut re-opens it. Regression: `uv run workflows/test_cut_proof.py`.

### Final dialogue dead-air gate (required before handoff and after EDL changes)

Run `uv run workflows/dead-air-qa.py <job_dir> --json <job_dir>/transcript/dead-air-qa.json` against the final saved EDL, including pinned segments. This read-only check uses the original dialogue audio, so music and SFX cannot conceal a pause. It bridges brief room-noise spikes and measures across edit joints. Every flagged ≥0.65s run must be checked acoustically and corrected if it is dead air. The repair (a screen-recording outro section, 2026-09-13, nine runs polish had bridged as room tone): split the containing segment at `[source_start + 0.07, source_start + duration − 0.035]` in the `/tmp` EDL (when `transcript/cuts.json` was written after the last splice, by `cut-audit.py --promote`, `live-edl.py --write` or a hand edit, copy it to the `/tmp` EDL first: `splice.sh` refuses to overwrite it otherwise) with both halves `"no_refine": true`, re-run `RENDER=0 splice.sh`, then re-run this gate until it passes. `no_refine` protects a measured boundary; it does not prove a pause was reviewed or intentionally retained. A segment carrying `media` (laid from a substitute file such as a lip-sync re-record) is not audited on the raw by `dead-air-qa.py` or `cut-audit.py`: each prints `segNN laid from <media>: not audited on the raw`, keeps the segment's EDL times, still counts its duration on the timeline and never joins a quiet run across it (it is listed as `not_audited` in the JSON). Check its audio by ear or on the bounce proof.

Also inspect transcript gaps ≥0.65s as independent review candidates. A quiet detector passing, timeline clips being contiguous, and an export decoding successfully are separate checks; none is a substitute for reviewing the actual pacing. After a repair, rerun this gate and verify live V1/A1 source ranges match the audited EDL. Never declare the rough cut clean from timeline contiguity alone.

### Transcript QA (auto, every run)

The static dictionary only fixes mishears it knows. This catches the **new** ones — names/brands WhisperX mangled. **Run it every job, right after splice:**

```bash
uv run .claude/skills/rough-cut/scripts/scan-transcript.py <job_dir>
```

(Windows has no system wordlist — the scan reports nothing there, so skip this step.)

It compares every word against a 235k-word English wordlist (+ inflection stripping) and the dictionary, printing only the **suspects**. Clean transcript → empty; otherwise a short list with context: `higsfield  ×1  …built it on higsfield and pushed to…`.

**Judge each suspect in context:** single token, recurring name/brand (`higsfield → Higgsfield`) → [`transcript-corrections.json`](../../../transcript-corrections.json) `auto`, fixed everywhere forever · one-off → `projects/<job>/corrections.local.json` · **multi-token mishear** ("higs field" → "Higgsfield") → **never** auto-apply (it changes word count and breaks per-word timestamps), flag it · already-correct proper noun → skip.

Then re-apply (instant, timings + cuts untouched):

```bash
bash .claude/skills/rough-cut/scripts/reapply-corrections.sh <job_dir>
```

**Hard rule:** only auto-apply **single-token, whole-word** swaps — the dictionary mechanism enforces this, which is why it can never shift a timestamp or alter a cut. Unsure? Flag it.

### Fresh-eyes second pass (ALWAYS, every job — 2026-08-28)

The author grading their own cut is why first cuts ship flaws. Before reporting (and before the
timeline replay on app-finish jobs), fan out **two subagents on this session's model, never Fable**
(the Fable → Opus override and the inherit trap: `edit-review` § Token efficiency), one pass, not a convergence
loop (that's `edit-review`'s territory):

1. **Script-flow reviewer.** Input: the cut sheet's transcript column as ONE continuous prose
   script (+ this skill's taste rules, self-contained in the prompt). Finds only: orphaned
   connectives, dead deictic antecedents, echoes kept more than once, fluff (good-to-know vs
   need-to-know-NOW), a beat stripped of its framing clause, meta-signposts / method teases (excluding the protected closure/handoff
   and the corner-turning section closes), momentum breaks, and a missing or chopped ending against the raw closing passage;
   plus the 2026-09-13 classes: a weak line right before its stronger restatement, a rhetorical Q&A with no claim, a second
   hedge after a hedged sentence, a wrong connective, a reading-aloud search, a second CTA in the outro, a killed line that a
   surviving *because / so / and also* still answers, a mid-phrase one-word filler cut out (a joint bought for nothing), and
   an argument's landing restatement killed as an echo. Findings must quote the exact lines.
2. **Mechanical reviewer.** Input: the polish-boundaries ⚠ list, the transcript, the words.json
   probabilities. Verifies every ⚠ by slice re-ASR — `uv run workflows/cut-audit.py <job_dir> --say
   <t0> <t1> [--clip <name>]` prints what an independent engine hears in that raw span (±4s around
   the boundary) — and diffs what was said against what the cut keeps. Use that command, never a
   hand-rolled `mlx_whisper` shell-out: it names its output file by the basename up to the FIRST
   dot, so a slice called `b0082.88.wav` silently overwrites `b0082`'s transcript and three batches
   come back wrong (your-job 2026-09-18). Catches
   fictional tails, missing sentence completions, and flubbed takes (an alignment-collapse cluster
   + an untranscribed speech burst nearby = a bad take to kill, not a boundary to fix).

Launch both in the background and do not poll for them (the harness notifies on completion; a grep
loop never matches and burns its whole timeout). Main session adjudicates: mechanical defects get
fixed (boundary moved, take killed, graft moved), flow findings are judgment calls decided against
the taste rules, and only the CHANGED segments get re-checked. Then report. Why this pass exists: the engineering archive.

### Report back

Show the creator: the detected format + the hook/takeaway you inferred (one line, where a wrong read
gets corrected), final duration vs raw total, and the cut sheet. On the default (`RENDER=0`) lane
report the segment count, `transcript/cuts.json`, `outputs/<job>.transcript.json` and the timeline
the EDL was replayed onto — **there is no flat MP4, do not report one.** Only the chat-only /
HyperFrames lane reports `outputs/<job>.mp4`.

```
✂️ ROUGH CUT DONE

📊 3:47 → 0:48 (79% cut)  ·  33 segments
📁 projects/<job-name>/transcript/cuts.json  →  replayed onto <timeline>
   (chat-only lane instead: projects/<job-name>/outputs/<job-name>.mp4)

CUT SHEET:
1. [clip-02 @ 1.24-4.60] "Are you still paying a VA three grand a month"
2. [clip-02 @ 4.95-8.10] "to do shit Claude Code can do for free"
...
```

Flag a weak segment: **"⚠️ segment 3 is borderline — consider killing."**

### Learn from the hand pass (Premiere-finish jobs)

When the creator hand-adjusts the cut on the Premiere timeline, **diff their edit against the EDL and fold the delta back into taste** — their trims ARE the ground truth this skill approximates:

```bash
node lanes/premiere/premiere-bridge.mjs diff-edl projects/<job>/transcript/cuts.json [more cuts.json...]
```

It matches every timeline clip to its EDL segment by source overlap and prints deletions, boundary trims/extensions (with the words at each moved boundary), grafts, and new material. Recurring pattern → a new Auto-Kill row or timestamp rule here; one-off → the job's notes. The 2026-07-29 rules came from exactly this diff. A clip's source out is derived from its own length (`inPoint + (end − start)`), never read from `outPoint`: a `STALE-OUTPOINT` line is a stale readback left by an earlier `clip.end` write, reported for information and never the creator's trim.

After a hand pass the **timeline is the source of truth**: never re-replay the EDL over it. Sync it with `uv run lanes/premiere/live-edl.py projects/<job> --write`, which backs the old EDL up as `transcript/cuts.pre-live-<stamp>.json`, derives every source out as `inPoint + (end − start)`, pins each boundary that moved (`pin_in` / `pin_out`, so the audit never undoes it), re-derives those segments' words with the polish's own `plays` rule (a grazed neighbour stays out, an aligner end past a hand OUT stays in, a word across a razor is promised once) and writes `_timeline`. Then run the two commands it prints: `ripple-cut.py --from <backup> --apply` first (it re-derives the canonical transcript and backs up the old one), then `export-transcript.py` only if there was no canonical transcript yet. A sequence that carries another EDL (an AD clone) is synced into its own file with `--sequence "<job> AD" --edl transcript/cuts.ad.json`; without `--edl` the tool refuses to write it into the organic's EDL. `--live-out live.json` feeds `cut-audit.py --live`. Exit 1 = V1 does not add up (a gap, a deleted clip); exit 2 = refused or failed. Never hand-build this from a dump script (proven live 2026-09-23, your-job's own stale clip reproduced to the digit).

**The 2026-09-13 outro hand pass is the worked example:** 74 clips against the 66 laid. Read back live, written as an EDL, bounced through `cut-proof.py` (so every ambiguous joint was HEARD, not inferred from WhisperX), audited with `cut-audit.py` on both EDLs (your leads: median 59 ms, same as the tool's; your tails: median 89 ms, p75 162 ms against the tool's 78/83), and the surviving-pause distribution measured on both bounces (your cap 645 ms, 21 pauses of 400–650 ms left alone: the 0.65 s dead-air threshold stands). The delta became: six restored lines (two section closes, an argument's landing restatement, the antecedent of a surviving "because", a sentence-initial "But", a list marker "And I also"), five kills (a prefix false start, a weak line before its stronger restatement, a second hedge, a rhetorical Q&A, a wrong connective, a second CTA), four mid-phrase filler kills reversed, two long pauses razored that the envelope never saw, eleven beat tails, and seven fused joints moved one frame inward. Every one of those is now a row or bullet above, and the tool changes live in `polish-boundaries.py` (`beat`, `keep_pauses`, pinned interiors still split) and `cut-audit.py` (inward snap, `beat`, ASR-verified aligner-gap splits, the false-start warning).

---

## Gotchas

- **`-c copy` alone desyncs A/V on arbitrary cut points** — `splice.sh` trims and concats in one filtergraph, encoding once. Never "optimize" to stream copy.
- **Don't auto-snap cuts to silence.** WhisperX word alignment is the unlock; silencedetect snapping moves chosen boundaries into filler words or awkward pauses. (The refiner and `polish-boundaries.py` are NOT this: they keep the chosen word fixed and only dial the cut against its measured acoustic edge, clamped inside the local gap.)
- **Whisper can mishear.** Cross-check before killing a line — "Claude" becomes "cloud" and the line looks wrong when it's fine.
- **`splice.sh` reads `/tmp/video-editor/<job>/cuts.json`, NOT `transcript/cuts.json`** (on Windows, `%TEMP%\video-editor\<job>`, Git Bash's `/tmp`: write it through the Bash tool, since a file tool may resolve `/tmp` to `C:\tmp`), then overwrites the job copy with what it spliced. Re-cutting an already-cut job would replay the STALE `/tmp` EDL over a newer `transcript/cuts.json`, so `splice.sh` stamps the EDL it wrote (`transcript/cuts.splice.sha1`) and exits 2 when `transcript/cuts.json` changed since (`cut-audit.py --promote`, `live-edl.py --write`, a hand edit) and the `/tmp` EDL is not that file. Start from `transcript/cuts.json` when it is newer than the last splice: copy it to the `/tmp` path (delete `cuts.refined.json` + `cuts.snapped.json` alongside it) first.
- **Transcribe.sh auto-skips** when `projects/<job-name>/transcript/words.json` exists. Use `--force` only if the raw footage actually changed.
- **Multi-section jobs: each newly filmed section runs as its own sub-job under `projects/<job>/sections/<name>/`** (raw symlinked from the parent's `raw/`; Windows refuses a symlink without Developer Mode, so there copy the raw into the section's `raw/` instead, its own `transcript/` + `outputs/`). This exists because of the auto-skip above: point a new section's transcribe at the main job dir and it silently reuses the WRONG `words.json`/`cuts.json`. (Same nesting the clipper uses.)
- **The authoring pad can pull the NEXT killed word into a segment (astra final-thoughts, 2026-09-14).** `refine-cuts.py` and `polish-boundaries.py` take a segment's words by OVERLAP, so an authored `end = word.end + 0.07` that touches the next word's WhisperX start makes that killed word the segment's last word: its decay gets measured and it ships ("then", "And", a stranded "My", a filler "like" on one job). When the word after the last kept one is killed and starts within ~100 ms, author `end` just under its start and read the polish's per-segment `…word` column: it names the word each boundary was measured on. **And when two independent ASR passes agree on a word at a joint that the envelope cannot label, the ASR's word ORDER wins** ("And here's… [pause] the, so that's" — the envelope read the post-pause burst as "So"; the bounce proof caught the stranded "the").
- **The per-section colour replay on Premiere:** one `premiere-bridge.mjs replay` per section, with that section's colour label set first (`premiere-pro` § Colour labels), then `cut-audit.py --live`, then `polish-boundaries.py` on the section's own sub-job, then `cut-proof.py --from <the section's start>`.
- **A second voice on a phone speaker goes missing from WhisperX's text, and the aligner then misplaces the MAIN speaker (your-job, 2026-09-17).** Usually this is not the VAD: measured 2026-09-23, the VAD scored your-job-pa's and long-form's AI lines 0.76–1.0, and Whisper drops them inside its 30 s decode window. No `transcribe.sh` setting prevents it (§ Transcribe). A live call demo: the AI's lines (about 10 dB under you) were dropped whole, and with their text missing wav2vec2 forced your next lines into the wrong windows (one landed 6 s early), so every cut authored off `words.json` there would have been fiction. Tell: gaps of several seconds inside a conversation, and a run of p < 0.3 words right after one. Fix at the source: `uv run workflows/cut-audit.py <job_dir> --coverage` finds the windows (§ Transcribe), `--say <t0> <t1> --boost --spans-out <spans.json>` tells you what is really in them and drafts the spans file, one span per ASR segment (`--boost` compresses and normalises the slice for a voice about 10 dB under; every pass runs with `--condition-on-previous-text False`, and `--say` with no times covers the whole clip in windows of 30 s or less, because one long pass locked into repeating a sentence, 2026-09-20). Check every line of the draft by ear and fix numeral times (never hand-roll `mlx_whisper`); then `~/.cache/video-editor/whisperx-venv/bin/python .claude/skills/rough-cut/scripts/realign-spans.py <job_dir> <spans.json>` (Windows: `…/whisperx-venv/Scripts/python.exe`) force-aligns THOSE spans with `whisperx.align` and keeps WhisperX's words everywhere else (run it with the venv `transcribe.sh` builds; it backs the old transcript up as `words.whisperx-vad.json`). **A span is a WINDOW, so spans may never overlap each other and every word that touches one is replaced** — it refuses an overlapping pair and says to merge them, and it counts the words it dropped for grazing an edge; leave either and `words.json` comes back with two words over the same seconds, which every boundary measured off it then inherits. Numerals come back squeezed into a few hundred ms — it flags each one — so set those word times from the envelope. **The same drift INVENTS words (your-job, 2026-09-18):** WhisperX laid "Okay, so it should call me" over you reading your phone number aloud and shifted your "Yo, there it is" onto the AI's "Done, it's on your calendar" line; only the bounce proof heard the digits, and the number was audible in the first laid cut. Any segment beside spoken digits or on a call is slice-ASR'd on the raw before it ships.
- **`transcript/cuts.json` is splice's own by-product, not an authored EDL.** `splice.sh` copies it from `cuts.snapped.json` AFTER the frame-snap, which takes ~10 s on a 208-segment EDL, so it is always newer than `cuts.refined.json` and the 5 s mtime slack false-aborted every long-form job with "the refined EDL is stale". `polish-boundaries.py` now skips it on byte-equality with the snapped file and only refuses on a real hand edit. Never clear a stale-EDL abort by `touch`ing the refined file — re-run `splice.sh` so the refiner measures the EDL you edited.
- **A SPOKEN CLAIM WHOSE TRUTH IS ON SCREEN IS CHECKED AGAINST THE FRAMES, AND THE PICTURE WINS (2026-09-19).** Reading the assembled cut sheet, list every claim of a quantity the footage can itself display — elapsed time, a timer or stopwatch, a clock, a counter, a price, a version, a count of items, a progress bar. For each, sample the kept spans (`ffmpeg -ss <t> -i <raw> -frames:v 1`, step about 4 s across the kept window) and read what is actually visible. If a kept frame contradicts the claim, the CLAIM goes — and the contradiction does not end there: the thing that disagrees is still in the picture. Record every kept span that still shows it in RUN.md with its **timeline window and its raw source time**, so step 5 can cover, blur, crop or cut it without re-sampling the whole cut. A claim cut without that record is half a fix (an intro promised "under 10 minutes" over a walkthrough whose visible Clock read 29:53, and finding the surviving 4-second window the next day cost six contact sheets).
- **Clip order in `cuts.json` = final order in the reel.**
- **A screen recorder's facecam is NOT lip-synced to its mic, and the offset drifts (your-job, 2026-09-19).** A bubble hides it; cut to that camera full-frame and it shows: +1.9 frames at the start of a 53-min take, +8.3 by the end. Before laying a facecam export as its own angle, `uv run workflows/lip-sync.py <cam> --audio <mic-source> --mouth-crop <w:h:x:y>` measures mouth motion against the voice across the take and fits the drift; each camera clip's in-point then slips later by its own lag, timeline start/end unchanged, proved on a timeline export. **Pass the crop: on the take this was calibrated against, the bare command exits 2 UNMEASURED** (the generic default band is wide enough to catch head and background motion, which correlates against the voice just well enough to look like an answer). Pick it once per shoot — grab one frame of the cam (`ffmpeg -ss <t> -i <cam> -frames:v 1 mouth.png`), read the mouth's box off it, and write it as fractions of the frame, `w:h:x:y` (that 3836-wide facecam measured `iw*0.14:ih*0.16:iw*0.44:ih*0.53`). Tight enough to hold just the mouth, wide enough to survive the head moving inside the take. The verdict itself is the exit code: 0 PASS, 1 FAIL with the slip formula, 2 UNMEASURED — and 2 means the crop, not the footage.
- **Questions are a last resort, not a step.** Intent comes from the transcript (or sampled frames on a visual-only edit), format from the clips' aspect ratios. Never ask for those; infer, state your read in the report, let the creator correct it. Ask only when something is genuinely undecidable, and then one question, one sentence.

---

## Handoff

A restored or appended passage changes the final transcript and duration: refresh the canonical cut-aligned transcript, then send the affected window back through graphics planning/build, SFX, and final verification. A dialogue repair is not a finished passage while its required visuals or sounds are missing.

A cut change after step 3 re-times what is already PLACED as well: run `uv run workflows/ripple-cut.py projects/<job> --from <the EDL the graphics were authored against>` before re-placing anything — `edit-video` § Running a step owns the gate that reopens the downstream steps.

The cut lands on the finish surface; the line continues in `edit-video` (repo-root `CLAUDE.md` has the eight-step flow).

**Transcribe-once is a contract, not a convenience.** Everything downstream reads the canonical `outputs/<job>.transcript.json` — including the locked caption builders ([Talking Head Explainer](../../../presets/instagram/talking-head-explainer/captions-style.md), built by its [`captions.py`](../../../presets/instagram/talking-head-explainer/captions.py); [tiktok/raw](../../../presets/tiktok/raw/tiktok-raw-style.md)), which never re-transcribe.

This skill does ONE thing: cut the reel to the essential lines (audio is normalized as part of the cut). No captions, B-roll, zoom effects, or vertical reframing.
