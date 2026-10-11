#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy"]
# ///
"""flash-scan.py: the whole-program gate for single-frame flashes, double cuts and unexpected hard cuts, run on each
exported file before it is delivered (where it binds: WHERE IT BINDS, below). It reads the export itself, so it needs
no extra draft.

  uv run workflows/flash-scan.py <video>                                   # flashes + double cuts; every hard cut listed
  uv run workflows/flash-scan.py <video> --expect projects/<job>           # + every hard cut checked against the plan
  uv run workflows/flash-scan.py <video> --expect projects/<job> --variant ad    # the ad deliverable's own boundaries
  uv run workflows/flash-scan.py <video> --expect-times 4.63,7.84 ...      # + checked against these times (seconds)
  ... --json OUT.json                                                      # every cut and finding, machine-readable

WHY. On a layered edit every planned boundary is several layers switching on one frame: the footage framing, the
graphic, the caption line, the V1 clip. One layer a frame off is a frame of footage with no panel over it, a blank
panel between two shots, a caption left in the wrong band for a frame. Stills never land on it and a watch at speed
rarely sees it, but a viewer's eye does. It only exists in the finished composite, so it is measured there.

HOW. ffmpeg decodes every frame to a 90 px-wide grey thumbnail (90x160 on 9:16, 160x90 on 16:9: exact enough to see a
panel, small enough for a whole program in seconds), with -vsync 0 (a constant-rate read duplicates a frame on any file
with audio). D[i] is the mean absolute difference between frame i-1 and frame i, on 0-255 grey. Then:
  FLASH       frame i differs from BOTH neighbours (D[i] and D[i+1] >= 2) while the neighbours match each other
              (|f[i+1] - f[i-1]| <= 0.4 x the smaller of the two). A stray frame, a blank panel body for one frame, a
              card missing for one frame.
  DOUBLE CUT  a shot one or two frames long between two hard changes, the picture HELD on both outer sides: the two
              diffs before the first change and the two after the last are each at most half of the change they
              border. One frame: two or three changes on consecutive frames, each frame between them a one-frame
              shot. Two frames: two changes two frames apart, the diff between them at most half of the smaller. A
              panel landing a frame or two after its framing switch, a blank frame between two shots, a caption line
              changing a frame after the picture, a V1 cut landing a frame or two before its layout switch.
              A change is hard at D >= 6.5, or from D >= 2 on a planned boundary of its OWN (--expect: within 1
              frame of it and nearer it than the shot's other change): a V1 jump cut inside one framing moves the
              whole frame by only 3-6, and two planned boundaries one or two frames apart are the defect however
              small either change is. "Of its own" keeps a frame of wobble just after a planned cut from borrowing
              that cut's boundary. A two-frame shot also needs one of its changes on a planned boundary, so it is
              judged only against a plan: off the plan, a graphic or a screen capture animated on twos (each drawing
              held two frames) has exactly this shape.
              The hold is two frames because a stepped scroll (two frames moving, one holding: a terminal log, a
              feed) looks like a pair of cuts against one held frame, and never holds for two; and an entrance
              animated on twos steps again two frames after its first step, so a cut into one stays motion.
  HARD CUT    one change (D >= 8) at least twice the diff on either side of it.
Every finding must also stand at least 4x above the local motion: the median diff over the 8 frames on each side of
it (the event and its borders left out), the calmer side. A jittering or shaking graphic is busy on both sides, so
it stays motion; a real stray frame has at least one calm side, even inside a capture that drifts.
Four or more hard changes in a row are motion (a fast slide), never three one-frame shots.

EXPECTED BOUNDARIES (--expect projects/<job>). A hard cut within 1 frame of one is expected; any other is an UNEXPECTED
CUT, a WARNING (a capture's own UI cuts: a message arriving, a page loading, an element that pops in one frame). Read
each one: it is a capture event or a boundary that landed off its plan. The boundaries come from graphics-plan.json and
transcript/cuts.json:
  - a plan with a top-level `layout` array (the talking-head explainer contract) goes through that preset's
    layout.py `breaks()`: the V1 cuts, every layout edge, every graphic cell's edges and every cell's `shot_cuts`,
    the same list its caption breaks are forced on;
  - any other plan: the V1 cuts, every graphic cell's start and end, and its `shot_cuts`.
--variant NAME composes the plan's `variants.NAME` in (layout.py compose_variant) and reads transcript/cuts.NAME.json.
The file's frame count is compared with the plan's duration: a mismatch means the wrong deliverable or a partial
export, and is warned.

THE LIMIT. A whole-frame mean sees what changes a visible share of the frame. A blank chat body under a pinned header
barely moved it on a mostly dark panel: the job-local scan this replaces missed two, because its hard-cut floor sat far
above them. At these floors both read here (one as a flash, one as a double cut). A defect confined to a small region
(a caption word, a single icon) is below any whole-frame floor; the per-graphic gates own those
(`workflows/graphics-qa-short.py`, the caption builder's own check).
A layer a frame or two off a planned boundary with a change under 6.5 (a caption line a frame late on a big cut, a
V1 jump cut a frame early) has no boundary of its own, so it cannot be told from motion and is not seen here; the
talking-head explainer's layout.py L-NEARCUT keeps such edges out of the plan, not a lane from landing a layer off
one. The other way round, a graphic built to land two frames after a planned cut, or one that steps once on twos out
of it and holds, reads as a two-frame shot: put it on the cut.

Calibrated (2026-09-23) on 15 exports of one 2-minute 9:16 talking-head explainer (13 drafts, the final organic and
the ad; 43k frames), every candidate viewed: the positives were the two blank chat bodies above, a blank panel frame
between two capture shots, a frame of the old capture's empty backdrop between two shots, and a split panel arriving
with the previous caption still in the old band; 0 findings on the shipped final and ad. Stepped terminal-log scrolls,
a jittering window stack, a chat app's send animation and cuts into an entrance animation all stay motion. Each floor
sits inside the band where the corpus reads clean with every positive found: HARD 6-7.9 (5.5 fails a chat input box
growing as its text wraps; 8 misses a blank panel at 7.96), SETTLE 0.45-0.5 (0.4 misses the caption lag at 0.43; 0.55
fails a cut into an entrance animation), LOCAL 1-8 (10 misses the stray frame inside a drifting capture), MATCH
0.4-0.6 (0.8 fails the jittering stack; the real flash read 0.14), HOLD 2 (3 misses the triple; 1 fails a stepped
scroll whose steps pass HARD, the synthetic control).
The shipped final still warns 8 unexpected cuts against its plan as it stands (5 when calibrated), every one a
graphic's own event: a montage's shots, chat messages arriving in a capture, icons stepping in and out on twos.
Re-checked (2026-09-25) for the two-frame shot and the planned-boundary floor: the 15 exports read exactly as before,
the final with its plan too, and so do the final's Final Cut and Resolve rebuilds and the receptionist short (final
with its plan, ad), whose graphic exits in two steps on twos (7.6 then 7.5, off the plan: the rule that keeps it
motion). The closest calls in the corpus are the final's icons: a cut into their entrance on twos (106, 12.6, 9.0,
two frames apart; HOLD keeps it out) and a shrink on twos (8.2 then 5.0, off the plan). The positives are the Final
Cut rebuild of demo-project: four two-frame shots, a V1 jump cut (5.1-10.6) two frames before its layout switch
(43-47), both on planned boundaries; its fifth short shot, a V1 cut landed a frame before a planned switch (5.4 then
52.5), is THE LIMIT's lagging layer. Viewed then, the corpus's drafts carry three one-frame shots no version of this
scan sees without their plans, which are gone: a V1 jump cut a frame before a full-screen (5.3 then 44.9 in the
first two drafts) or before a panel and caption change (3.7 then 14.8 there, 4.2 then 7.0-10.6 in v2-v10), and a
caption line a frame late on a cut (52.0 then 3.2 in the first two).

WHERE IT BINDS. The method is format-agnostic (any aspect, any plan), but exit 1 stops a delivery only where a step-8
definition of done names this scan. The talking-head explainer's does: its README § Export, on every deliverable, the
ad with --variant ad. The house step-8 row (edit-video's step table, CLAUDE.md pipeline row 8) is where it becomes
every job's gate. A format whose definition of done does not name it runs it as a report line, not a stop; and since
the floors above were calibrated on 9:16 only, a first run on a 16:9 program is read finding by finding before its
exit code is trusted. Exit 0 does not mean every hard cut was expected: read the warnings.

Exit 0 = no flash, no double cut (unexpected cuts are warnings). Exit 1 = a flash or a double cut. Exit 2 = the video
or an --expect input cannot be read.
"""
import argparse
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
from fractions import Fraction
from pathlib import Path

