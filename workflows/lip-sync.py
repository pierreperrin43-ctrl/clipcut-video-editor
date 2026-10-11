#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy"]
# ///
"""lip-sync.py: measure how far a camera stream runs from the voice it is cut against, and whether the offset DRIFTS.

  uv run workflows/lip-sync.py <cam.mp4> --audio <mic-source.mp4>                      # 9 windows across the take
  uv run workflows/lip-sync.py <cam.mp4> --audio <mic.mp4> --mouth-crop iw*0.14:ih*0.16:iw*0.44:ih*0.53
  uv run workflows/lip-sync.py <cam.mp4> --audio <mic.mp4> --windows 5 --window-len 90 --json

  --fps N           the grid the answer is reported on (default: the cam's own rate)
  --mouth-crop C    ffmpeg crop (w:h:x:y) around the mouth; default is the centre column's lower band
  --windows N       probe points spread across the take (default 9), each slid onto the talkiest window in its slot
  --window-len S    seconds correlated per window (default 120; a long window is what makes sub-frame drift readable)
  --max-lag N       frames searched either way (default 12)
  --min-speech F    fraction of a window that must carry voice for it to be probed (default 0.35)
  --min-peak S      drop a window whose peak stands less than S sigma above its own curve (default 0: report only)
  --json            the table, the fit and the verdict as JSON

Positive lag = the PICTURE is late against the voice by that many frames, so the camera clip's source in-point
moves LATER by the lag to line up.

Exit 0 = PASS, in sync within a frame across the take. Exit 1 = FAIL, with the per-clip slip to apply. Exit 2 =
UNMEASURED: the windows disagree, so there is no answer to act on (almost always the mouth crop — see below).

Why this exists (2026-09-19): a screen recorder's facecam is not lip-synced to its own mic, and the error
is not constant — that take ran +1.9 frames at the start and +8.3 by the end, a slow stretch of about 2 frames per
1000 s. It is invisible while the facecam is a corner bubble and unmissable the moment the angle is cut full frame,
which is when the creator caught it on playback. Measuring it is two envelopes: the mouth region's frame-to-frame
motion, and the voice's energy change. Both spike on a plosive, so their cross-correlation peak IS the offset; the
peak is fitted parabolically for sub-frame resolution and the per-window lags are fitted linearly (weighted by peak
strength) to expose the drift a single probe would hide.

THE WINDOWS HAVE TO LAND ON SPEECH. A probe point dropped on a silent stretch — a pause, a demo playing, a long
read — still returns a peak, just one correlated out of room tone and idle face motion: a weak window like that
sits at the wrong lag and, because it is only DOWN-weighted rather than excluded, it tilts the whole drift line.
So the evenly-spread probe points are slid onto the talkiest window inside their own slot, measured off a coarse
voice envelope of the take, and a slot with no speech in it is skipped and named rather than measured. Ties go to
the even spacing: on a take that talks throughout, sliding every window to the first-best candidate bunches the
probes into a corner of the take, and the drift line is only as good as its lever arm.

VOICE IN THE MIC IS NOT PROOF THE SPEAKER IS ON CAMERA, though — a clip playing on screen, an off-camera line, a
stretch of listening all fill a window with speech energy while the mouth does something else. Each window
therefore also reports how far its correlation peak stands above the rest of its own curve, in sigma, and that
number is what weights the drift fit (measured against a hand-built reference fit, it tracked it twice as closely
as weighting by the correlation itself). It is NOT a gate by default: on the take it was calibrated against, an
accurate window and one seven frames out both read 1.4 sigma, so a threshold would have thrown away good windows
to catch a bad one. --min-peak turns it into a gate for a take whose own table shows a clean split.

The rule this enforces: rough-cut § Gotchas — a facecam laid as its own angle is lip-sync-measured first, and each
clip's in-point slips by the lag AT ITS OWN SOURCE TIME, not by one number for the whole take.
"""
import argparse, json, subprocess, sys

