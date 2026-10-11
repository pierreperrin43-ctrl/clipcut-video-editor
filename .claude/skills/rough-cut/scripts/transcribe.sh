#!/usr/bin/env bash
# transcribe.sh — runs WhisperX (large-v3 + wav2vec2 forced alignment) on every clip in a job folder
# usage: transcribe.sh <job_dir> [--diarize] [--force] [--chunk-size N] [--vad-onset X --vad-offset Y]
# output: <job_dir>/transcript/words.json  (durable canonical — transcribe ONCE, reuse forever;
#         /tmp/video-editor/<job-name>/ is just render scratch)
#
# standalone: transcribe.sh --file <audio|video> --out <words.json> [--diarize] [--chunk-size N] [--vad-...]
#   One file in (a pickup re-record, a spliced audio), the same words.json shape out at --out.
#   It never reads or writes a job's transcript/: no canonical, no reuse, always transcribes.
#
# --diarize adds speaker labels per word (requires HUGGINGFACE_TOKEN in env;
# pyannote/speaker-diarization-3.1 must be accepted on Hugging Face).
#
# A second voice on a phone speaker (about 10 dB under the host) goes missing from the text, and
# wav2vec2 then force-fits the host's next words over its window. Two knobs, both unset = WhisperX's
# own defaults, both apply only to a fresh transcription (a reuse of the canonical refuses them),
# and neither is a fix (measured on the three reference phone-call jobs, 2026-09-23): each moves WHERE Whisper
# drops the quiet voice, so `cut-audit.py --coverage` still gates and realign-spans.py still repairs.
#   --chunk-size N (env WHISPERX_CHUNK_SIZE; 1-30 s, default 30) caps how much VAD-merged speech
#     Whisper decodes as one window. Where the VAD FOUND the AI's lines and Whisper dropped them
#     inside a 30 s window shared with the louder host, 20 recovered them; on a whole 53-minute
#     call it dropped other AI lines the default had kept. Below 20 it invented words in room tone.
#   --vad-onset X --vad-offset Y (env VAD_ONSET / VAD_OFFSET) set the pyannote speech thresholds,
#     together, offset <= onset (defaults 0.500 / 0.363), for a voice the VAD itself scores low.
# The flags win over the env.

set -euo pipefail

# Windows pipes default python stdio to cp1252, which can't encode the ⚠/→ glyphs in the
# long-span warnings (or huggingface's progress output), so force UTF-8 everywhere.
# Windows without Developer Mode also denies os.symlink (WinError 1314): a real first-run
# large-v3 download crashed on that (2026-08-13). HF_HUB_DISABLE_SYMLINKS makes
# huggingface_hub copy instead of symlink, but treat it as belt-and-suspenders, NOT the
# proven fix: whisperx pins huggingface-hub <1.0, which never reads this var (only hub
# >=1.0 does) and whose cache already copy-degrades on denied symlinks. The likelier root
# cure for that crash is the uv interpreter pre-install below (junction race). If 1314
# recurs on a fresh no-Developer-Mode box, capture the traceback to find the real symlink
# site. Windows-only; costs disk, never correctness. No-ops on macOS/Linux.
export PYTHONUTF8=1 PYTHONIOENCODING=utf-8
case "$(uname -s)" in MINGW*|MSYS*|CYGWIN*) export HF_HUB_DISABLE_SYMLINKS=1 ;; esac

# ─ Hardware auto-detect: an NVIDIA GPU (Windows/Linux) runs WhisperX on CUDA,
# several times faster than CPU. Apple Silicon stays CPU int8 (the lock: MPS
# torch is still flaky for some ops; CPU is slower but never silently wrong).
# WHISPERX_DEVICE=cpu|cuda overrides the auto-pick. The python side runs a full
# fallback ladder (cuda float16 → cuda int8_float16 → cpu int8), so a broken
# CUDA stack degrades to CPU with a warning; it can never block an edit.
GPU=0
if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi -L >/dev/null 2>&1; then GPU=1; fi
DEVICE="${WHISPERX_DEVICE:-}"
if [ -z "$DEVICE" ]; then
  if [ "$GPU" -eq 1 ]; then DEVICE=cuda; else DEVICE=cpu; fi
fi