for _s in (sys.stdout, sys.stderr):  # Windows pipes default to cp1252, which cannot encode the status glyphs
    try:
        if (getattr(_s, "encoding", "") or "").lower().replace("-", "") != "utf8":
            _s.reconfigure(encoding="utf-8")
    except Exception:
        pass
import numpy as np

REPO = Path(__file__).resolve().parent.parent
LAYOUT_PY = REPO / "presets" / "instagram" / "talking-head-explainer" / "layout.py"

SHORT_SIDE = 90     # px: the thumbnail's short side (90x160 on 9:16)
FLASH_MIN = 2.0     # grey levels: a flash frame differs from each neighbour by at least this
MATCH = 0.4         # a flash's neighbours match: |f[i+1] - f[i-1]| <= MATCH x the smaller of its two diffs
HARD = 6.5          # grey levels: a change inside a double cut
CUT = 8.0           # grey levels: a lone hard cut
SETTLE = 0.5        # the diffs beside a double cut are at most this share of the change they border
HOLD = 2            # frames: the picture holds this long on each side of a double cut (a stepped scroll never does)
SPIKE = 2.0         # a lone hard cut is at least this many times the diff on either side of it
LOCAL = 4.0         # every finding stands this many times above the local motion
WINDOW = 8          # frames either side the local motion is measured over
MAX_RUN = 3         # hard changes in a row that can still be one-frame shots; more is motion
TOLERANCE = 1       # frames: a hard cut this close to an expected boundary is expected


