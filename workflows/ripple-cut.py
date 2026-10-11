#!/usr/bin/env python3
"""ripple-cut.py: re-time everything a cut change moves — the transcript clock, the graphics plan, the placement,
the SFX cues and the text-animation metas — from the OLD EDL to the current one, in one pass.

  uv run workflows/ripple-cut.py projects/<job>                                  # DRY RUN: what moves, what breaks
  uv run workflows/ripple-cut.py projects/<job> --from transcript/cuts.pre-six-lead.json
  uv run workflows/ripple-cut.py projects/<job> --apply                          # write, each file backed up first

  --from <edl>   the EDL the downstream layers were authored against (default transcript/cuts.pre-recut.json)
  --to <edl>     the EDL they must land on (default transcript/cuts.json)
  --tag <name>   backup suffix on --apply (default pre-ripple: placement.pre-ripple.json …)
  --fps <r>      the grid shifts are reported on (default: the plan's fps, else 24000/1001)
  --apply        actually write

Every anchor is mapped THROUGH THE SOURCE, never by one global offset: old timeline time -> the source frame it
shows -> where that source frame sits on the new timeline. A row whose material was cut away is reported as
ORPHANED and left alone; a row whose span now straddles a new cut is reported as STRADDLING and moved by its start
only, because a placed render has a fixed duration and cannot absorb a hole.

Exit 0 = every row landed. Exit 1 = rows are still on a DEAD ANCHOR: they keep their old times while the plan
carries the NEW cut_rev, so place-graphics.py's stale-plan guard waves them through. Re-anchor or delete each one
before the lane's placers run — nothing downstream reads the `ripple` marker this writes.

THE LAYOUT MAP (a plan with a top-level `layout`, the Talking Head Explainer's layout.md § 12) is re-tiled through
the source too: each span keeps the material it framed. An edge whose frame was cut away moves to the span's nearest
surviving material and is reported as a DEAD EDGE: it counts toward exit 1 only when the neighbouring span's edge was
cut too (the switch itself is gone, so the layout wants a look); when the neighbour's edge maps cleanly the span only
lost the sentence at the switch, and it is listed at the end as a switch to check. A span whose material was all cut
is DROPPED (checked FIRST, so a cut first or last span is dropped, never crashed on); a gap left between two spans is
CLOSED by extending the earlier one (reported); the first span starts at 0 and the last ends on the new duration.
Every cell's `shot_cuts` (the speech-anchored picture cuts inside its render) are mapped each through the source, and
one on cut material is dropped and named. A captions cell starting at 0 is re-fit to the new duration. Each
`layout_deviations[].at` is re-mapped (on cut material: ORPHANED). A `variants.<name>` (from, layout, cells or beats,
duration, its waivers) moves rigidly by the shift of its `from`, which is re-mapped like any start: its tail is its own
EDL's material, which an organic re-cut does not touch. Crowns in face-frame.json are named for a re-read.

--apply writes NOTHING until every step has computed: each file is then backed up and written in one go.

What this tool does NOT do, on purpose: the timeline half. Re-lay V1/A1 from the new EDL, re-apply the audio polish,
move the grade clip, then let the lane's own placers re-place from the files this rewrote.

Why this exists (2026-09-19): a fluff pass asked for AFTER the grade and the graphics were done rebuilt every
downstream layer by hand — the transcript clock, 29 plan rows, 26 placed outro graphics, the text metas, the SFX
cues, the grade span and the baked camera moves, each by its own throwaway script, and then twice more for the two
hand re-cuts that followed. Each of those scripts hard-coded that job's sequence name and tick constant, so none of
it survived the job. The measurement is the same every time: this is it.

The rule this serves: edit-video § the cut is locked — a cut change after step 3 is a declared RE-CUT, and the
re-time runs before anything is touched on the timeline.
"""
import argparse, difflib, hashlib, json, re, shutil, subprocess, sys, tempfile
from pathlib import Path

for _s in (sys.stdout, sys.stderr):  # Windows pipes default to cp1252, which cannot encode the status glyphs
    try:
        if (getattr(_s, "encoding", "") or "").lower().replace("-", "") != "utf8":
            _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

