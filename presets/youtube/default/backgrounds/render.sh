#!/usr/bin/env bash
# render the standard full-screen background assets -> renders/<id>.mp4
# usage: render.sh [id ...]        (no args = bg-light bg-dark)
#        VER=b render.sh bg-light   (-> renders/bg-light-b.mp4 — NEVER re-render onto
#                                    a path an editing app has already placed)
#        FPS=30000/1001 render.sh  (default; match the timeline when it matters)
#        GRAIN=0 render.sh         (skip bg-light's film-grain pass)
#
# bg-light gets FILM GRAIN as an ffmpeg post-pass: luma-only temporal noise
# (chroma noise reads as color speckle on a light field, luma reads as film).
# Strength knob: GRAIN_STRENGTH (default 7). libx264 CRF 14 so the re-encode
# never becomes the quality ceiling. bg-dark ships clean.
#
# Pin: 0.8.16 — the validated new-job pin (2026-08-27). Bump deliberately.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p renders

FPS="${FPS:-30000/1001}"
IDS="${*:-bg-light bg-dark}"
GRAIN="${GRAIN:-1}"
GRAIN_STRENGTH="${GRAIN_STRENGTH:-7}"
SUF=""
[ -n "${VER:-}" ] && SUF="-$VER"

for ID in $IDS; do
  echo "==> $ID"
  npx hyperframes@0.8.16 render . -c "compositions/$ID.html" --fps "$FPS" --quality standard \
    --video-frame-format png --format mp4 --output "renders/$ID$SUF.mp4"

  if [ "$ID" = "bg-light" ] && [ "$GRAIN" = "1" ]; then
    echo "==> $ID (film grain)"
    ffmpeg -y -v error -i "renders/$ID$SUF.mp4" \
      -vf "noise=c0s=$GRAIN_STRENGTH:c0f=t" \
      -c:v libx264 -crf 14 -pix_fmt yuv420p -movflags +faststart "renders/$ID$SUF.grain.mp4"
    mv "renders/$ID$SUF.grain.mp4" "renders/$ID$SUF.mp4"
  fi
done
