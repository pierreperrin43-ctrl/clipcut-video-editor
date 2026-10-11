#!/usr/bin/env python3
"""place-music.py: lay the background-music bed on the Premiere music track (the opt-in pass, Premiere lane).

  uv run lanes/premiere/place-music.py projects/<job> --apply [--track <file>] [--bed-db -20] [--source-in seconds]   # place, level, tail fade, read back, save
  uv run lanes/premiere/place-music.py projects/<job> --apply --refit [flags]                   # after a ripple: remove the bed, re-lay it from hf-graphics/music-plan.json (flags override), read back, save
  uv run lanes/premiere/place-music.py projects/<job> --verify                                  # timeline readback vs the house numbers (exit 1 on drift)
  uv run lanes/premiere/place-music.py projects/<job> --bounce                                  # music-only WAV bounce in-Premiere (no AME) + LUFS: the proof
  uv run lanes/premiere/place-music.py projects/<job> --remove                                  # take the bed off the music track

The WHAT is the `background-music` skill (flat bed, no ducking, no fade-in); this is the HOW for
Premiere, the by-hand placement of 2026-09-04 made repeatable. Mechanics, all read back:

  - the track is the newest audio file in projects/<job>/audio/ unless --track names one; it is
    imported ONCE into a `music` bin (found by media path on later runs)
  - the bed starts where the SONG starts: source in-point = the sustained entrance from workflows/music-onset.py
    (or explicit --source-in), snapped DOWN to the sequence frame grid (under a frame of pre-roll, never a
    clipped attack) and REQUESTED at the top of that frame so both of Premiere's floors land on it
    (in_point()), so a silent intro never ships under the hook; the plan saves the in-point that LANDED
  - the clip lands on the music track (A5, index 4, the `music` role on the youtube/default map)
    at 0, hard-trimmed to the timeline end (the last clip end on every other track)
  - the level is the clip's intrinsic Volume > Level through `clip_level.lvl_v` (the encoding's one
    code home; its prose home is lanes/premiere/lab-notes.md), written THROUGH THE FIRST KEYFRAME:
    a static setValue plus keys reads back right
    everywhere and still plays ≈ −64 dB (lab-notes.md), so the level is never set statically
  - the tail fade is two Level keys, end − 2.0 s → end, bed → −96 dB, in SOURCE time
    (inPoint + timeline time)
  - readback cannot see the keyframe-vs-static trap, so --bounce is the proof: it mutes every
    other audio track, exports the sequence to a mono WAV through exportAsMediaDirect, unmutes,
    and prints the bed's integrated LUFS and its level in the first 100 ms
  - a laid bed does not follow the timeline: after a ripple it runs past the new end (2026-09-23:
    125.876 vs 119.745). Plain --apply on a laid bed only verifies, and on a failure names the exact
    `--apply --refit` command; --refit removes the bed and re-lays it from hf-graphics/music-plan.json
    (a flag overrides its value; with no plan, the laid bed's own in-point is kept, never re-derived),
    verifies and saves once at the end. Where the plan disagrees with the laid bed's in-point or level
    and no flag names it, the laid value is a hand edit: refit refuses before removing anything and
    prints the command for each side
"""
import json, math, os, shlex, subprocess, sys, tempfile
for _s in (sys.stdout, sys.stderr):  # Windows pipes default to cp1252, which cannot encode the status glyphs
    try:
        if (getattr(_s, "encoding", "") or "").lower().replace("-", "") != "utf8":
            _s.reconfigure(encoding="utf-8")
    except Exception:
        pass
from pathlib import Path
from job_guard import require_job_project
from pes import es, wav_preset           # lanes/premiere/pes.py: the bridge's one output contract
from clip_level import lvl_v, v_lvl      # lanes/premiere/clip_level.py: the ONE Volume > Level encoding

BRIDGE = Path(__file__).resolve().parent / 'premiere-bridge.mjs'
TRACK = 4            # A5: the music role on presets/youtube/default/README.md's track map
BED_DB = -20         # the house flat bed
TAIL = 2.0           # tail fade-out seconds (2026-09-04)
FLOOR_DB = -96
AUDIO_EXT = ('.mp3', '.wav', '.m4a', '.aac', '.flac', '.aif', '.aiff')


