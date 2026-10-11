#!/usr/bin/env python3
"""assemble.py: the chat-only lane's composite (LANES.md steps 5' and 5): the base cut, its footage laid out per the
plan's layout map, every placed graphic over it, the caption layer last. One ffmpeg pass; the base is never
re-rendered by graphics and its audio rides through untouched.

  uv run lanes/chat-only/assemble.py projects/<job>               -> hf-graphics/renders/final.mp4
  uv run lanes/chat-only/assemble.py projects/<job> --out <mp4>

Reads outputs/<job>.mp4 (the base cut), hf-graphics/placement.json (the placed rows: id, kind, start, end, file) and,
on a layout-rotation preset (the Talking Head Explainer), graphics-plan.json `layout` + face-frame.json `modes`
through the preset's layout.py: the base is cut at the layout edges and each span gets its footage transform (a row's
own `frame` over its mode's; S slides the frame, T punches in about the face, W is untouched; F and O keep W's
footage under their graphic; hard cuts, no ramps: layout.md § 2). A plan without `layout` keeps the footage as it is.

The mechanics below were each forced by a flash-scan FAIL on the Windows test job (2026-09-27) and stay exactly so:
  · layout edges cut FRAME-exact (trim=start_frame/end_frame): a float-second trim (14.8148 = frame 443.998) rounded
    a frame early, and every layout switch landed a frame before its graphic;
  · each overlay is placed FRAME-exact with setpts=(N+f0)/fps: a float -itsoffset ran it a frame early;
  · each overlay carries a one-frame tpad: with eof_action=pass ffmpeg never shows an overlay's LAST frame;
  · each overlay's enable window sits half a frame inside the frame grid: between(t, start, end) on float seconds
    missed the first frame whenever t and start differed in the last digit.
The caption layer goes on last. Built by captions.py --straight-alpha (hf-graphics/captions/renders/
captions-alpha-sa*.mov) it composites as approved: ffmpeg's overlay blends straight alpha in gamma space
(incremental-graphics.md). The stutter guardrail runs after every composite: 8 % or more frames identical to the
previous (signalstats YDIF == 0) exits 1.
"""
import argparse
import importlib.util
import json
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

for _s in (sys.stdout, sys.stderr):  # Windows pipes default to cp1252, which cannot encode the status glyphs
    try:
        if (getattr(_s, "encoding", "") or "").lower().replace("-", "") != "utf8":
            _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

REPO = Path(__file__).resolve().parents[2]
LAYOUT = REPO / "presets" / "instagram" / "talking-head-explainer" / "layout.py"
DUP_LIMIT = 0.08


def probe(path):
    d = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                   "stream=width,height,r_frame_rate", "-of", "json", str(path)],
                                  capture_output=True, text=True, check=True).stdout)["streams"][0]
    return int(d["width"]), int(d["height"]), d["r_frame_rate"]