for _s in (sys.stdout, sys.stderr):  # Windows pipes default to cp1252, which cannot encode the status glyphs
    try:
        if (getattr(_s, "encoding", "") or "").lower().replace("-", "") != "utf8":
            _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

import numpy as np

# The mouth sits in the centre column, below the midline, on any sane face framing — wide enough to survive a
# reframe, tight enough to keep a moving hand or a busy background out of the motion envelope.
DEFAULT_CROP = 'iw*0.34:ih*0.30:iw*0.33:ih*0.45'


def probe(path):
    out = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                          'stream=r_frame_rate:format=duration', '-of', 'default=nw=1:nk=1', str(path)],
                         capture_output=True, text=True).stdout.split()
    rate = out[0].rstrip(',') if out else '0/1'
    num, _, den = rate.partition('/')
    try:                                   # a container without a format duration answers N/A, not a number
        dur = float(out[-1]) if len(out) > 1 else 0.0
    except ValueError:
        dur = 0.0
    return (float(num) / float(den or 1) if float(num) else 0.0), dur


def mouth(cam, t0, dur, crop, fps):
    """Frame-to-frame motion of the mouth region, one sample per frame."""
    raw = subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-ss', str(t0), '-t', str(dur), '-i', str(cam),
                          '-vf', f'crop={crop},scale=64:40,format=gray', '-r', str(fps),
                          '-f', 'rawvideo', '-'], capture_output=True).stdout
    f = np.frombuffer(raw, np.uint8).reshape(-1, 40, 64).astype(float)
    if len(f) < 2:
        sys.exit(f'✗ no video decoded from {cam} at {t0}s')
    return np.abs(np.diff(f, axis=0)).mean(axis=(1, 2))


def voice(audio, t0, dur, fps):
    """Change in voice energy, on the SAME grid as the mouth envelope (1000 samples per frame)."""
    rate = int(round(1000 * fps))
    raw = subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-ss', str(t0), '-t', str(dur), '-i', str(audio),
                          '-vn', '-ac', '1', '-ar', str(rate), '-f', 's16le', '-'], capture_output=True).stdout
    a = np.frombuffer(raw, np.int16).astype(float)
    n = len(a) // 1000
    if n < 2:
        sys.exit(f'✗ no audio decoded from {audio} at {t0}s')
    e = np.sqrt((a[:n * 1000].reshape(n, 1000) ** 2).mean(1))
    return np.abs(np.diff(e))


def envelope(audio, dur, hop=1.0):
    """One RMS per `hop` seconds across the whole take: the coarse map of where the voice is."""
    raw = subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-t', str(dur), '-i', str(audio),
                          '-vn', '-ac', '1', '-ar', '1000', '-f', 's16le', '-'], capture_output=True).stdout
    a = np.frombuffer(raw, np.int16).astype(float)
    step = int(1000 * hop)
    n = len(a) // step
    if n < 2:
        return None
    return np.sqrt((a[:n * step].reshape(n, step) ** 2).mean(1))


def place_windows(env, hop, span, length, n, floor):
    """-> [(start, speech fraction)] — the evenly-spread probe points, each slid onto the talkiest
    window inside its own slot, and a slot with no speech in it dropped.

    Loud is measured against the take's own 90th percentile, so a quiet shoot is not all silence and
    a hot one is not all speech; `floor` is how much of a window has to be above that.
    """
    if n < 2:
        return [(span / 2, 1.0)]
    even = [span * k / (n - 1) for k in range(n)]
    if env is None:
        return [(t, 1.0) for t in even]
    # 20 dB under the take's own loud level is not voice — relative, so a quiet shoot is not all silence and
    # a hot one is not all speech — but with an absolute floor under it, or a dead track reads as 100% speech
    # (its own percentile is room tone, and everything clears a tenth of that).
    active = env > max(0.1 * float(np.percentile(env, 90)), 0.001 * 32768)
    def speech(t):
        lo = int(round(t / hop))
        return float(active[lo:lo + max(1, int(round(length / hop)))].mean())
    reach = span / (2 * (n - 1))
    out = []
    for t in even:
        cands = [min(max(t + d * hop, 0.0), span)
                 for d in range(-int(reach / hop), int(reach / hop) + 1)]
        # Ties go to the evenly-spread point: on a take that talks throughout, every candidate scores 1.0
        # and a plain max() slides every window to the near edge of its slot, bunching the probes.
        best = max(cands, key=lambda c: (speech(c), -abs(c - t)))
        if speech(best) >= floor:
            out.append((best, speech(best)))
        else:
            print(f'  slot at {t + length / 2:8.1f}s: {speech(best) * 100:.0f}% speech at best, under the {floor:.0%} '
                  f'floor — skipped (nothing to correlate there)')
    return out