class InputError(Exception):
    """An input that cannot be read: exit 2, named."""


# ── the video ───────────────────────────────────────────────────────────────────────────────────────────────────────
def probe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=width,height,avg_frame_rate,r_frame_rate", "-of", "json", str(path)],
                       capture_output=True, text=True)
    if r.returncode:
        raise InputError(f"ffprobe cannot read {path}: {(r.stderr.strip().splitlines() or ['?'])[-1]}")
    streams = json.loads(r.stdout or "{}").get("streams") or []
    if not streams:
        raise InputError(f"{path}: no video stream")
    s = streams[0]
    fps = None
    for key in ("avg_frame_rate", "r_frame_rate"):
        try:  # Windows ffprobe builds can print a trailing comma
            v = Fraction(str(s.get(key) or "0/0").strip().rstrip(","))
        except (ValueError, ZeroDivisionError):
            continue
        if v > 0:
            fps = float(v)
            break
    if not fps:
        raise InputError(f"{path}: no frame rate")
    return int(s["width"]), int(s["height"]), fps


def thumb_size(w, h):
    """The grey thumbnail: SHORT_SIDE on the short side, the aspect kept, even sides."""
    if w <= h:
        return SHORT_SIDE, max(2, int(round(SHORT_SIDE * h / w / 2)) * 2)
    return max(2, int(round(SHORT_SIDE * w / h / 2)) * 2), SHORT_SIDE


def measure(path, tw, th):
    """(D, M): D[i] = mean |f[i] - f[i-1]| (D[0] = 0), M[i] = mean |f[i+1] - f[i-1]| (0 at the two ends), on the
    grey thumbnails of every frame, streamed so a long program never sits in memory."""
    size = tw * th
    cmd = ["ffmpeg", "-v", "error", "-nostdin", "-i", str(path), "-map", "0:v:0", "-vsync", "0",
           "-vf", f"scale={tw}:{th}:flags=area,format=gray", "-f", "rawvideo", "-pix_fmt", "gray", "-"]
    D, M = [0.0], []
    prev2 = prev1 = None
    with tempfile.TemporaryFile() as errf:  # a file, not a pipe: a damaged export can print an error per frame
        with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=errf) as p:
            while True:
                buf = p.stdout.read(size * 64)
                if not buf:
                    break
                while len(buf) % size:  # a pipe read can stop mid-frame
                    more = p.stdout.read(size - len(buf) % size)
                    if not more:
                        break
                    buf += more
                n = len(buf) // size
                frames = np.frombuffer(buf[:n * size], np.uint8).reshape(n, th, tw).astype(np.int16)
                for f in frames:
                    if prev1 is not None:
                        D.append(float(np.abs(f - prev1).mean()))
                    if prev2 is not None:
                        M.append(float(np.abs(f - prev2).mean()))
                    prev2, prev1 = prev1, f
        errf.seek(0)
        err = errf.read().decode(errors="replace").strip()
    if prev1 is None:
        raise InputError(f"ffmpeg decoded no frames from {path}: {(err.splitlines() or ['?'])[-1]}")
    n = len(D)
    return np.array(D), np.array([0.0] + M + [0.0])[:n]