USAGE="usage: transcribe.sh <job_dir> [--diarize] [--force] [--chunk-size N] [--vad-onset X --vad-offset Y]
       transcribe.sh --file <audio|video> --out <words.json> [--diarize] [--chunk-size N] [--vad-onset X --vad-offset Y]"
JOB_DIR=""
case "${1:-}" in
  --file|--out) ;;
  *) JOB_DIR="${1:?$USAGE}"; shift ;;
esac

DIARIZE=0
FORCE=0
FILE=""
OUT=""
CHUNK_SIZE="${WHISPERX_CHUNK_SIZE:-}"
VAD_ONSET="${VAD_ONSET:-}"
VAD_OFFSET="${VAD_OFFSET:-}"
while [ $# -gt 0 ]; do
  case "$1" in
    --diarize) DIARIZE=1 ;;
    --force)   FORCE=1 ;;
    --file)       FILE="${2:?--file needs a path}"; shift ;;
    --out)        OUT="${2:?--out needs a path}"; shift ;;
    --chunk-size) CHUNK_SIZE="${2:?--chunk-size needs a value}"; shift ;;
    --vad-onset)  VAD_ONSET="${2:?--vad-onset needs a value}"; shift ;;
    --vad-offset) VAD_OFFSET="${2:?--vad-offset needs a value}"; shift ;;
    *) echo "unknown flag: $1" >&2; exit 1 ;;
  esac
  shift
done

# Whisper hears 30 s at a time: a longer window would be cut short, so 30 is the ceiling.
if [ -n "$CHUNK_SIZE" ]; then
  if ! [[ "$CHUNK_SIZE" =~ ^[0-9]+$ ]] || [ "$CHUNK_SIZE" -lt 1 ] || [ "$CHUNK_SIZE" -gt 30 ]; then
    echo "--chunk-size is whole seconds from 1 to 30, got '$CHUNK_SIZE'" >&2; exit 1
  fi
fi

# The two thresholds go together: an onset lowered alone under the default offset (0.363)
# would close every speech region on the frame after it opens.
if [ -n "$VAD_ONSET$VAD_OFFSET" ]; then
  if [ -z "$VAD_ONSET" ] || [ -z "$VAD_OFFSET" ]; then
    echo "--vad-onset and --vad-offset (VAD_ONSET / VAD_OFFSET) are set together" >&2; exit 1
  fi
  for v in "$VAD_ONSET" "$VAD_OFFSET"; do
    [[ "$v" =~ ^0?\.[0-9]+$ ]] || { echo "a VAD threshold is a fraction like 0.3, got '$v'" >&2; exit 1; }
  done
  awk -v on="$VAD_ONSET" -v off="$VAD_OFFSET" 'BEGIN { exit !(off + 0 <= on + 0) }' \
    || { echo "--vad-offset ($VAD_OFFSET) must not exceed --vad-onset ($VAD_ONSET)" >&2; exit 1; }
fi

if [ -n "$FILE$OUT" ]; then
  # Standalone form: never a job folder's transcript/, so nothing canonical is read or replaced.
  if [ -n "$JOB_DIR" ] || [ -z "$FILE" ] || [ -z "$OUT" ]; then echo "$USAGE" >&2; exit 1; fi
  [ -f "$FILE" ] || { echo "no such file: $FILE" >&2; exit 1; }
  FILE="$(cd "$(dirname "$FILE")" && pwd)/$(basename "$FILE")"
  mkdir -p "$(dirname "$OUT")"
  OUT="$(cd "$(dirname "$OUT")" && pwd)/$(basename "$OUT")"
  WORK="/tmp/video-editor/transcribe-file"
  mkdir -p "$WORK"
  CLIPS=("$FILE")
  PY_OUT="$OUT"