def lag_at(cam, audio, t0, length, crop, fps, max_lag):
    """-> (lag in frames, correlation at the peak, how far that peak stands above the rest of the curve).

    The third number is the one to trust of the two. The correlation itself is small even on a good window
    (two coarse envelopes, not two copies of a signal) and its size says little: the window that disagreed
    most with the others, on the take this was calibrated against, carried the HIGHEST correlation of the
    nine. How far the peak stands above its own curve at least measures whether one lag beat the rest.
    """
    m, v = mouth(cam, t0, length, crop, fps), voice(audio, t0, length, fps)
    n = min(len(m), len(v))
    m, v = m[:n], v[:n]
    if m.std() < 1e-9 or v.std() < 1e-9:
        return None, 0.0, 0.0                             # a still frame or silence: nothing to correlate
    m = (m - m.mean()) / m.std(); v = (v - v.mean()) / v.std()
    L = np.arange(-max_lag, max_lag + 1)
    sc = np.array([np.dot(v[max(0, -l):n - max(0, l)], m[max(0, l):n - max(0, -l)]) / (n - abs(l)) for l in L])
    i = int(sc.argmax())
    z = float((sc[i] - sc.mean()) / (sc.std() or 1.0))
    if i in (0, len(L) - 1):
        return None, float(sc[i]), z   # pinned at the edge of the search: not a peak, widen --max-lag
    d = 0.0
    if (sc[i - 1] - 2 * sc[i] + sc[i + 1]) != 0:
        d = 0.5 * (sc[i - 1] - sc[i + 1]) / (sc[i - 1] - 2 * sc[i] + sc[i + 1])   # parabolic peak: sub-frame
    return float(L[i] + d), float(sc[i]), z


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('cam'); ap.add_argument('--audio', required=True)
    ap.add_argument('--fps', type=float); ap.add_argument('--mouth-crop', default=DEFAULT_CROP)
    ap.add_argument('--windows', type=int, default=9); ap.add_argument('--window-len', type=float, default=120.0)
    ap.add_argument('--max-lag', type=int, default=12); ap.add_argument('--min-speech', type=float, default=0.35)
    ap.add_argument('--min-peak', type=float, default=0.0); ap.add_argument('--json', action='store_true')
    a = ap.parse_args()
    cam_fps, cam_dur = probe(a.cam)
    _, aud_dur = probe(a.audio)
    fps = a.fps or cam_fps
    if not fps:
        sys.exit(f'✗ cannot read a frame rate from {a.cam}; pass --fps')
    dur = min(cam_dur, aud_dur) if aud_dur else cam_dur
    if dur <= 0:
        sys.exit(f'✗ ffprobe reports no duration for {a.cam}: every window would start at 0 and the drift fit '
                 f'would be meaningless. Remux the take, or measure a trimmed copy.')
    length = min(a.window_len, max(10.0, dur / 4))
    span = max(0.0, dur - length)
    print(f'{a.cam} vs {a.audio}  ·  {dur:.0f}s @ {fps:.3f} fps  ·  {a.windows} windows of {length:.0f}s'
          f'  ·  mouth crop {a.mouth_crop}')
    env = envelope(a.audio, dur)
    if env is None:
        print(f'⚠ no voice envelope decoded from {a.audio}: probing evenly, so a window may land on silence')
    starts = place_windows(env, 1.0, span, length, a.windows, a.min_speech)
    pts, weak_peaks = [], 0
    for t0, sp in starts:
        lag, r, z = lag_at(a.cam, a.audio, t0, length, a.mouth_crop, fps, a.max_lag)
        centre = t0 + length / 2
        if lag is None:
            print(f'  src {centre:8.1f}s: no peak inside ±{a.max_lag} frames (r={r:.3f}) — skipped')
            continue
        line = (f'  src {centre:8.1f}s: lag {lag:+6.2f} fr ({lag / fps * 1000:+5.0f} ms)  r={r:.3f}  peak {z:4.1f}σ'
                f'  speech {sp:.0%}')
        if z < a.min_peak:                    # opt-in, and only when the take's own table splits cleanly
            print(line + f' — DROPPED, peak under the {a.min_peak:.1f}σ asked for')
            weak_peaks += 1
            continue
        print(line)
        pts.append((centre, lag, z))
    if len(pts) < 2:
        sys.exit(f'✗ fewer than two usable windows ({weak_peaks} dropped on --min-peak): widen --window-len, point '
                 f'--mouth-crop at the mouth (it is printed above), or lower --min-peak and read the table by hand')
    t, l, w = (np.array(x) for x in zip(*pts))
    slope, base = np.polyfit(t, l, 1, w=w)                # weighted by peak strength: a soft peak steers less
    ends = [base, base + slope * dur]
    rms = float(np.sqrt((((base + slope * t) - l) ** 2).mean()))
    worst = max(abs(x) for x in list(l) + ends)
    # A WEAK MEASUREMENT GETS NO VERDICT. Every window returns a peak, so a crop that is not on the mouth
    # still produces a confident-looking line — and a FAIL hands back a slip formula that would move every
    # clip by a number nothing corroborates. Windows that disagree with their own fit, or a take where most
    # of them had no peak at all, are reported as unmeasured rather than answered.
    weak = rms > 1.0 or len(pts) < max(2, len(starts) // 2)
    ok = worst < 1.0 and not weak
    print(f'fit: lag_frames = {base:+.3f} + {slope * 1000:.4f} per 1000 s   '
          f'(0 s: {ends[0]:+.2f} fr · {dur:.0f} s: {ends[1]:+.2f} fr)   residual {rms:.2f} fr rms')
    if weak:
        print(f'⚠ UNMEASURED: {len(pts)} of {len(starts)} windows measured and they do not agree (residual {rms:.2f} fr), '
              f'so the line above is not an answer and nothing should be slipped by it.')
        print(f'  Point --mouth-crop at the mouth — the default {DEFAULT_CROP} is a generic centre band, and on a wide '
              f'framing it correlates head and background motion instead — then raise --window-len and re-run.')
    elif ok:
        print(f'✓ PASS: within {worst:.2f} frames across the take — lay the angle as cut')
    else:
        print(f'✗ FAIL: off by up to {worst:.2f} frames, drifting {abs(ends[1] - ends[0]):.2f} fr across the take.')
        print(f'  Slip each camera clip LATER in its source by its own lag: lag_frames = {base:+.4f} '
              f'+ {slope:.8f} * src_seconds  (timeline start/end unchanged), then prove it on a timeline export.')
    if a.json:
        print(json.dumps(dict(cam=a.cam, audio=a.audio, fps=fps, duration=dur, crop=a.mouth_crop,
                              windows=[dict(centre=round(c, 3), lag_frames=round(x, 3), peak_sigma=round(zz, 2))
                                       for c, x, zz in pts],
                              fit=dict(base_frames=round(float(base), 4), frames_per_second=round(float(slope), 8),
                                       at_start=round(float(ends[0]), 3), at_end=round(float(ends[1]), 3),
                                       residual_frames=round(rms, 3)),
                              verdict='UNMEASURED' if weak else 'PASS' if ok else 'FAIL'), indent=1))
    return 2 if weak else 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
