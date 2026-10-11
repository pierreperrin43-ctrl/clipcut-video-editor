#!/usr/bin/env python3
"""mix-sfx.py: the chat-only lane's SFX pass (LANES.md § step 6). Every row of hf-graphics/sfx-plan.json (at, file,
src_in, src_out, level_db, fade_out_s) is cut to its slice, levelled, faded where the plan says, delayed to its
timeline second and summed onto the render's own dialogue, never normalised; the video is stream-copied.

  uv run lanes/chat-only/mix-sfx.py projects/<job> <in.mp4> <out.mp4>

Run it on the assemble render (lanes/chat-only/assemble.py), before the optional music bed (mix-music.sh). The AAC
re-encode is 320k, above the splice's 256k (downstream steps never degrade the voice). The plan's levels are the
preset's, and sfx-plan.py has already held every stack of cues to -1 dBTP on the mix.
"""
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def main(argv=None):
    a = sys.argv[1:] if argv is None else argv
    if len(a) != 3:
        sys.exit(__doc__)
    job, src, dst = Path(a[0]).resolve(), a[1], a[2]
    rows = json.loads((job / "hf-graphics" / "sfx-plan.json").read_text(encoding="utf-8"))
    rows = rows["rows"] if isinstance(rows, dict) else rows
    orphans = [str(r.get("id", "?")) for r in rows if r.get("ripple") == "orphaned"]
    if orphans:                     # a re-cut deleted their anchor (ripple-cut.py): mixed, they land at pre-recut times
        sys.exit(f"✗ sfx row(s) orphaned by a re-cut: {', '.join(orphans)}. Re-run workflows/sfx-plan.py, then mix")
    ins, fc, mix = ["-i", src], [], ["[0:a]"]
    for i, r in enumerate(rows, start=1):
        f = Path(r["file"])
        if not f.is_absolute():
            f = REPO / "assets" / "sfx" / r["file"]
        if not f.exists():
            hit = next((REPO / "assets" / "sfx").rglob(Path(r["file"]).name), None)
            if hit is None:
                sys.exit(f"✗ {r.get('id')}: no {Path(r['file']).name} in assets/sfx")
            f = hit
        s0, s1 = float(r["src_in"]), float(r["src_out"])
        fade = float(r.get("fade_out_s") or 0)
        ins += ["-i", str(f)]
        fc.append(f"[{i}:a]atrim={s0}:{s1},asetpts=PTS-STARTPTS,aformat=sample_rates=48000:channel_layouts=stereo,"
                  f"volume={float(r['level_db'])}dB"
                  + (f",afade=t=out:st={max(0.0, s1 - s0 - fade):.4f}:d={fade:.4f}" if fade else "")
                  + f",adelay={int(round(float(r['at']) * 1000))}:all=1[s{i}]")
        mix.append(f"[s{i}]")
    fc.append("".join(mix) + f"amix=inputs={len(mix)}:duration=first:normalize=0[a]")
    # -map_chapters 0: the render's own chapters, never a sound's. ffmpeg copies them from the first input that has
    # any, and the pack's "Pop 1.wav" carries two, which shipped as a chapter text track in the deliverable (2026-09-27)
    subprocess.run(["ffmpeg", "-y", "-v", "error", *ins, "-filter_complex", ";".join(fc), "-map", "0:v", "-map", "[a]",
                    "-map_chapters", "0", "-c:v", "copy", "-c:a", "aac", "-b:a", "320k", "-movflags", "+faststart", dst],
                   check=True)
    print(f"-> {dst}  ({len(rows)} sounds mixed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