EPS = 1e-4


def load_edl(path):
    return load_edl_doc(json.load(open(path, encoding='utf-8')))


def load_edl_doc(doc):
    """Segments in EDL order, each with its source span and the timeline span it lands on."""
    segs = doc['segments']
    rows, t = [], 0.0
    for s in segs:
        dur = float(s['end']) - float(s['start'])
        rows.append(dict(clip=Path(s.get('clip', '')).name, s0=float(s['start']), s1=float(s['end']),
                         t0=t, t1=t + dur))
        t += dur
    return rows, t


def fps_of(text):
    num, _, den = str(text).partition('/')
    return float(num) / float(den or 1)


def overlap(a, b):
    return 0.0 if a['clip'] != b['clip'] else max(0.0, min(a['s1'], b['s1']) - max(a['s0'], b['s0']))


class Ripple:
    """Old segment -> new segment, IN ORDER, then the source frame inside it.

    Matching is ordinal, not a source lookup: a cold open replays material the body also uses, and a pure
    "which segment holds this source time" search happily sends the hook's graphics into the demo.
    """

    def __init__(self, old, new):
        self.old, self.new = old, new
        key = lambda r: (r['clip'], round(r['s0'], 2), round(r['s1'], 2))
        blocks = difflib.SequenceMatcher(a=[key(r) for r in old], b=[key(r) for r in new],
                                         autojunk=False).get_matching_blocks()
        self.match = {a + d: b + d for a, b, size in blocks for d in range(size)}
        for i in range(len(old)):                    # a segment whose head or tail was trimmed keeps no key, but
            if i in self.match:                      # it still lies between its neighbours: take the best overlap
                continue
            lo = max((self.match[k] for k in self.match if k < i), default=-1)
            hi = min((self.match[k] for k in self.match if k > i), default=len(new))
            cands = [(overlap(old[i], new[k]), k) for k in range(lo + 1, hi)]
            best = max(cands, default=(0.0, None))
            if best[0] > 0:
                self.match[i] = best[1]

    def map(self, t, side='start'):
        """-> (new timeline time, why) where why is None, 'past-the-end', 'cut' or 'trimmed'.

        A time that lands exactly ON a joint belongs to TWO segments. A start anchor belongs to the one it opens
        (search backwards, last match wins); an end anchor to the one it closes (search forwards). Reading it the
        other way round orphans a graphic that comes in on a cut whenever the outgoing segment is the one removed.
        """
        order = reversed(range(len(self.old))) if side == 'start' else range(len(self.old))
        for i in order:
            o = self.old[i]
            if not (o['t0'] - EPS <= t <= o['t1'] + EPS):
                continue
            j = self.match.get(i)
            if j is None:
                return None, 'cut'
            n, u = self.new[j], o['s0'] + (t - o['t0'])
            if u < n['s0'] - EPS or u > n['s1'] + EPS:   # the frame itself was trimmed off this segment's head/tail
                return n['t0'] + min(max(u, n['s0']), n['s1']) - n['s0'], 'trimmed'
            return n['t0'] + (u - n['s0']), None
        return None, 'past-the-end'