# ── the scan ────────────────────────────────────────────────────────────────────────────────────────────────────────
def local_motion(D, a, b):
    """The motion an event D[a..b] must stand above: the median diff over WINDOW frames on each side of it (the event
    and the two diffs bordering it left out), the calmer side. A jittering or scrolling graphic is busy on both sides;
    a real cut or stray frame has at least one calm side, even when it lands inside a moving capture."""
    before = D[max(1, a - 1 - WINDOW):max(1, a - 1)]
    after = D[b + 2:b + 2 + WINDOW]
    sides = [float(np.median(x)) for x in (before, after) if len(x)]
    return min(sides) if sides else 0.0


def scan(D, M, expected=()):
    """{'flashes': [...], 'doubles': [...], 'cuts': [...]} on the frame diffs. A flash or double cut names its one- or
    two-frame shot(s); a cut names the first frame of the new picture. `expected`: the planned boundary frames, where a
    change inside a double cut counts from FLASH_MIN instead of HARD (planned(), below)."""
    n = len(D)
    d = lambda i: float(D[i]) if 0 <= i < n else 0.0
    flashes, doubles, taken = [], [], set()
    expected = set(expected)

    def planned(k, others):
        """A boundary of k's own: within TOLERANCE of k and nearer k than any other change of the shot. A frame of
        encoder or footage wobble just after a planned cut is nearer the cut's change: it never borrows its boundary."""
        return any(b in expected and all(abs(b - k) < abs(b - o) for o in others)
                   for b in range(k - TOLERANCE, k + TOLERANCE + 1))

    def change(k, shot):
        return d(k) >= HARD or (d(k) >= FLASH_MIN and planned(k, [o for o in shot if o != k]))

    def settled(i, j):
        return (max(d(i - k) for k in range(1, HOLD + 1)) <= SETTLE * D[i]
                and max(d(j + k) for k in range(1, HOLD + 1)) <= SETTLE * D[j])

    # FLASH: frame i differs from both neighbours, and the neighbours match
    for i in range(1, n - 1):
        lo = min(D[i], D[i + 1])
        if lo >= FLASH_MIN and M[i] <= MATCH * lo and lo >= LOCAL * local_motion(D, i, i + 1):
            flashes.append(dict(frames=[i], into=round(d(i), 2), out=round(d(i + 1), 2),
                                neighbours=round(float(M[i]), 2)))
            taken.add(i)

    # DOUBLE CUT: 2..MAX_RUN hard changes in a row, the picture settled on both sides of them
    for i in range(1, n):
        for j in range(i + 1, min(n, i + MAX_RUN)):
            shot = range(i, j + 1)
            if any(k in taken for k in range(i, j)) or not all(change(k, shot) for k in shot):
                continue
            lo = float(D[i:j + 1].min())
            if settled(i, j) and lo >= LOCAL * local_motion(D, i, j):
                if j == i + 1 and M[i] <= MATCH * lo:   # the two neighbours match: a flash after all
                    flashes.append(dict(frames=[i], into=round(d(i), 2), out=round(d(j), 2),
                                        neighbours=round(float(M[i]), 2)))
                else:
                    doubles.append(dict(frames=list(range(i, j)), changes=list(range(i, j + 1)),
                                        diffs=[round(d(k), 2) for k in range(i, j + 1)]))
                taken.update(range(i, j))
                break

    # DOUBLE CUT, a two-frame shot: two changes two frames apart, the frame between them held, settled on both sides,
    # at least one of them on a planned boundary (an animation or a capture on twos has this shape off the plan)
    on_plan = lambda k: any(b in expected for b in range(k - TOLERANCE, k + TOLERANCE + 1))
    for i in range(1, n - 2):
        j = i + 2
        if (i in taken or i + 1 in taken or not (on_plan(i) or on_plan(j))
                or not (change(i, (i, j)) and change(j, (i, j)))):
            continue
        lo = min(d(i), d(j))
        if d(i + 1) <= SETTLE * lo and settled(i, j) and lo >= LOCAL * local_motion(D, i, j):
            doubles.append(dict(frames=[i, i + 1], changes=[i, j], diffs=[round(d(i), 2), round(d(j), 2)]))
            taken.update((i, i + 1))

    # HARD CUT: one change, well above the diffs either side of it
    cuts = []
    for i in range(1, n):
        if (D[i] >= CUT and D[i] >= SPIKE * max(d(i - 1), d(i + 1))
                and D[i] >= LOCAL * local_motion(D, i, i)):
            cuts.append(dict(frame=i, diff=round(d(i), 2)))
    flashes.sort(key=lambda e: e["frames"][0])
    doubles.sort(key=lambda e: e["frames"][0])
    return dict(flashes=flashes, doubles=doubles, cuts=cuts)