else
  JOB_DIR="$(cd "$JOB_DIR" && pwd)"
  JOB_NAME="$(basename "$JOB_DIR")"
  MEDIA_DIR="$JOB_DIR"
  [ -d "$JOB_DIR/raw" ] && MEDIA_DIR="$JOB_DIR/raw"
  WORK="/tmp/video-editor/$JOB_NAME"
  CANON="$JOB_DIR/transcript/words.json"   # persisted canonical transcript — transcribe ONCE, reuse forever
  mkdir -p "$WORK" "$JOB_DIR/transcript"

  # Transcribe ONCE. WhisperX large-v3 is slow + deterministic, so a persisted canonical
  # transcript wins unless --force. This is the single source of truth for the whole
  # pipeline (rough cut AND finishing captions) — nothing else transcribes this footage.
  if [ "$FORCE" -eq 0 ] && [ -f "$CANON" ]; then
    if [ -n "$VAD_ONSET$CHUNK_SIZE" ]; then
      # A reuse would silently drop the settings the caller asked for.
      echo "[transcribe] $CANON exists: --chunk-size / the VAD thresholds apply only to a fresh transcription;" >&2
      echo "[transcribe]   add --force to re-transcribe with them, or unset them to reuse it" >&2
      exit 1
    fi
    echo "[transcribe] reusing canonical transcript $CANON (pass --force to re-transcribe)" >&2
    cp "$CANON" "$WORK/words.json"
    echo "$WORK/words.json"
    exit 0
  fi

  shopt -s nullglob nocaseglob
  CLIPS=("$MEDIA_DIR"/*.mov "$MEDIA_DIR"/*.mp4 "$MEDIA_DIR"/*.mkv "$MEDIA_DIR"/*.m4v)
  shopt -u nocaseglob
  if [ ${#CLIPS[@]} -eq 0 ]; then
    echo "no clips found in $MEDIA_DIR" >&2
    exit 1
  fi
  PY_OUT="$WORK/words.json"
fi

if [ -d /opt/homebrew/opt/ffmpeg@7 ]; then
  export DYLD_LIBRARY_PATH="/opt/homebrew/opt/ffmpeg@7/lib:${DYLD_LIBRARY_PATH:-}"
  export PATH="/opt/homebrew/opt/ffmpeg@7/bin:$PATH"
fi

# Persistent venv: built once, reused every run. whisperx pulls torch, so it
# gets its own box — it can't share the faster-whisper venv (different deps).
VENV="${VIDEO_EDITOR_WHISPERX_VENV:-$HOME/.cache/video-editor/whisperx-venv}"
# venv layout differs by OS: bin/python (macOS/Linux) vs Scripts/python.exe (Windows)
venv_py() { if [ -e "$VENV/Scripts/python.exe" ]; then echo "$VENV/Scripts/python.exe"; else echo "$VENV/bin/python"; fi; }
# sentinel written only after a successful install — a half-built venv (install
# interrupted once) self-heals on the next run instead of wedging forever
if [ ! -e "$VENV/.deps-ok" ]; then
  echo "[transcribe] first-run: building whisperx venv at $VENV (pulls torch, ~minutes)" >&2
  rm -rf "$VENV"
  # Windows: materialize the managed interpreter BEFORE creating the venv. `uv venv
  # --python 3.11` can trigger a just-in-time CPython download whose junction/trampoline
  # finalization races the venv creation and yields a broken venv (hit on a real machine,
  # 2026-08-13). A separate install step is idempotent and instant when already present.
  # Its output goes to a log: on a healthy box it still prints "Missing expected target
  # directory for Python minor version link" (a client box, 2026-09-07), which reads as an
  # error to someone watching the first run and is nothing; the venv step is the real check.
  case "$(uname -s)" in MINGW*|MSYS*|CYGWIN*)
    echo "[transcribe] ensuring a managed Python 3.11 (uv; log: $WORK/uv-python-install.log)" >&2
    uv python install 3.11 >"$WORK/uv-python-install.log" 2>&1 \
      || echo "[transcribe] · uv python install 3.11 reported a problem (see the log); the venv step below is the real check" >&2
    ;;
  esac
  if ! uv venv "$VENV" --python 3.11 >&2; then
    echo "[transcribe] venv creation failed; retrying once from clean" >&2
    rm -rf "$VENV"
    uv venv "$VENV" --python 3.11 >&2
  fi
  uv pip install --python "$(venv_py)" whisperx >&2
  # record what this venv was VERIFIED for; the CUDA step below upgrades it in place
  echo cpu > "$VENV/.mode"
  touch "$VENV/.deps-ok"
fi

# cuda_torch: make this venv's torch a CUDA build and PROVE it, writing .mode from the
# probe. Used on a fresh build AND to repair a venv that exists but is CPU-only on a GPU
# machine (a venv built before GPU support, or while no GPU was visible): that case used
# to print "rm -rf the venv and re-run" and carry on at CPU speed, so an RTX 5070 box
# with an August venv transcribed on CPU with the GPU reported ready by check-setup
# (2026-09-27). The repair keeps the venv, whisperx and the downloaded models; only
# torch/torchaudio are swapped (~3 GB). A repair that fails leaves .cuda-tried so it is
# not re-attempted (and re-downloaded) on every run; delete that file to retry.
cuda_torch() {
  case "$(uname -s)" in
    MINGW*|MSYS*|CYGWIN*)
      # PyPI torch on Windows is CPU-only; swap in the CUDA build (Linux PyPI
      # wheels already ship CUDA, so only Windows needs this). cu128 wheels
      # want a current NVIDIA driver (and are the first to run Blackwell, RTX 50xx);
      # if this install or the runtime probe fails, everything falls back to CPU
      # and the edit still runs.
      #
      # whisperx installed the CPU torch, and a plain `uv pip install torch
      # --index-url <cu128>` on top is a NO-OP: the requirement is already satisfied,
      # so uv never consults the CUDA index, exits 0 ("Checked 2 packages"), and the
      # venv keeps CPU torch while .mode said cuda (a client RTX 3060 ran CPU-only for
      # exactly that, 2026-09-07). Force the reinstall, pinned to the versions whisperx
      # resolved so torchvision/torchcodec, ABI-matched to that torch, keep working.
      echo "[transcribe] NVIDIA GPU detected: installing CUDA torch (~3 GB, once)" >&2
      read -r -a TORCH_PINS <<< "$("$(venv_py)" -c 'import torch, torchaudio; print("torch==" + torch.__version__.split("+")[0], "torchaudio==" + torchaudio.__version__.split("+")[0])' 2>/dev/null || echo "torch torchaudio")"
      uv pip install --python "$(venv_py)" \
          --reinstall-package torch --reinstall-package torchaudio "${TORCH_PINS[@]}" \
          --index-url https://download.pytorch.org/whl/cu128 >&2 \
        || echo "[transcribe] ⚠ CUDA torch install failed (read the uv output above)" >&2
      ;;
  esac
  # .mode is written from a PROBE, never from intent: the install's exit code proves
  # nothing (above). A venv that says cuda but holds CPU torch would request CUDA and
  # the python ladder would quietly drop to CPU on every run.
  if "$(venv_py)" -c 'import torch, sys; sys.exit(0 if torch.cuda.is_available() else 1)' 2>/dev/null; then
    echo "[transcribe] ✓ CUDA verified: $("$(venv_py)" -c 'import torch; print(torch.__version__, "on", torch.cuda.get_device_name(0))' 2>/dev/null)" >&2
    echo cuda > "$VENV/.mode"
    rm -f "$VENV/.cuda-tried"
    return 0
  fi
  echo "[transcribe] ⚠ CUDA did not take (torch.cuda.is_available() is False); this venv stays CPU-only." >&2
  echo "[transcribe]   Transcription works, several times slower. GPU retry: rm \"$VENV/.cuda-tried\" and re-run" >&2
  echo "[transcribe]   (an NVIDIA driver too old for cu128 is the usual cause; update it first)." >&2
  echo cpu > "$VENV/.mode"
  touch "$VENV/.cuda-tried"
  return 1
}
if [ "$DEVICE" = cuda ] && [ "$(cat "$VENV/.mode" 2>/dev/null || echo cpu)" != "cuda" ]; then
  if [ -e "$VENV/.cuda-tried" ]; then
    echo "[transcribe] · CUDA requested, but this venv's CUDA torch did not take on an earlier try: CPU." >&2
    echo "[transcribe]   GPU retry: rm \"$VENV/.cuda-tried\" and re-run." >&2
    DEVICE=cpu
  else
    echo "[transcribe] · this WhisperX venv is CPU-only on a GPU machine: upgrading it to CUDA in place" >&2
    cuda_torch || DEVICE=cpu
  fi
fi
PYBIN="$(venv_py)"

"$PYBIN" - "$PY_OUT" "$DIARIZE" "$DEVICE" "$CHUNK_SIZE" "$VAD_ONSET" "$VAD_OFFSET" "${CLIPS[@]}" <<'PY'
import json, os, sys, warnings
# pyannote warns on import when torchcodec's shared libraries do not load (Windows: winget's static ffmpeg ships no
# FFmpeg DLLs, 2026-09-27 S5). WhisperX decodes through the ffmpeg CLI and hands pyannote a waveform, so the warning is
# noise; anything that really needs torchcodec still raises its own RuntimeError.
warnings.filterwarnings("ignore", message=r"\s*torchcodec is not installed correctly")
import whisperx

out_path = sys.argv[1]
diarize_flag = sys.argv[2] == "1"
want_device = sys.argv[3]      # "cuda" or "cpu", decided by transcribe.sh
# Validated by transcribe.sh; empty = WhisperX's own defaults (no chunk_size, vad_options None).
chunk_kw = {"chunk_size": int(sys.argv[4])} if sys.argv[4] else {}
vad_options = ({"vad_onset": float(sys.argv[5]), "vad_offset": float(sys.argv[6])}
               if sys.argv[5] else None)
clip_paths = sys.argv[7:]
if chunk_kw:
    print(f"[transcribe] Whisper window (chunk size) {chunk_kw['chunk_size']} s (WhisperX default 30)",
          file=sys.stderr)
if vad_options:
    print(f"[transcribe] VAD onset {vad_options['vad_onset']} / offset {vad_options['vad_offset']} "
          "(WhisperX defaults 0.500 / 0.363)", file=sys.stderr)

# Device ladder. CPU int8 is the always-works floor (and the Apple Silicon
# lock: MPS torch is still spotty for some ops; CPU is slower but never
# silently wrong). With an NVIDIA GPU the ladder tries float16 first, then
# int8_float16 (fits ~4 GB cards), then drops to CPU: a broken CUDA stack
# (old driver, missing cuDNN, OOM) must never block an edit.
tiers = [("cpu", "int8", 8)]
if want_device == "cuda":
    tiers = [("cuda", "float16", 16), ("cuda", "int8_float16", 16)] + tiers
    try:
        import torch
        if not torch.cuda.is_available():
            raise RuntimeError(
                "torch.cuda.is_available() is False (CPU-only torch build, or the "
                "NVIDIA driver is too old for this CUDA runtime; a driver update "
                "usually fixes it)")
        # Windows: ctranslate2 resolves cublas/cudnn DLLs by name from the DLL
        # search path, and the CUDA torch wheel bundles them in torch/lib.
        if os.name == "nt":
            _lib = os.path.join(os.path.dirname(torch.__file__), "lib")
            if os.path.isdir(_lib):
                os.add_dll_directory(_lib)
                os.environ["PATH"] = _lib + os.pathsep + os.environ.get("PATH", "")
        print(f"[transcribe] NVIDIA GPU: {torch.cuda.get_device_name(0)}", file=sys.stderr)
    except Exception as e:
        # Loud on purpose: a correct transcript at several times the cost is the failure
        # mode nobody reports (the trap a client RTX 3060 sat in, 2026-09-07).
        print("[transcribe] " + "!" * 66, file=sys.stderr)
        print(f"[transcribe] ⚠ SLOW PATH: CUDA unavailable ({e}); using CPU int8.", file=sys.stderr)
        print("[transcribe]   This venv was verified for CUDA when built, and the GPU is not reachable now.", file=sys.stderr)
        print("[transcribe]   Fix the NVIDIA driver, or rm -rf the venv and re-run so the rebuild re-verifies CUDA.", file=sys.stderr)
        print("[transcribe] " + "!" * 66, file=sys.stderr)
        tiers = [("cpu", "int8", 8)]

def load_stack(device, compute_type):
    print(f"[transcribe] loading whisperx large-v3 ({device}, {compute_type})", file=sys.stderr)
    asr = whisperx.load_model("large-v3", device, compute_type=compute_type, language="en",
                              vad_options=vad_options)
    print("[transcribe] loading wav2vec2 alignment model", file=sys.stderr)
    align, meta = whisperx.load_align_model(language_code="en", device=device)
    return asr, align, meta

for i, (device, compute_type, batch_size) in enumerate(tiers):
    try:
        asr_model, align_model, align_metadata = load_stack(device, compute_type)
        break
    except Exception as e:
        if i == len(tiers) - 1:
            raise
        nd, nc, _ = tiers[i + 1]
        print(f"[transcribe] ⚠ {device}/{compute_type} failed to load "
              f"({type(e).__name__}: {e}); trying {nd}/{nc}", file=sys.stderr)

def load_diarize(device):
    hf_token = os.environ.get("HUGGINGFACE_TOKEN", "").strip()
    if not hf_token:
        print("[transcribe] --diarize requires HUGGINGFACE_TOKEN in env", file=sys.stderr)
        sys.exit(1)
    print("[transcribe] loading pyannote diarization pipeline", file=sys.stderr)
    return whisperx.DiarizationPipeline(use_auth_token=hf_token, device=device)

diarize_model = load_diarize(device) if diarize_flag else None

def process(path):
    audio = whisperx.load_audio(path)
    tr = asr_model.transcribe(audio, batch_size=batch_size, language="en", **chunk_kw)
    al = whisperx.align(
        tr["segments"], align_model, align_metadata, audio, device,
        return_char_alignments=False)
    if diarize_model is not None:
        al = whisperx.assign_word_speakers(diarize_model(audio), al)
    return audio, al

result = {"clips": []}
for path in clip_paths:
    name = os.path.basename(path)
    print(f"[transcribe] {name}", file=sys.stderr)
    try:
        audio, aligned = process(path)
    except Exception as e:
        # CUDA can also die mid-run (OOM on a long clip, a cuDNN kernel error):
        # rebuild the whole stack on CPU once and redo this clip. CPU errors
        # are real errors and still raise.
        if device == "cpu":
            raise
        print(f"[transcribe] ⚠ CUDA failed mid-run on {name} "
              f"({type(e).__name__}: {e}); falling back to CPU int8", file=sys.stderr)
        device, compute_type, batch_size = "cpu", "int8", 8
        asr_model, align_model, align_metadata = load_stack(device, compute_type)
        if diarize_flag:
            diarize_model = load_diarize(device)
        audio, aligned = process(path)
    duration = len(audio) / 16000.0

    words = []
    for seg in aligned.get("segments", []):
        for w in seg.get("words", []):
            # wav2vec2 sometimes can't align unspeakable tokens (numerals, punctuation).
            # Skip words missing timestamps so cuts.json builders don't crash.
            if "start" not in w or "end" not in w:
                continue
            entry = {
                "w": str(w.get("word", "")).strip(),
                "start": round(float(w["start"]), 3),
                "end": round(float(w["end"]), 3),
                "prob": round(float(w.get("score", 1.0)), 3),
            }
            if "speaker" in w:
                entry["speaker"] = w["speaker"]
            words.append(entry)

    result["clips"].append({
        "clip": name,
        "path": path,
        "duration": round(duration, 3),
        "words": words,
    })

with open(out_path, "w") as f:
    json.dump(result, f, indent=2)
print(f"[transcribe] wrote {out_path}", file=sys.stderr)

# WhisperX collapses an immediately repeated word into ONE long-span entry —
# the transcript shows a single word but the audio has every utterance. Flag
# them so cut authoring doesn't trust the span (splice's refiner auto-snaps
# these at segment boundaries; MID-segment ones need an authored split).
# A LOW-PROBABILITY word is flagged at half the span: the aligner stretches an uncertain word
# across the silence next to it (your-job 2026-09-04: a p0.35 "the" spanned 0.94 s over a
# 0.9 s pause, under the 1.0 s flag, and the pause shipped inside a segment).
for c in result["clips"]:
    for w in c["words"]:
        span = w["end"] - w["start"]
        if span > 1.0 or (span > 0.5 and w["prob"] < 0.5):
            why = ("possible merged repeat" if span > 1.0
                   else f"low-prob (p{w['prob']:.2f}) word stretched over a pause")
            print(f"[transcribe] ⚠ long-span word {w['w']!r} "
                  f"{w['start']:.2f}-{w['end']:.2f} ({span:.2f}s) "
                  f"— {why}, check the audio before keeping",
                  file=sys.stderr)
PY

if [ -n "$FILE" ]; then
  echo "$OUT"
  exit 0
fi

# Persist the canonical copy so we never transcribe this footage again.
cp "$WORK/words.json" "$CANON"
echo "[transcribe] persisted canonical transcript → $CANON" >&2
echo "$WORK/words.json"