def rewrite(rip, rows, keys, fps, label, out, orphans=None):
    """Move each row by its START; a fixed-length render keeps its own duration. Returns the notes to print.

    `orphans` collects '<label> <name>' for every row left on a dead anchor, because NOTHING downstream
    reads the `ripple` marker: the lane's placers would lay those rows at their pre-recut times under a
    freshly stamped cut_rev. The run reports them as a block and fails, rather than trusting the note.
    """
    notes = []
    for row, name in rows:
        start = row.get(keys[0])
        if start is None:
            continue
        if row.get('ripple') == 'orphaned':
            # Marked by an earlier ripple. Its times mean nothing now, so re-mapping them would invent a position.
            notes.append(f'  ORPHANED  {label} {name}: still orphaned from an earlier re-cut — re-anchor it or delete the row')
            if orphans is not None:
                orphans.append(f'{label} {name}')
            continue
        new_start, why = rip.map(float(start), 'start')
        if why in ('cut', 'past-the-end'):
            row['ripple'] = 'orphaned'
            notes.append(f'  ORPHANED  {label} {name}: {start:.3f}s {"is past the new end" if why == "past-the-end" else "was cut away"} — marked, left where it was, decide by hand')
            if orphans is not None:
                orphans.append(f'{label} {name}')
            continue
        if why == 'trimmed':
            notes.append(f'  TRIMMED   {label} {name}: the frame it was anchored on is gone; pinned to the new join at {new_start:.3f}s')
        shift = new_start - float(start)
        if len(keys) > 1 and row.get(keys[1]) is not None:
            end = float(row[keys[1]])
            new_end, why_end = rip.map(end, 'end')
            if why_end in ('cut', 'past-the-end') or abs((new_end - new_start) - (end - float(start))) > 0.5 / fps:
                notes.append(f'  STRADDLING {label} {name}: {start:.3f}–{end:.3f}s now spans a cut — moved by its start, '
                             f're-check its tail (and any render trimmed to the old join)')
            row[keys[1]] = round(new_start + (end - float(start)), 6)
        row[keys[0]] = round(new_start, 6)
        if abs(shift) > 0.5 / fps:
            out.append((name, float(start), new_start, shift))
    return notes


def layout_rows(rows):
    """[(start, end, mode, rest)] from a plan `layout`: {start, end, mode, ...} or [start, end, mode, ...] rows,
    `rest` = the row itself so its other fields ride along."""
    out = []
    for r in rows or []:
        a, b, m = (r['start'], r['end'], r['mode']) if isinstance(r, dict) else (r[0], r[1], r[2])
        out.append((float(a), float(b), m, r))
    return sorted(out, key=lambda x: x[0])


def _set(r, a, b):
    if isinstance(r, dict):
        return dict(r, start=round(a, 6), end=round(b, 6))
    return [round(a, 6), round(b, 6), *list(r)[2:]]


def remap_layout(rip, rows, old_dur, new_dur, fps, label, orphans, moved=None):
    """(new layout rows, notes): the map re-tiled on the new timeline (see the header, THE LAYOUT MAP). A DEAD EDGE
    whose neighbour's matching edge still maps cleanly is a sentence lost at the switch, not a lost switch: it goes to
    `moved` (a check, printed at the end), and only an edge whose neighbour's edge was cut too joins `orphans`."""
    notes, spans = [], []
    tol = 0.5 / fps

    def surviving(a, b, side):
        """the span's first (side='start') or last (side='end') moment of material the new EDL keeps."""
        segs = [o for i, o in enumerate(rip.old) if rip.match.get(i) is not None and o['t1'] > a + EPS and o['t0'] < b - EPS]
        if not segs:
            return None
        return rip.map(max(a, segs[0]['t0']), 'start')[0] if side == 'start' else rip.map(min(b, segs[-1]['t1']), 'end')[0]

    rows_ = layout_rows(rows)
    dead = lambda why: why in ('cut', 'past-the-end')
    edge = []                                   # per row: (start why, end why) as mapped, before any pin
    for a, b, m, r in rows_:
        edge.append((None if a <= EPS else rip.map(a, 'start')[1], None if b >= old_dur - EPS else rip.map(b, 'end')[1]))
    for k, (a, b, m, r) in enumerate(rows_):
        if surviving(a, b, 'start') is None:        # FIRST: a span with no surviving material is gone, whatever the
            notes.append(f'  DROPPED   {label} {m} {a:.3f}–{b:.3f}s: all of its material was cut')   # 0 / end pins say
            continue
        na, wa = (0.0, None) if a <= EPS else rip.map(a, 'start')
        nb, wb = (new_dur, None) if b >= old_dur - EPS else rip.map(b, 'end')
        for side, why in (('start', wa), ('end', wb)):
            if dead(why):
                t = surviving(a, b, side)
                if side == 'start': na = t
                else: nb = t
                j = k - 1 if side == 'start' else k + 1
                lost = not (0 <= j < len(rows_)) or dead(edge[j][1 if side == 'start' else 0])
                notes.append(f'  DEAD EDGE {label} {m} {a:.3f}–{b:.3f}s: its {side} ({a if side == "start" else b:.3f}s) '
                             f'was cut away, moved to its surviving material at {t:.3f}s: check the switch'
                             + ('' if lost else ' (the neighbouring edge maps cleanly: the switch survives)'))
                (orphans if lost else (moved if moved is not None else [])).append(f'{label} {m} {a:.3f}s ({side})')
            elif why == 'trimmed':
                notes.append(f'  TRIMMED   {label} {m} {a:.3f}–{b:.3f}s: its {side} frame is gone, pinned to the new join')
        if nb - na <= tol:
            notes.append(f'  DROPPED   {label} {m} {a:.3f}–{b:.3f}s: collapsed to nothing on the new timeline')
            continue
        spans.append([na, nb, m, r])
    spans.sort(key=lambda x: x[0])
    if spans and spans[0][0] > tol:
        notes.append(f'  GAP       {label}: nothing framed 0–{spans[0][0]:.3f}s, the first span extended to 0')
    if spans:
        spans[0][0] = 0.0
    for x, y in zip(spans, spans[1:]):
        if y[0] - x[1] > tol:
            notes.append(f'  GAP       {label}: {x[1]:.3f}–{y[0]:.3f}s left unframed, closed by extending the {x[2]} before it')
        elif x[1] - y[0] > tol:
            notes.append(f'  OVERLAP   {label}: {x[2]} ran {x[1] - y[0]:.3f}s into the {y[2]} after it, cut at {y[0]:.3f}s')
        x[1] = y[0]
    if spans:
        spans[-1][1] = new_dur
    return [_set(r, a, b) for a, b, m, r in spans], notes


