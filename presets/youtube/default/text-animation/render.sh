#!/usr/bin/env bash
# render the text animations -> renders/<id>-alpha.mov (ProRes 4444, STRAIGHT alpha)
# usage: render.sh [id ...]          (no args = every entry in text.json)
#        VER=b render.sh p1          (-> renders/p1-alpha-b.mov)
#        FPS=30000/1001 render.sh    (default; set to the TIMELINE's exact rate)
#        JOB=<job_dir> render.sh     (override the job auto-derived from folder position)
#
# VER: NEVER re-render onto a path an editing app has already placed. Overwriting
# a placed file half-stales Premiere's frame index and random frames come back
# transparent. Version the filename and import it fresh.
#
# Alpha is STRAIGHT. A lane that composites premultiplied converts on its own
# side — LANES.md § step 5.
#
# Pin: 0.8.16 — the validated new-job pin (2026-08-27). Bump deliberately.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p renders

PY=python3; "$PY" -c '' 2>/dev/null || PY=python
export PYTHONUTF8=1 PYTHONIOENCODING=utf-8   # Windows pipes default to cp1252, which cannot encode the ⚠ status glyphs
FPS="${FPS:-30000/1001}"

if [ $# -gt 0 ]; then
  IDS="$*"
else
  IDS=$("$PY" build.py --ids)
fi

BUILD_ARGS=""
[ -n "${JOB:-}" ] && BUILD_ARGS="--job $JOB"
"$PY" build.py $BUILD_ARGS $IDS

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
  echo "          Re-render it as a new version instead: VER=<next unused letter> $0 ${_b%%-alpha*}" >&2
  exit 2
}

# MBLUR=1 -> TRUE motion blur: render at MBLUR_SS x the target rate, then average
# MBLUR_SHUTTER consecutive frames and decimate back. Averaging must happen on
# PREMULTIPLIED pixels (straight alpha averages wrong at soft edges), so the chain
# premultiplies, mixes, then unpremultiplies back to the straight alpha Premiere
# and Resolve expect. SS 5 / shutter 3 ~= a 216-degree shutter.
#
# STEP_FPS=12 -> "12 fps style": ANIMATE at 12 fps and hold each frame, then expand
# back to the timeline rate by frame duplication (the on-2s / stop-motion look).
# NEVER with MBLUR: the 12 fps look steps, it does not blur (creative-moves.md 4c).
SS="${MBLUR_SS:-5}"; SHUT="${MBLUR_SHUTTER:-3}"
FPS_NUM="${FPS%%/*}"; FPS_DEN="${FPS##*/}"
[ "$FPS_NUM" = "$FPS_DEN" ] && FPS_DEN=1
if [ -n "${STEP_FPS:-}" ]; then
  ANIM_NUM="$STEP_FPS"; ANIM_DEN=1
  EXPAND=",fps=$FPS"
else
  ANIM_NUM="$FPS_NUM"; ANIM_DEN="$FPS_DEN"
  EXPAND=""
fi
ANIM_FPS="$ANIM_NUM/$ANIM_DEN"
SS_FPS="$((ANIM_NUM * SS))/$ANIM_DEN"
WEIGHTS=""; _i=0
while [ "$_i" -lt "$SHUT" ]; do WEIGHTS="$WEIGHTS 1"; _i=$((_i + 1)); done
WEIGHTS="${WEIGHTS# }"   # NOT `yes 1 | head` — SIGPIPE + pipefail kills the script
# tmix emits at every input index with a TRAILING window: out[j] = mean(j-SHUT+1..j).
# So the shutter centred on output frame m is j = m*SS + (SHUT-1)/2. The supersampled
# stream ends mid-group (both rates ceil() independently), so clone-pad the tail by SS
# or the last output frame is silently dropped. Verified against a no-blur render:
# same frame count, same onset.
PHASE=$(( (SHUT - 1) / 2 ))
# The tail pad guarantees the last group exists. The supersampled and base renders
# round their frame counts independently, so derive the cap as ceil(ss_frames / SS):
# it can run ONE frame long but never short. Long is harmless (placement pins the
# out point); short would leave a one-frame gap at the graphic's tail.
mb_frames() { # $1 = supersampled file -> exact target frame count
  _L=$(ffprobe -v error -select_streams v:0 -count_frames \
       -show_entries stream=nb_read_frames -of csv=p=0 "$1")
  echo $(( (_L + SS - 1) / SS ))
}

for ID in $IDS; do
  OUT="renders/$ID-alpha$SUF.mov"
  placed_guard "$OUT"
  if [ -n "${MBLUR:-}" ]; then
    echo "==> $ID (alpha overlay, motion blur ${SS}x/${SHUT}f)"
    npx hyperframes@0.8.16 render . -c "compositions/$ID.html" --fps "$SS_FPS" --quality standard \
      --video-frame-format png --format mov --output "renders/$ID-ss.mov"
    NB=$(mb_frames "renders/$ID-ss.mov")
    [ -z "${STEP_FPS:-}" ] || NB=""   # `&& NB=` would exit under set -e
    ffmpeg -y -v error -i "renders/$ID-ss.mov" ${NB:+-frames:v "$NB"} -vf \
      "format=rgba64le,premultiply=inplace=1,tmix=frames=$SHUT:weights=$WEIGHTS,tpad=stop=$SS:stop_mode=clone,select='eq(mod(n\,$SS)\,$PHASE)',unpremultiply=inplace=1,setpts=N/($ANIM_NUM/$ANIM_DEN)/TB$EXPAND,format=yuva444p12le" \
      -c:v prores_ks -profile:v 4444 -r "$FPS" "$OUT"
    rm "renders/$ID-ss.mov"
    echo "-> $OUT (motion blur baked)"
  else
    echo "==> $ID (alpha overlay)"
    npx hyperframes@0.8.16 render . -c "compositions/$ID.html" --fps "$ANIM_FPS" --quality standard \
      --video-frame-format png --format mov --output "$OUT"
  fi
done