def layout_module():
    spec = importlib.util.spec_from_file_location("thx_layout", LAYOUT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def footage_chain(job, plan, W, H, fps, FPS):
    """(filter pieces, label) laying the base's footage out per the layout map; None when the plan has no layout."""
    if not plan.get("layout"):
        return None
    L = layout_module()
    md = L.modes(json.loads((job / "face-frame.json").read_text(encoding="utf-8")))
    fc, labels = [], []
    for k, (a, b, _key, m) in enumerate(L.footage_spans(plan, md)):
        s, (cx, cy) = float(m["scale"]), m["centre"]
        sw, sh = round(W * s / 2) * 2, round(H * s / 2) * 2
        x, y = round(cx * W - sw / 2), round(cy * H - sh / 2)
        f0, f1 = round(a * FPS), round(b * FPS)
        fc.append(f"[0:v]trim=start_frame={f0}:end_frame={f1},setpts=PTS-STARTPTS,scale={sw}:{sh}:flags=lanczos[s{k}];"
                  f"color=c=black:s={W}x{H}:r={fps}[bg{k}];[bg{k}][s{k}]overlay=x={x}:y={y}:shortest=1,setsar=1[v{k}]")
        labels.append(f"[v{k}]")
    fc.append("".join(labels) + f"concat=n={len(labels)}:v=1:a=0[foot]")
    return fc, "foot"


def overlay_rows(job):
    """The placed overlays, the caption layer last (its straight-alpha build when one exists)."""
    pl = json.loads((job / "hf-graphics" / "placement.json").read_text(encoding="utf-8"))
    rows = pl["rows"] if isinstance(pl, dict) else pl
    orphans = [f"{r.get('id', '?')} at {float(r.get('start') or 0):.3f}s" for r in rows if r.get("ripple") == "orphaned"]
    if orphans:                     # a re-cut deleted their anchor (ripple-cut.py): laid, they sit at pre-recut times
        sys.exit(f"✗ placement row(s) orphaned by a re-cut: {', '.join(orphans)}. Re-anchor or delete each row, re-run "
                 "workflows/placement.py --write, then assemble (every placer refuses them, never lays them)")
    out, caps = [], []
    for r in rows:
        f = Path(r["file"])
        f = f if f.is_absolute() else job / f
        if not f.exists():
            sys.exit(f"✗ {r.get('id')}: {f} is not rendered")
        (caps if r.get("kind") == "captions" else out).append({**r, "file": str(f)})
    for c in caps:
        sa = sorted((job / "hf-graphics" / "captions" / "renders").glob("captions-alpha-sa*.mov"),
                    key=lambda p: p.stat().st_mtime)
        if sa:
            c["file"] = str(sa[-1])
        else:
            print(f"⚠ no straight-alpha caption build: {Path(c['file']).name} composites heavier than approved over "
                  "ffmpeg's gamma-space blend; build it with captions.py projects/<job> --straight-alpha",
                  file=sys.stderr)
    return out + caps


def dup_share(path):
    r = subprocess.run(["ffmpeg", "-v", "info", "-i", str(path), "-vf", "signalstats,metadata=print:key=lavfi.signalstats.YDIF",
                        "-f", "null", "-"], capture_output=True, text=True)
    ydif = [float(l.split("=")[1]) for l in (r.stderr + r.stdout).splitlines() if "YDIF=" in l]
    return len(ydif), sum(1 for v in ydif[1:] if v == 0.0) / max(1, len(ydif) - 1)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Composite a chat-only job: footage layout, overlays, captions.")
    ap.add_argument("job")
    ap.add_argument("--out", help="default: hf-graphics/renders/final.mp4")
    a = ap.parse_args(argv)
    job = Path(a.job).resolve()
    base = job / "outputs" / f"{job.name}.mp4"
    if not base.exists():
        sys.exit(f"✗ no base cut at {base}: splice it first (rough-cut, RENDER=1)")
    plan = json.loads((job / "graphics-plan.json").read_text(encoding="utf-8"))
    W, H, rate = probe(base)
    fps = str(plan.get("fps") or rate)
    FPS = float(Fraction(fps))
    out = Path(a.out) if a.out else job / "hf-graphics" / "renders" / "final.mp4"

    inputs, fc = ["-i", str(base)], []
    lay = footage_chain(job, plan, W, H, fps, FPS)
    if lay:
        fc += lay[0]
        last = lay[1]
    else:
        fc.append("[0:v]null[foot]")
        last = "foot"
    rows = overlay_rows(job)
    for i, r in enumerate(rows, start=1):
        inputs += ["-i", r["file"]]
        f0 = round(float(r["start"]) * FPS)
        h = 0.5 / FPS
        a_, b_ = f0 / FPS - h, round(float(r["end"]) * FPS) / FPS - h
        fc.append(f"[{i}:v]tpad=stop=1:stop_mode=clone,setpts=(N+{f0})/({fps})/TB[g{i}]")
        fc.append(f"[{last}][g{i}]overlay=eof_action=pass:enable='between(t,{a_:.6f},{b_:.6f})'[o{i}]")
        last = f"o{i}"
    fc.append(f"[{last}]format=yuv420p[vout]")
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", ";".join(fc), "-map", "[vout]",
                    "-map", "0:a", "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-r", fps, "-c:a", "copy",
                    "-movflags", "+faststart", str(out)], check=True)
    n, dups = dup_share(out)
    print(f"-> {out}  ({len(rows)} overlay(s){', layout keyed' if lay else ''}; {n} frames, "
          f"{100 * dups:.1f}% identical to the previous)")
    if dups >= DUP_LIMIT:
        sys.exit(f"✗ {100 * dups:.1f}% duplicated frames (the stutter trap, incremental-graphics.md): an overlay without "
                 "eof_action=pass, or a slow input")
    return 0


if __name__ == "__main__":
    sys.exit(main())