# ── the expected boundaries ─────────────────────────────────────────────────────────────────────────────────────────
def _load_json(path, what):
    if not path.is_file():
        raise InputError(f"{what}: no file at {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except ValueError as e:
        raise InputError(f"{what}: {path} is not JSON ({e})")


def _layout_module():
    if not LAYOUT_PY.is_file():
        raise InputError(f"the plan carries a `layout` array but {LAYOUT_PY} is missing")
    spec = importlib.util.spec_from_file_location("talking_head_layout", LAYOUT_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _fps(v):
    if isinstance(v, str) and "/" in v:
        n, dd = v.split("/")
        return float(n) / float(dd)
    return float(v)


def _v1_cuts(cuts, plan):
    """The interior V1 cuts on the plan's clock: the `_timeline` readback when every segment carries one, else the
    cumulative kept durations (the same reading as layout.py's v1_cuts)."""
    segs = (cuts or {}).get("segments") or []
    off = float(plan.get("timeline_offset") or 0)
    if segs and all(isinstance(s.get("_timeline"), list) for s in segs):
        ends = [float(s["_timeline"][1]) - off for s in segs]
    else:
        t, ends = 0.0, []
        for s in segs:
            t += float(s["end"]) - float(s["start"])
            ends.append(t)
    return ends[:-1]


def job_expectations(job, variant=None):
    """(times, plan, source): every expected hard-cut time (seconds, plan clock) for this job's export."""
    job = Path(job)
    plan = _load_json(job / "graphics-plan.json", "graphics-plan.json")
    if plan.get("fps") is None or plan.get("duration") is None:
        raise InputError(f"{job / 'graphics-plan.json'}: needs `fps` and `duration`")
    layout = None
    if variant:
        if not (plan.get("variants") or {}).get(variant):
            raise InputError(f"graphics-plan.json has no `variants.{variant}`")
        layout = _layout_module()
        try:
            plan = layout.compose_variant(plan, variant)
        except Exception as e:  # layout.MissingInput: the variant lacks `from` or `layout`
            raise InputError(f"layout.py cannot compose `variants.{variant}` ({e})")
    cp = job / "transcript" / (f"cuts.{variant}.json" if variant else "cuts.json")
    if variant and not cp.is_file():
        cp = job / "transcript" / "cuts.json"
    cuts = _load_json(cp, cp.name)
    if plan.get("layout"):
        layout = layout or _layout_module()
        try:
            times = list(layout.breaks(plan, cuts))
        except Exception as e:  # layout.LayoutError / MissingInput: the layout array itself is broken
            raise InputError(f"layout.py cannot resolve the plan's `layout` ({e}); run layout.py on the job first")
        source = f"{cp.name} V1 cuts, layout edges, graphic cell edges and shot_cuts (layout.py)"
    else:
        times = list(_v1_cuts(cuts, plan))
        for c in plan.get("beats") or plan.get("cells") or []:
            if not c.get("graphic") or c.get("kind") == "captions" or c.get("id") == "captions":
                continue
            times += [float(c.get("start", 0)), float(c.get("end", 0))]
            times += [float(t) for t in c.get("shot_cuts") or []]
        source = f"{cp.name} V1 cuts, graphic cell edges and shot_cuts"
    return sorted(set(round(float(t), 6) for t in times)), plan, source


def parse_times(text):
    try:
        return sorted(float(x) for x in re.split(r"[,\s]+", text.strip()) if x)
    except ValueError:
        raise InputError(f"--expect-times: not a list of seconds: {text!r}")


# ── report ──────────────────────────────────────────────────────────────────────────────────────────────────────────
def timecode(f, fps):
    """HH:MM:SS:FF, non-drop, counted at the nominal rate (how the editor shows 23.976 as 24)."""
    nom = max(1, int(round(fps)))
    s, ff = divmod(int(f), nom)
    return f"{s // 3600:02d}:{s // 60 % 60:02d}:{s % 60:02d}:{ff:02d}"


def where(f, fps):
    return f"f{f:<6d}{timecode(f, fps)}  {f / fps:8.3f} s"


def nearest(f, exp_frames):
    if not exp_frames:
        return None
    return min(exp_frames, key=lambda e: abs(e - f))


def run(video, expect=None, expect_times=None, variant=None, json_out=None, out=print):
    w, h, fps = probe(video)
    tw, th = thumb_size(w, h)
    D, M = measure(video, tw, th)
    n = len(D)
    warnings = []

    exp_times, source = None, None
    if expect:
        exp_times, plan, source = job_expectations(expect, variant)
        pf = _fps(plan["fps"])
        if abs(pf - fps) > 0.01:
            warnings.append(f"the plan runs at {pf:.3f} fps and the file at {fps:.3f}: the boundaries are placed on the file's grid")
        want = int(round(float(plan["duration"]) * pf))
        if abs(want - n) > 1:
            warnings.append(f"the file has {n} frames and the plan{' (' + variant + ')' if variant else ''} {want}: "
                            f"the wrong deliverable, or a partial export")
    elif expect_times is not None:
        exp_times, source = expect_times, "--expect-times"
    exp_frames = sorted({int(round(t * fps)) for t in exp_times}) if exp_times is not None else None
    found = scan(D, M, exp_frames or ())

    def at_expected(f):
        e = nearest(f, exp_frames)
        return e is not None and abs(e - f) <= TOLERANCE

    unexpected = []
    for c in found["cuts"]:
        if exp_frames is not None:
            c["expected"] = at_expected(c["frame"])
            e = nearest(c["frame"], exp_frames)
            c["nearest_expected"] = None if e is None else round(e / fps, 3)
            if not c["expected"]:
                unexpected.append(c)
    for e in found["doubles"] + found["flashes"]:
        e["t"] = round(e["frames"][0] / fps, 3)
        e["timecode"] = timecode(e["frames"][0], fps)
        if exp_frames is not None:
            ch = e.get("changes") or [e["frames"][0], e["frames"][-1] + 1]
            e["expected_boundary_near"] = [round(x / fps, 3) for x in exp_frames
                                           if ch[0] - TOLERANCE <= x <= ch[-1] + TOLERANCE]
    for c in found["cuts"]:
        c["t"] = round(c["frame"] / fps, 3)
        c["timecode"] = timecode(c["frame"], fps)

    fail = bool(found["flashes"] or found["doubles"])
    out(f"flash-scan: {video}")
    out(f"  {n} frames @ {fps:.3f} fps · {w}x{h} · read as {tw}x{th} grey")
    if exp_frames is not None:
        out(f"  expected boundaries: {len(exp_frames)} ({source}), each within {TOLERANCE} frame")
    for m in warnings:
        out(f"  ⚠ {m}")
    for e in found["flashes"]:
        fr = e["frames"]
        out(f"  ✗ FLASH       {where(fr[0], fps)}  differs from both neighbours ({e['into']} in, {e['out']} out) while "
            f"they match each other ({e['neighbours']}): {'a stray frame' if len(fr) == 1 else f'{len(fr)} stray frames'}")
    for e in found["doubles"]:
        fr, ch = e["frames"], e["changes"]
        two = ch[-1] - ch[0] == 2 and len(ch) == 2
        if two:
            shots, apart = f"frames {fr[0]}-{fr[-1]} are a two-frame shot", "two frames apart"
        else:
            shots = f"frame {fr[0]} is a one-frame shot" if len(fr) == 1 else f"frames {fr[0]}-{fr[-1]} are one-frame shots"
            apart = "on consecutive frames"
        near = e.get("expected_boundary_near")
        hint = ""
        if near and len(near) > 1:
            gap = round((near[-1] - near[0]) * fps)
            hint = (f"; planned boundaries {', '.join(f'{t:.3f} s' for t in near)}, {gap} frame{'s' if gap != 1 else ''} "
                    f"apart: two boundaries this close are the defect, land them on one frame")
        elif near:
            hint = f"; planned boundary {near[0]:.3f} s: one layer landed {'two frames' if two else 'a frame'} off the others"
        elif exp_frames is not None:
            hint = "; no planned boundary here"
        out(f"  ✗ DOUBLE CUT  {where(fr[0], fps)}  changes {' / '.join(str(x) for x in e['diffs'])} {apart}: "
            f"{shots}{hint}")
    for c in unexpected:
        off = "" if c["nearest_expected"] is None else \
            f"; nearest boundary {c['nearest_expected']:.3f} s, {abs(round(c['nearest_expected'] * fps) - c['frame'])} frames off"
        out(f"  ⚠ UNEXPECTED  {where(c['frame'], fps)}  hard cut ({c['diff']}) at no expected boundary{off}")
    if exp_frames is None:
        out(f"  hard cuts: {len(found['cuts'])} (no expected boundaries given: pass --expect projects/<job> to check them)")
        for c in found["cuts"]:
            out(f"    {where(c['frame'], fps)}  {c['diff']}")
    else:
        out(f"  hard cuts: {len(found['cuts'])} · {len(found['cuts']) - len(unexpected)} at an expected boundary · "
            f"{len(unexpected)} unexpected")
    verdict = "FAIL" if fail else "PASS"
    out(f"{verdict}: {len(found['flashes'])} flash{'es' if len(found['flashes']) != 1 else ''}, "
        f"{len(found['doubles'])} double cut{'s' if len(found['doubles']) != 1 else ''} · "
        f"{len(unexpected)} unexpected cut{'s' if len(unexpected) != 1 else ''} (warnings)")

    result = dict(video=str(video), frames=n, fps=fps, size=[w, h], thumb=[tw, th], verdict=verdict,
                  expected=None if exp_frames is None else dict(source=source, count=len(exp_frames),
                                                                 times=[round(t, 6) for t in exp_times]),
                  flashes=found["flashes"], double_cuts=found["doubles"], cuts=found["cuts"],
                  unexpected=[c["frame"] for c in unexpected], warnings=warnings,
                  thresholds=dict(FLASH_MIN=FLASH_MIN, MATCH=MATCH, HARD=HARD, CUT=CUT, SETTLE=SETTLE, HOLD=HOLD,
                                  SPIKE=SPIKE, LOCAL=LOCAL, WINDOW=WINDOW, MAX_RUN=MAX_RUN, TOLERANCE=TOLERANCE))
    if json_out:
        Path(json_out).write_text(json.dumps(result, indent=1), encoding="utf-8")
    return result


def main(argv=None):
    ap = argparse.ArgumentParser(description="Whole-program gate: single-frame flashes, double cuts, unexpected hard cuts.")
    ap.add_argument("video")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--expect", metavar="JOB", help="projects/<job>: the plan's boundaries are the expected cuts")
    g.add_argument("--expect-times", metavar="T,...", help="expected cut times in seconds, comma- or space-separated")
    ap.add_argument("--variant", help="with --expect: the plan's variants.<name> (e.g. ad), composed by layout.py")
    ap.add_argument("--json", dest="json_out", metavar="OUT", help="write every cut and finding here")
    a = ap.parse_args(argv)
    if a.variant and not a.expect:
        ap.error("--variant needs --expect")
    try:
        if not Path(a.video).is_file():
            raise InputError(f"no file at {a.video}")
        times = parse_times(a.expect_times) if a.expect_times is not None else None
        r = run(a.video, a.expect, times, a.variant, a.json_out)
    except InputError as e:
        print(f"flash-scan: {e}", file=sys.stderr)
        return 2
    return 1 if r["verdict"] == "FAIL" else 0


if __name__ == "__main__":
    sys.exit(main())