def remap_times(rip, ts, label, notes):
    """Timeline times (a cell's shot_cuts) mapped each through the source -> the survivors; one on cut material is
    dropped and named. A picture cut inside a render is speech-anchored: a hole inside the cell moves the cuts after it."""
    out = []
    for t in ts or []:
        n, why = rip.map(float(t), 'start')
        if why in ('cut', 'past-the-end'):
            notes.append(f'  DROPPED   {label} shot cut {float(t):.3f}s: its material was cut')
            continue
        out.append(round(n, 6))
    return out


def report(label, out, fps, notes):
    if not out and not notes:
        print(f'{label}: nothing moves')
        return
    shifts = sorted({round(s, 3) for _, _, _, s in out})
    print(f'{label}: {len(out)} row(s) move, {min(shifts) if shifts else 0:+.3f}s … {max(shifts) if shifts else 0:+.3f}s '
          f'({min(shifts) * fps if shifts else 0:+.0f} … {max(shifts) * fps if shifts else 0:+.0f} frames)')
    for name, a, b, s in out[:6]:
        print(f'    {name:<10} {a:9.3f} -> {b:9.3f}  ({s:+.3f}s / {s * fps:+.0f} fr)')
    if len(out) > 6:
        print(f'    … {len(out) - 6} more')
    for n in notes:
        print(n)


PENDING = []   # every write of an --apply run, made only once every step has been computed (flush)


def save(path, doc, tag, apply, indent=1):
    """Queue the file's new content (--apply): nothing is written until the whole run has computed, so a failure
    part-way leaves every file as it was, never a transcript re-clocked under an un-rippled plan."""
    if not apply:
        return
    PENDING.append((path, json.dumps(doc, indent=indent).encode('utf-8'), tag))


