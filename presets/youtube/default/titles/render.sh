#!/usr/bin/env bash
# render the section-title cards -> renders/<id>.mp4  (opaque card, grid bg baked in)
#                                -> renders/<id>-alpha.mov (ProRes 4444, type only)
# usage: render.sh [id ...]          (no args = every title in titles.json)
#        ALPHA_ONLY=1  render.sh t-setup   (skip the opaque card)
#        OPAQUE_ONLY=1 render.sh           (skip the alpha overlays — the V1
#                                           timeline only ever places the opaque card)
#        VER=b         render.sh           (-> renders/<id>-b.mp4)
#
# VER: NEVER re-render onto a path an editing app has already placed. Overwriting a
# placed file half-stales Premiere's frame index and random frames come back
# transparent. Version the filename and import it fresh.
#
# Alpha is STRAIGHT. A lane that composites premultiplied converts on its own side — see LANES.md § step 5.
#
# Pin: 0.8.16 — the validated new-job pin (2026-08-27, PNG-sequence A/B vs 0.7.92
# on this very builder: opaque pixel-identical 90/90, alpha 233 px of glyph AA total). Bump deliberately.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p renders

PY=python3; "$PY" -c '' 2>/dev/null || PY=python
export PYTHONUTF8=1 PYTHONIOENCODING=utf-8   # Windows pipes default to cp1252, which cannot encode the ⚠ status glyphs

# The timeline rate comes from the JOB (reference/fullscreen-render.sh's resolution, word for word): FPS, else the
# job's graphics-plan.json "fps", else the first raw's rate. A hardcoded --fps 30 gave a 29.97 or 23.976 job 30 fps
# cards the NLE had to conform (2026-09-27).
FPS_SRC="FPS"
if [ -z "${FPS:-}" ] && [ -f ../../graphics-plan.json ]; then
  FPS=$(node -e 'const p = JSON.parse(require("fs").readFileSync(process.argv[1], "utf8")); process.stdout.write(p.fps == null ? "" : String(p.fps))' ../../graphics-plan.json)
  FPS_SRC="graphics-plan.json"
fi
if [ -z "${FPS:-}" ]; then
  for _r in ../../raw/*; do
    [ -f "$_r" ] || continue
    _rf=$(ffprobe -v error -select_streams v:0 -show_entries stream=r_frame_rate -of csv=p=0 "$_r" 2>/dev/null | tr -d ',\r' || true)
    case "$_rf" in ''|0/0) continue ;; esac
    FPS="$_rf"; FPS_SRC="raw/${_r##*/}"; break
  done
fi
if [ -z "${FPS:-}" ]; then
  FPS="30000/1001"; FPS_SRC="default"
  echo "⚠️  no fps in ../../graphics-plan.json and no video in ../../raw/: rendering at $FPS. Pass FPS=<the timeline's rate> if that is wrong." >&2
fi
case "$FPS" in ''|/*|*/|*/*/*|*[!0-9/]*)
  echo "refusing: FPS=$FPS (from $FPS_SRC) is not a frame rate like 24000/1001, 30000/1001 or 25." >&2; exit 2 ;; esac
echo "fps $FPS (from $FPS_SRC)"

if [ $# -gt 0 ]; then
  IDS="$*"
else
  IDS=$("$PY" build.py --ids)
fi

"$PY" build.py --fps "$FPS" $IDS

SUF=""
[ -n "${VER:-}" ] && SUF="-$VER"

# THE VER RULE ABOVE, ENFORCED: refuse an output path the placer has already laid (a builder
# overwrote one anyway on 2026-09-19). The job's placement.json sits one level up; no file = nothing
# placed yet, so this is a no-op before the first `place-graphics.py --plan --write`.
placed_guard() {   # $1 = the file this run is about to write
  _pj="../placement.json"; [ -f "$_pj" ] || return 0
  _b="${1##*/}"
  grep -q "[/\\]$_b\"" "$_pj" || return 0
  echo "refusing: renders/$_b is PLACED on the timeline (../placement.json)." >&2
  echo "          Re-render it as a new version instead: VER=<next unused letter> $0 $ID" >&2
  exit 2
}

for ID in $IDS; do
  if [ "${ALPHA_ONLY:-0}" != "1" ]; then
    placed_guard "renders/$ID$SUF.mp4"
    echo "==> $ID (opaque card)"
    npx hyperframes@0.8.16 render . -c "compositions/$ID.html" --fps "$FPS" --quality standard \
      --video-frame-format png --format mp4 --output "renders/$ID$SUF.mp4"
  fi

  if [ "${OPAQUE_ONLY:-0}" = "1" ]; then
    continue
  fi

  placed_guard "renders/$ID-alpha$SUF.mov"
  echo "==> $ID (alpha overlay)"
  npx hyperframes@0.8.16 render . -c "compositions/$ID-alpha.html" --fps "$FPS" --quality standard \
    --video-frame-format png --format mov --output "renders/$ID-alpha$SUF.mov"
done