def sh(*cmd, check=True):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if check and r.returncode:
        sys.exit(f"{' '.join(cmd[:3])} failed:\n{r.stderr or r.stdout}")
    return r.stdout


TICKS = 254016000000  # Premiere ticks per second
IN_NUDGE = 1e-5       # the in-point request sits this far under the NEXT sequence frame (in_point())


def in_point(raw, fps):
    """(snapped, request): the sequence frame at or before `raw`, and the seconds to REQUEST so it lands.

    An audio item's in-point is floored TWICE on the way to the timeline: `setInPoint` floors it to the
    item's own source grid (29.97 on an MP3 under a 23.976 sequence), then `overwriteClip` floors that to
    the sequence grid (lanes/premiere/lab-notes.md). A request just above the frame (the old `+1e-4`) lost
    a whole frame whenever a source-grid line fell inside it, 3 frames in 4 at 23.976 over 29.97; half a
    frame up still loses 1 in 4. The TOP of the frame survives both floors for any source grid no coarser
    than the sequence's (your-job, 2026-09-23). Snapped in whole ticks so a saved value re-snaps to itself:
    the float 10.635624999999989 floored to the frame BEFORE 10.635625.
    """
    tpf = round(TICKS / fps)                       # ticks per sequence frame (the sequence's timebase)
    n = max(0, round(raw * TICKS) // tpf)
    return n * tpf / TICKS, (n + 1) * tpf / TICKS - IN_NUDGE


def onset(track):
    """Shared sustained-entrance candidate, including attack pre-roll."""
    helper = BRIDGE.parents[2] / 'workflows/music-onset.py'
    return float(sh(sys.executable, str(helper), str(track)).strip())


def lufs(wav, seconds=None):
    cmd = ['ffmpeg', '-hide_banner', '-nostats', '-i', wav] + (['-t', str(seconds)] if seconds else []) + ['-af', 'ebur128', '-f', 'null', '-']
    out = subprocess.run(cmd, capture_output=True, text=True).stderr
    tail = out[out.rfind('Summary:'):]
    for ln in tail.splitlines():
        if ln.strip().startswith('I:'): return float(ln.split()[1])
    return None


class Placer:
    def __init__(self, job, track=None, bed_db=None, source_in=None):
        self.job = Path(job).resolve()
        self.plan_path = self.job / 'hf-graphics/music-plan.json'
        self.named = {k: v for k, v in (('track', track), ('bed_db', bed_db), ('source_in', source_in)) if v is not None}   # the CLI's own values
        saved = json.loads(self.plan_path.read_text(encoding="utf-8")) if self.plan_path.exists() else {}
        if track is None and saved.get('track'): track = saved['track']
        if track: self.track = str(Path(track).resolve())
        else:
            aud = self.job / 'audio'
            cands = sorted([p for p in aud.glob('*') if p.suffix.lower() in AUDIO_EXT], key=lambda p: p.stat().st_mtime) if aud.is_dir() else []
            if not cands: sys.exit(f'no music track: drop one in {aud} or pass --track')
            self.track = str(cands[-1])
        if not os.path.exists(self.track): sys.exit(f'no such track: {self.track}')
        if 'track' in self.named: self.named['track'] = self.track
        if not saved.get('track') or str(Path(saved['track']).resolve()) != self.track: saved = {}
        self.saved = saved
        self.bed_db = bed_db if bed_db is not None else saved.get('bed_db', BED_DB)
        self.source_in = source_in if source_in is not None else saved.get('source_in')
        if self.source_in is not None and (not math.isfinite(self.source_in) or self.source_in < 0):
            sys.exit('source-in must be a finite nonnegative number')
        require_job_project(es, self.job)   # every command here reads or writes the ACTIVE sequence (lanes/premiere/job_guard.py)

    def readback(self):
        r = es(r"""
(function(){
  var seq = app.project.activeSequence; if (!seq) return "ERROR: no active sequence";
  var PATH = %s, TRACK = %d, tlEnd = 0, i, c;
  for (var t = 0; t < seq.videoTracks.numTracks; t++) for (i = 0; i < seq.videoTracks[t].clips.numItems; i++) { c = seq.videoTracks[t].clips[i]; if (c.end.seconds > tlEnd) tlEnd = c.end.seconds; }
  for (var t = 0; t < seq.audioTracks.numTracks; t++) { if (t === TRACK) continue;
    for (i = 0; i < seq.audioTracks[t].clips.numItems; i++) { c = seq.audioTracks[t].clips[i]; if (c.end.seconds > tlEnd) tlEnd = c.end.seconds; } }
  var out = {tlEnd: tlEnd, tracks: seq.audioTracks.numTracks, fps: 254016000000 / Number(seq.timebase), clips: []};
  if (seq.audioTracks.numTracks <= TRACK) return JSON.stringify(out);
  var tr = seq.audioTracks[TRACK];
  for (i = 0; i < tr.clips.numItems; i++) { c = tr.clips[i];
    var p = c.projectItem ? c.projectItem.getMediaPath() : "";
    if (p !== PATH) continue;
    var e = {start: c.start.seconds, end: c.end.seconds, srcIn: c.inPoint.seconds, keys: [], vIn: null, vMid: null};
    for (var k = 0; k < c.components.numItems; k++) { var cm = c.components[k];
      if (cm.displayName !== "Volume") continue;
      for (var q = 0; q < cm.properties.numItems; q++) { var pr = cm.properties[q];
        if (pr.displayName !== "Level") continue;
        e.vIn = pr.getValueAtTime(c.inPoint.seconds); e.vMid = pr.getValueAtTime(c.inPoint.seconds + (c.end.seconds - c.start.seconds) / 2);
        if (pr.isTimeVarying()) { var ks = pr.getKeys(); for (var z = 0; z < ks.length; z++) e.keys.push({t: ks[z].seconds - c.inPoint.seconds, v: pr.getValueAtKey(ks[z])}); } } }
    out.clips.push(e); }
  return JSON.stringify(out);
})()""" % (json.dumps(self.track), TRACK))
        if str(r).startswith('ERROR'): sys.exit(r)
        return json.loads(r)

    def verify(self, quiet=False):
        tl = self.readback(); ok = True
        if len(tl['clips']) != 1:
            print(f"✗ {len(tl['clips'])} music clips on A{TRACK + 1} (want 1): {os.path.basename(self.track)}"); return False
        c = tl['clips'][0]
        def chk(cond, msg):
            nonlocal ok
            if not cond: ok = False; print('✗ ' + msg)
        if self.source_in is not None:
            # half a frame: a one-frame drift (the double floor's exact size) must fail, not pass on float luck
            chk(abs(c['srcIn'] - self.source_in) < 0.5/tl['fps'], f"source in {c['srcIn']:.3f}, want {self.source_in:.3f}")
        else:
            print('— no reviewed source start on file (hf-graphics/music-plan.json): entrance NOT checked; '
                  'pass --source-in N to check against one, or re-place with --apply --source-in N to record it.')
        chk(abs(c['start']) < 0.02, f"starts at {c['start']:.3f}, want 0")
        chk(abs(c['end'] - tl['tlEnd']) < 0.02, f"ends at {c['end']:.3f}, timeline ends {tl['tlEnd']:.3f}")
        chk(c['vIn'] is not None and abs(v_lvl(c['vIn']) - self.bed_db) < 0.2, f"level at start {v_lvl(c['vIn']) if c['vIn'] else None} dB, want {self.bed_db:+d}")
        chk(c['vMid'] is not None and abs(v_lvl(c['vMid']) - self.bed_db) < 0.2, f"level mid-clip {v_lvl(c['vMid']) if c['vMid'] else None} dB, want {self.bed_db:+d}")
        ks = c['keys']
        chk(len(ks) == 2, f"{len(ks)} Level keyframes, want 2 (the tail fade)")
        if len(ks) == 2:
            chk(abs(ks[0]['t'] - (c['end'] - TAIL)) < 0.05 and abs(v_lvl(ks[0]['v']) - self.bed_db) < 0.2, f"fade start key at {ks[0]['t']:.3f} = {v_lvl(ks[0]['v']):.1f} dB, want {c['end'] - TAIL:.3f} = {self.bed_db:+d}")
            chk(abs(ks[1]['t'] - c['end']) < 0.05 and v_lvl(ks[1]['v']) < -90, f"fade end key at {ks[1]['t']:.3f} = {v_lvl(ks[1]['v']):.1f} dB, want {c['end']:.3f} = −96")
        if ok and not quiet:
            print(f"✓ A{TRACK + 1} 0 → {c['end']:.3f} from source {c['srcIn']:.3f}  {self.bed_db:+d} dB flat, {TAIL:.1f}s tail fade  {os.path.basename(self.track)}")
        return ok

    def refit_cmd(self, **vals):
        """The exact `--apply --refit` command line (run from the repo root): this run's flags, `vals` over them."""
        v = {**self.named, **vals}
        root = BRIDGE.parents[2]
        job = (self.job.relative_to(root) if self.job.is_relative_to(root) else self.job).as_posix()
        seq = os.environ.get('VE_SEQUENCE')   # the job guard's sequence pick rides the env: a fresh shell must get it too
        cmd = ([f'VE_SEQUENCE={shlex.quote(seq)}'] if seq else []) + ['uv', 'run', 'lanes/premiere/place-music.py', shlex.quote(job), '--apply', '--refit']
        if 'track' in v: cmd += ['--track', shlex.quote(v['track'])]
        if 'bed_db' in v: cmd += ['--bed-db', str(v['bed_db'])]
        if 'source_in' in v: cmd += ['--source-in', repr(v['source_in'])]   # repr: a truncated decimal floors a frame early
        return ' '.join(cmd)

    def refit_from(self, laid, fps):
        """Before a refit removes anything: keep the laid bed's in-point when nothing names one, and refuse
        when the plan (or the house level) disagrees with the laid bed on a value no flag names — the laid
        value is then a hand edit, and a refit never lays over one silently."""
        if self.source_in is None:
            self.source_in = laid['srcIn']
            print(f"— no source in on file: keeping the laid bed's {laid['srcIn']:.3f}")
        lvl = v_lvl(laid['vIn']) if laid['vIn'] is not None else None
        keep, plan, diff = {}, {}, []
        if 'source_in' not in self.named and abs(laid['srcIn'] - self.source_in) >= 0.5/fps:
            keep['source_in'], plan['source_in'] = laid['srcIn'], self.source_in
            diff.append(f"source in: laid {laid['srcIn']:.3f}, plan {self.source_in:.3f}")
        keep_as = 'keep the laid bed'
        if 'bed_db' not in self.named and lvl is not None and abs(lvl - self.bed_db) >= 0.2:
            keep['bed_db'], plan['bed_db'] = round(lvl), self.bed_db
            diff.append(f"level: laid {lvl:.1f} dB, {'plan' if 'bed_db' in self.saved else 'house default'} {self.bed_db:+d} dB")
            if abs(lvl - keep['bed_db']) >= 0.05:   # --bed-db takes whole dB, so this one cannot keep the laid level
                keep_as = f"nearest the laid bed (--bed-db takes whole dB: {keep['bed_db']:+d}, not the laid {lvl:.1f})"
        if diff:
            ref = 'hf-graphics/music-plan.json' if self.saved else 'the house level'
            sys.exit(f'✗ the laid bed disagrees with {ref}, so it was left alone (a hand edit?):\n  ' + '\n  '.join(diff)
                     + f"\n  {keep_as}: {self.refit_cmd(**keep)}"
                     + f"\n  {'back to the plan' if self.saved else 'the house level'}: {self.refit_cmd(**plan)}")

    def apply(self, refit=False):
        tl = self.readback()
        if tl['clips'] and not refit:
            print('already placed')
            if self.verify(): return True
            src = 'hf-graphics/music-plan.json' if self.saved else "the laid in-point and the house level"
            print(f"re-fit it (remove, re-lay from {src} and this run's flags, verify, save):\n  {self.refit_cmd()}")
            return False
        if tl['tlEnd'] <= 0: sys.exit('empty timeline: nothing to lay music under')
        if tl['clips']:
            # nothing reaches disk until the re-laid bed verifies: the save below is the refit's only one
            self.refit_from(min(tl['clips'], key=lambda c: c['start']), tl['fps'])
            self.remove(save=False)
        # the last sequence frame at or before the onset (never a frame late), requested at the top of
        # that frame so the item's source-grid floor and overwriteClip's sequence floor both land on it
        raw = self.source_in if self.source_in is not None else onset(self.track)
        sin, req = in_point(raw, tl['fps'])
        self.source_in = sin
        out = es(r"""
(function(){
  var seq = app.project.activeSequence, root = app.project.rootItem; app.enableQE();
  var PATH = %s, SIN = %s, REQ = %s, END = %s, TRACK = %d, V = %s, VMIN = %s, TAIL = %s, tries = 0;
  while (seq.audioTracks.numTracks < TRACK + 1 && tries++ < 8)
    qe.project.getActiveSequence().addTracks(0, 0, 1, 1, seq.audioTracks.numTracks, 0, 0);
  if (seq.audioTracks.numTracks < TRACK + 1) return "ERROR: could not provision A" + (TRACK + 1);
  function findByPath(bin){ for (var i = 0; i < bin.children.numItems; i++) { var c = bin.children[i];
    if (c.type === ProjectItemType.BIN) { var f = findByPath(c); if (f) return f; }
    else if (c.getMediaPath && c.getMediaPath() === PATH) return c; } return null; }
  function findBin(name){ for (var i = 0; i < root.children.numItems; i++) { var c = root.children[i];
    if (c.type === ProjectItemType.BIN && c.name === name) return c; } return null; }
  var item = findByPath(root);
  if (!item) { var bin = findBin("music") || root.createBin("music"); app.project.importFiles([PATH], true, bin, false); item = findByPath(root); }
  if (!item) return "ERROR: import failed for " + PATH;
  var tr = seq.audioTracks[TRACK];
  item.setInPoint(REQ, 4); item.setOutPoint(SIN + END + 1e-4, 4);
  tr.overwriteClip(item, 0 + 1e-4);
  item.clearInPoint(4); item.clearOutPoint(4);
  var clip = null;
  for (var i = 0; i < tr.clips.numItems; i++) { var c = tr.clips[i]; if (c.projectItem && c.projectItem.getMediaPath() === PATH) clip = c; }
  if (!clip) return "ERROR: clip did not land on A" + (TRACK + 1);
  var t = new Time(); t.seconds = END; try { clip.end = t; } catch (e) {}
  var done = false;
  for (var k = 0; k < clip.components.numItems; k++) { var cm = clip.components[k];
    if (cm.displayName !== "Volume") continue;
    for (var q = 0; q < cm.properties.numItems; q++) { var pr = cm.properties[q];
      if (pr.displayName !== "Level") continue;
      var fs = clip.inPoint.seconds + (clip.end.seconds - TAIL), fe = clip.inPoint.seconds + clip.end.seconds - 0.001;
      pr.setTimeVarying(true);
      pr.addKey(fs); pr.setValueAtKey(fs, V, true);
      pr.addKey(fe); pr.setValueAtKey(fe, VMIN, true);
      done = true; } }
  if (!done) return "ERROR: no Volume > Level on the clip";
  return JSON.stringify({start: clip.start.seconds, end: clip.end.seconds, srcIn: clip.inPoint.seconds});
})()""" % (json.dumps(self.track), sin, req, tl['tlEnd'], TRACK, lvl_v(self.bed_db), lvl_v(FLOOR_DB), TAIL))
        if str(out).startswith('ERROR'): sys.exit(out)
        got = json.loads(out)
        print(f"+ A{TRACK + 1} {got['start']:.3f} → {got['end']:.3f} from source {got['srcIn']:.3f} (source start candidate {raw:.3f}) {self.bed_db:+d} dB, {TAIL:.1f}s tail  {os.path.basename(self.track)}")
        if not self.verify(quiet=True): sys.exit('readback drifted from the plan, not saving')
        self.plan_path.parent.mkdir(parents=True, exist_ok=True)
        self.plan_path.write_text(json.dumps({'track':self.track, 'bed_db':self.bed_db, 'source_in':got['srcIn'], 'tail':TAIL}, indent=2)+'\n', encoding="utf-8")
        sh('node', str(BRIDGE), 'save_project'); print('saved')
        return True

    def bounce(self):
        # regenerable QA scratch: NOT in audio/ (it would become "the newest track") and not in outputs/
        wav = Path(tempfile.gettempdir()) / f'{self.job.name}.music-bounce.wav'
        if wav.exists(): wav.unlink()
        preset = wav_preset()
        try:
            out = es(r"""
(function(){
  var seq = app.project.activeSequence, TRACK = %d, t;
  for (t = 0; t < seq.audioTracks.numTracks; t++) if (t !== TRACK) seq.audioTracks[t].setMute(1);
  var r = seq.exportAsMediaDirect(%s, %s, 0);
  for (t = 0; t < seq.audioTracks.numTracks; t++) if (t !== TRACK) seq.audioTracks[t].setMute(0);
  var m = []; for (t = 0; t < seq.audioTracks.numTracks; t++) m.push(seq.audioTracks[t].isMuted());
  return JSON.stringify({r: r, muted: m});
})()""" % (TRACK, json.dumps(str(wav)), json.dumps(preset)),
                     # the panel's watchdog kills a script at 45 s and reports a finished export as a failure
                     # (lanes/premiere/lab-notes.md § the bridge's output contract) — and this one leaves every
                     # other audio track MUTED behind it, so a false failure is worse here than anywhere else
                     timeout=1800000)
        except SystemExit:
            # the unmute is the LAST statement of that script, so a failure anywhere in it leaves every
            # other audio track muted — silently, and the next bounce or export would be music-only
            print('⚠ the bounce did not come back: every audio track except the music one may still be MUTED. '
                  'Unmute them in Premiere before anything else is exported.', file=sys.stderr)
            raise
        got = json.loads(out)
        if any(got['muted']): sys.exit(f"a track is still muted after the bounce: {got['muted']} — unmute by hand")
        if not wav.exists(): sys.exit(f"bounce failed: {got['r']}")
        whole, head = lufs(str(wav)), lufs(str(wav), 0.4)
        print(f"music-only bounce: {whole} LUFS integrated, first 0.4s {head} LUFS  ({wav})")
        if head is None or head < -60: sys.exit('✗ no music in the first 0.4s: the bed is not playing where it should')
        print('✓ the bed plays from the first frame')

    def remove(self, save=True):
        r = es(r"""
(function(){
  var seq = app.project.activeSequence, PATH = %s, TRACK = %d, n = 0;
  if (seq.audioTracks.numTracks <= TRACK) return JSON.stringify({n: 0});
  var tr = seq.audioTracks[TRACK];
  for (var i = tr.clips.numItems - 1; i >= 0; i--) { var c = tr.clips[i];
    if (c.projectItem && c.projectItem.getMediaPath() === PATH) { c.remove(false, false); n++; } }
  return JSON.stringify({n: n});
})()""" % (json.dumps(self.track), TRACK))
        n = json.loads(r)['n']
        print(f"removed {n} music clip(s) from A{TRACK + 1}")
        if n and save: sh('node', str(BRIDGE), 'save_project'); print('saved')


def main():
    a = sys.argv[1:]
    if not a or a[0].startswith('-'): sys.exit(__doc__)
    job = a[0]; mode = None; refit = False; track = None; bed = None; source_in = None
    i = 1
    while i < len(a):
        if a[i] in ('--apply', '--verify', '--bounce', '--remove'): mode = a[i][2:]
        elif a[i] == '--refit': refit = True
        elif a[i] == '--track': i += 1; track = a[i]
        elif a[i] == '--bed-db': i += 1; bed = int(a[i])
        elif a[i] == '--source-in': i += 1; source_in = float(a[i])
        else: sys.exit(f'unknown arg {a[i]}\n{__doc__}')
        i += 1
    if refit: mode = mode or 'apply'
    if refit and mode != 'apply': sys.exit(f'--refit goes with --apply, not --{mode}')
    if not mode: sys.exit(__doc__)
    p = Placer(job, track, bed, source_in)
    if mode == 'apply': sys.exit(0 if p.apply(refit) else 1)
    elif mode == 'verify': sys.exit(0 if p.verify() else 1)
    elif mode == 'bounce': p.bounce()
    elif mode == 'remove': p.remove()


if __name__ == '__main__':
    main()