def flush():
    """Write every queued file, each backed up first (a backup already there is kept: it is the pre-ripple original)."""
    for path, body, tag in PENDING:
        backup = path.with_suffix(f'.{tag}{path.suffix}')
        if not backup.exists():
            backup.write_bytes(path.read_bytes())
        path.write_bytes(body)
    PENDING.clear()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('job')
    ap.add_argument('--from', dest='src', default='transcript/cuts.pre-recut.json')
    ap.add_argument('--to', dest='dst', default='transcript/cuts.json')
    ap.add_argument('--tag', default='pre-ripple'); ap.add_argument('--fps')
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--force', action='store_true', help='ripple again even though the job already names the target EDL')
    a = ap.parse_args()
    job = Path(a.job).resolve()
    old_path, new_path = job / a.src, job / a.dst
    for p in (old_path, new_path):
        if not p.exists():
            sys.exit(f'✗ no {p}')
    old, old_dur = load_edl(old_path)
    new, new_dur = load_edl(new_path)
    rip = Ripple(old, new)

    plan_path = next((p for p in (job / 'graphics-plan.json', job / 'hf-graphics' / 'graphics-plan.json') if p.exists()), None)
    plan = json.load(open(plan_path, encoding='utf-8')) if plan_path else None
    fps = fps_of(a.fps or (plan or {}).get('fps') or '24000/1001')
    new_rev = hashlib.sha1(new_path.read_bytes()).hexdigest()[:12]

    # A RE-RUN IS THE DANGEROUS CASE. Every anchor is read as an OLD-timeline time, so a second pass over
    # already-rippled files maps them a second time: rows double-shift onto each other and the ones that landed
    # where cut material used to be come back marked ORPHANED — and the run reports all of it as ordinary work.
    # The plan's cut_rev is the stamp that says which EDL these files are already on.
    if plan is not None and plan.get('cut_rev') == new_rev and not a.force:
        sys.exit(f'✗ {plan_path.name} already carries cut_rev {new_rev}: this job is ALREADY timed against '
                 f'{new_path.name}.\n  A second pass would re-map times that are on the NEW timeline and silently '
                 f'double-shift them. Nothing was read or written.\n  Restore from the .{a.tag}. backups if a pass '
                 f'went wrong, or pass --force if the stamp itself is wrong.')
    old_rev = hashlib.sha1(old_path.read_bytes()).hexdigest()[:12]
    if plan is not None and plan.get('cut_rev') and plan['cut_rev'] not in (old_rev, new_rev):
        # --from is the BASELINE every anchor is read against, and picking the wrong snapshot out of a folder
        # of them maps every row from a timeline the plan was never on — silently, because the arithmetic is
        # just as well-behaved. The stamp is the only thing that knows which one it was.
        print(f'⚠ {plan_path.name} is stamped cut_rev {plan["cut_rev"]}, but --from {old_path.name} is {old_rev}: '
              f'this is NOT the EDL the plan was authored against. Every row would be mapped off the wrong '
              f'baseline. Pick the snapshot whose sha1 matches the stamp before --apply.')
    if plan is None and (job / 'hf-graphics' / f'placement.{a.tag}.json').exists() and not a.force:
        print(f'⚠ hf-graphics/placement.{a.tag}.json already exists: a ripple has run here before. With no '
              f'graphics-plan.json to carry cut_rev, nothing can prove these files are not already re-timed — '
              f'check one row against the new EDL before --apply.')

    print(f'{old_path.name} -> {new_path.name}   {len(old)} segments / {old_dur:.3f}s  ->  {len(new)} / {new_dur:.3f}s '
          f'({new_dur - old_dur:+.3f}s, {(new_dur - old_dur) * fps:+.0f} frames at {fps:.3f} fps)')
    print(f'cut_rev {old_rev} -> {new_rev}'
          + ('' if a.apply else '   [DRY RUN: nothing is written]'))

    # 1. the canonical transcript — RE-DERIVED, not shifted
    tpath = job / 'outputs' / f'{job.name}.transcript.json'
    words_src = job / 'transcript' / 'words.json'
    exporter = Path(__file__).resolve().parent.parent / '.claude/skills/rough-cut/scripts/export-transcript.py'
    if tpath.exists() and words_src.exists() and exporter.exists():
        # The canonical transcript is a FUNCTION of words.json + the EDL, so the re-cut re-runs that function:
        # the repo's own law is to re-run a step from its durable inputs rather than patch its output. Shifting
        # the old file cannot give back a passage the re-cut RESTORED (those words are in words.json and in no
        # timeline at all), and it leaves the doc's `text` prose still describing lines the video no longer has.
        before = len(json.load(open(tpath, encoding='utf-8')).get('words', []))
        with tempfile.TemporaryDirectory(prefix='ripple-cut-') as td:
            # export-transcript.py finds the job's corrections.local.json from the OUT path's own parents
            # (<job>/outputs/<file> -> <job>/corrections.local.json), so a draft written flat into the temp
            # dir loses every per-job correction in silence — and the canonical transcript is where they are
            # applied ONCE (CLAUDE.md § transcript corrections). So the draft is written into a MIRROR of the
            # job layout with the override carried in beside it; the repo-wide map still resolves off the
            # exporter's own location.
            mirror = Path(td) / job.name / 'outputs'
            mirror.mkdir(parents=True)
            local = job / 'corrections.local.json'
            if local.exists():
                shutil.copyfile(local, mirror.parent / local.name)
            draft = mirror / tpath.name
            subprocess.run([sys.executable, str(exporter), str(words_src), str(new_path), str(draft)], check=True)
            after = len(json.load(open(draft, encoding='utf-8')).get('words', []))
            if after == 0 and before:
                print(f'✗ the re-derive produced 0 words from {words_src.name}: leaving {tpath.name} alone and '
                      f're-deriving nothing. Check that words.json covers the clips this EDL names.')
            else:
                print(f'transcript: re-derived from {words_src.name} + {new_path.name}, {before} -> {after} words'
                      + ('' if a.apply else '   (preview only, nothing written)'))
                if a.apply:
                    PENDING.append((tpath, draft.read_bytes(), a.tag))
    elif tpath.exists():
        # No words.json (an archived job, a client tree): shift what is there, and rebuild the prose with it.
        doc = json.load(open(tpath, encoding='utf-8'))
        kept, dropped = [], 0
        for w in doc.get('words', []):
            s, why = rip.map(float(w['start']), 'start')
            e, why_e = rip.map(float(w['end']), 'end')
            if why in ('cut', 'past-the-end') or why_e in ('cut', 'past-the-end'):
                dropped += 1
                continue
            w['start'], w['end'] = round(s, 3), round(e, 3)
            kept.append(w)
        doc['words'] = kept
        if 'text' in doc:   # the prose is the kept words: leaving it stale ships a script of lines that were cut
            doc['text'] = re.sub(r'\s+([,.!?;:])', r'\1', ' '.join(w.get('text', '') for w in kept)).strip()
        print(f'⚠ no {words_src.name}: SHIFTED the transcript clock instead of re-deriving it — {len(kept)} words '
              f're-clocked, {dropped} dropped. Restored material cannot come back this way.')
        save(tpath, doc, a.tag, a.apply)

    # 2. the graphics plan
    orphans, moved = [], []
    if plan:
        out = []
        beats = plan.get('beats') or plan.get('cells') or []
        # the caption layer spans the whole cut: it is re-fit to the new duration, never moved by its start (a moved
        # captions cell straddled every re-cut with end = the OLD duration, and the placer lays it to that end)
        is_caps = lambda b: (b.get('kind') == 'captions' or b.get('id') == 'captions') and float(b.get('start') or 0) <= EPS
        notes = []
        for b in beats:
            if is_caps(b) and b.get('end') is not None and abs(float(b['end']) - new_dur) > EPS:
                notes.append(f'  REFIT     beat {b.get("id", "captions")}: the caption layer now ends at {new_dur:.3f}s '
                             f'(was {float(b["end"]):.3f}s): rebuild it (captions.py)')
                b['end'] = round(new_dur, 6)
        notes += rewrite(rip, [(b, b.get('id', '?')) for b in beats if not is_caps(b)], ('start', 'end'), fps, 'beat', out, orphans)
        for b in beats:                                       # the picture cuts inside a render, each through the source
            if b.get('shot_cuts') and b.get('ripple') != 'orphaned' and not is_caps(b):
                b['shot_cuts'] = remap_times(rip, b['shot_cuts'], f'beat {b.get("id", "?")}', notes)
        if plan.get('layout'):
            before = len(plan['layout'])
            plan['layout'], lnotes = remap_layout(rip, plan['layout'], old_dur, new_dur, fps, 'layout', orphans, moved)
            notes += [f'  layout: {before} span(s) -> {len(plan["layout"])}'] + lnotes
        for d_ in plan.get('layout_deviations') or []:        # a waiver is matched to its finding within 0.5 s of `at`
            if d_.get('at') is None:
                continue
            n, why = rip.map(float(d_['at']), 'start')
            if why in ('cut', 'past-the-end'):
                notes.append(f'  ORPHANED  layout_deviations {d_.get("rule")} at {float(d_["at"]):.3f}s: its material was cut '
                             '— re-pin it or drop it')
                orphans.append(f'layout_deviations {d_.get("rule")} (at)')
                continue
            d_['at'] = round(n, 6)
        for name, v in (plan.get('variants') or {}).items():
            if not isinstance(v, dict) or v.get('from') is None:
                continue
            nf, why = rip.map(float(v['from']), 'start')
            if why in ('cut', 'past-the-end'):
                notes.append(f'  ORPHANED  variant {name}: its from {float(v["from"]):.3f}s was cut away — re-anchor it by hand')
                orphans.append(f'variant {name} (from)')
                continue
            # the variant's tail is its OWN EDL's material, which an organic re-cut does not touch: it moves rigidly
            d = nf - float(v['from'])
            v['from'] = round(nf, 6)
            v['layout'] = [_set(r, a + d, b + d) for a, b, m, r in layout_rows(v.get('layout'))]
            if v.get('duration') is not None:                 # layout.py compose_variant's end: it moves with the rest
                v['duration'] = round(float(v['duration']) + d, 6)
            for c in v.get('cells') or v.get('beats') or []:
                for k in ('start', 'end'):
                    if c.get(k) is not None: c[k] = round(float(c[k]) + d, 6)
                if c.get('shot_cuts'): c['shot_cuts'] = [round(float(t) + d, 6) for t in c['shot_cuts']]
            for d_ in v.get('layout_deviations') or []:
                if d_.get('at') is not None: d_['at'] = round(float(d_['at']) + d, 6)
            if abs(d) > 0.5 / fps:
                notes.append(f'  variant {name}: from, layout, cells, duration and waivers moved {d:+.3f}s with its from')
        for b in beats:                                       # a section job's own timeline anchors ride along
            if isinstance(b.get('_timeline'), list) and len(b['_timeline']) == 2:
                s, why = rip.map(float(b['_timeline'][0]), 'start')
                if not why:
                    b['_timeline'] = [round(s, 6), round(s + float(b['_timeline'][1]) - float(b['_timeline'][0]), 6)]
                else:   # never leave a second timing record behind: `start` moved and this one could not
                    notes.append(f'  ORPHANED  beat {b.get("id", "?")}: its _timeline anchor {b["_timeline"][0]:.3f}s '
                                 f'{"is past the new end" if why == "past-the-end" else "was cut away"} while its start moved — re-anchor it')
                    orphans.append(f'beat {b.get("id", "?")} (_timeline)')
        plan['duration'] = round(new_dur, 6)
        plan['cut_rev'] = new_rev                             # the plan now names the EDL it is valid against
        report('graphics plan', out, fps, notes)
        save(plan_path, plan, a.tag, a.apply)
        baked = [b.get('id', '?') for b in beats if b.get('push_in')]
        if baked:
            print(f'  RE-BAKE  {len(baked)} emphasis push-in(s) sit on V1 under {", ".join(baked)}: their anchors moved, '
                  f'the baked keyframes did not')
        print(f'  RE-BAKE  the opening zoom-out rides the first clip, and the grade layer now ends at {new_dur:.3f}s')

    # 3. placement, 4. SFX cues, 5. the text-animation metas
    place_path = job / 'hf-graphics' / 'placement.json'
    if place_path.exists():
        doc = json.load(open(place_path, encoding='utf-8'))
        rows = doc['rows'] if isinstance(doc, dict) and 'rows' in doc else doc   # both shapes, as review-frames.py reads it
        out = []
        notes = rewrite(rip, [(r, r.get('id', '?')) for r in rows], ('start', 'end'), fps, 'placed', out, orphans)
        report('placement', out, fps, notes)
        save(place_path, doc, a.tag, a.apply)

    sfx_path = job / 'hf-graphics' / 'sfx-plan.json'
    if sfx_path.exists():
        rows = json.load(open(sfx_path, encoding='utf-8'))
        out = []
        notes = rewrite(rip, [(r, r.get('id', r.get('gid', '?'))) for r in rows], ('at',), fps, 'cue', out, orphans)
        report('sfx cues', out, fps, notes)
        save(sfx_path, rows, a.tag, a.apply)

    # The text-animation folder is the one whose metas the lane's placer reads back for timing, so it is the
    # set that has to move. A timed meta under any OTHER comp folder is named rather than touched: re-timing a
    # file nothing reads is noise, and leaving one unnamed is how a second timing record drifts in silence.
    metas = sorted((job / 'hf-graphics' / 'text-animation' / 'compositions').glob('*.meta.json'))
    out, notes = [], []
    for m in metas:
        doc = json.load(open(m, encoding='utf-8'))
        notes += rewrite(rip, [(doc, m.stem.split('.')[0])], ('place', 'until'), fps, 'meta', out, orphans)
        save(m, doc, a.tag, a.apply, indent=2)
    if metas:
        report('text-animation metas', out, fps, notes)
    others = sorted(p for p in (job / 'hf-graphics').glob('*/compositions/*.meta.json')
                    if p.parent.parent.name != 'text-animation'
                    and {'place', 'until'} & set(json.load(open(p, encoding='utf-8'))))
    if others:
        print(f'⚠ {len(others)} timed meta(s) outside text-animation/ were NOT re-timed '
              f'({", ".join(sorted({p.parent.parent.name for p in others}))}): check them by hand')

    face = job / 'face-frame.json'
    try:
        crowns = json.loads(face.read_text(encoding='utf-8')).get('crowns') if face.exists() else None
    except ValueError:
        crowns = None
    if crowns:
        print(f'⚠ face-frame.json holds {len(crowns)} crown(s) read through the OLD cut: their timeline spans now hold other '
              'material. layout.py ignores a crown stamped with another EDL; re-read each card\'s crown '
              '(uv run workflows/face-frame.py projects/<job> --crown A B) before the card clearance is trusted.')
    if moved:
        print(f'\n⚠ {len(moved)} layout edge(s) moved onto surviving material (the sentence at the switch was cut, the '
              'switch itself survives): check each switch on the new cut')
        for name in moved:
            print(f'    {name}')

    if orphans:
        # THE STAMP DOES NOT COVER THESE ROWS. cut_rev says "timed against this EDL", and place-graphics.py
        # believes it — so a row left on a dead anchor is placed at its PRE-RECUT time with a green stamp on
        # the plan, which is the exact bug this tool exists to prevent. Nothing downstream reads `ripple`,
        # so the run ends non-zero instead of on a note in the middle of a long report.
        print(f'\n✗ {len(orphans)} row(s) are still on a DEAD ANCHOR and were left at their old times:')
        for name in orphans[:20]:
            print(f'    {name}')
        if len(orphans) > 20:
            print(f'    … {len(orphans) - 20} more')
        print('  Nothing downstream reads the `ripple` marker: re-anchor each row (or delete it) BEFORE the '
              'lane\'s placers run, or they go down at their pre-recut times under a current cut_rev.')
    flush()
    print('\nNEXT, on the lane: re-lay V1/A1 from the new EDL, re-apply the audio polish, move the grade clip to the '
          f'new end, re-place from these files, re-bake the moves above, then prove the cut.'
          + ('' if a.apply else '\nNothing was written: re-run with --apply once the numbers above read right.'))
    return 1 if orphans else 0


if __name__ == '__main__':
    sys.exit(main())
