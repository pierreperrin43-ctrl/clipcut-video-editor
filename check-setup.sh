#!/usr/bin/env bash
# check-setup.sh — verify the tools the VIDEO-EDITOR pipeline needs (raw → exported cut).
#
# Report-only: checks what's installed and prints the install command for anything
# missing. Installs NOTHING and touches nothing. Run it once before editing.
#
#   ./check-setup.sh
#
# Cross-platform: macOS, Windows (native — runs in Git Bash, the shell Claude Code uses on
# Windows; see SETUP.md "Windows"), or plain Linux. The Python side (WhisperX large-v3 + torch)
# is NOT installed here — the rough-cut skill builds its own isolated venv on first run
# (~3–5 GB, several minutes).
set -uo pipefail

# ── platform detection ──────────────────────────────────────────────────────
UNAME="$(uname -s 2>/dev/null || echo unknown)"
case "$UNAME" in
  Darwin)               OS=mac;     OSLABEL="macOS" ;;
  Linux)                OS=linux;   OSLABEL="Linux" ;;
  MINGW*|MSYS*|CYGWIN*) OS=windows; OSLABEL="Windows (Git Bash)" ;;
  *)                    OS=other;   OSLABEL="$UNAME" ;;
esac
IS_WSL=0
if [ "$OS" = linux ] && grep -qi microsoft /proc/version 2>/dev/null; then
  IS_WSL=1; OSLABEL="Windows · WSL2 (works, but native Windows is the supported path — see SETUP.md)"
fi

# install-command hint for a given tool, per platform (bash 3.2-safe: case, no assoc arrays)
hint() {  # hint <tool-key>
  case "$OS:$1" in
    mac:ffmpeg)    echo "brew install ffmpeg" ;;
    mac:uv)        echo "brew install uv" ;;
    mac:node)      echo "brew install node" ;;
    mac:python3)   echo "brew install python" ;;
    mac:pillow)    echo "brew install pillow" ;;
    mac:git)       echo "xcode-select --install" ;;
    linux:ffmpeg)  echo "sudo apt install -y ffmpeg" ;;
    linux:uv)      echo "curl -LsSf https://astral.sh/uv/install.sh | sh" ;;
    linux:node)    echo "curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash - && sudo apt install -y nodejs" ;;
    linux:python3) echo "sudo apt install -y python3 python3-pip" ;;
    linux:pillow)  echo "sudo apt install -y python3-pil" ;;
    linux:git)     echo "sudo apt install -y git" ;;
    windows:ffmpeg)  echo "winget install Gyan.FFmpeg          (then restart Claude Code)" ;;
    windows:uv)      echo "winget install astral-sh.uv         (then restart Claude Code)" ;;
    windows:node)    echo "winget install OpenJS.NodeJS.LTS    (then restart Claude Code)" ;;
    windows:python3) echo "winget install Python.Python.3.12   (then restart Claude Code)" ;;
    windows:pillow)  echo "python -m pip install pillow" ;;
    windows:git)     echo "winget install Git.Git             (then restart Claude Code)" ;;
    mac:mono-font)     echo "Menlo ships with macOS: restore /System/Library/Fonts/Menlo.ttc" ;;
    linux:mono-font)   echo "sudo apt install -y fonts-dejavu-core" ;;
    windows:mono-font) echo "Consolas ships with Windows: restore consolab.ttf in your Windows Fonts folder" ;;
    *:higgsfield)  echo "curl -fsSL https://raw.githubusercontent.com/higgsfield-ai/cli/main/install.sh | sh" ;;
    mac:yt-dlp)     echo "brew install yt-dlp" ;;
    linux:yt-dlp)   echo "uv tool install yt-dlp        (apt's build is too old for YouTube)" ;;
    windows:yt-dlp) echo "winget install yt-dlp.yt-dlp        (then restart Claude Code)" ;;
    *)             echo "install $1" ;;
  esac
}

if [ -t 1 ]; then
  G=$(tput setaf 2); R=$(tput setaf 1); Y=$(tput setaf 3); D=$(tput setaf 8); B=$(tput bold); N=$(tput sgr0)
else
  G=; R=; Y=; D=; B=; N=
fi

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
missing=0

check() {  # check <cmd> <label> <tool-key> <used-by>
  local cmd="$1" label="$2" key="$3" used="$4"
  if command -v "$cmd" >/dev/null 2>&1; then
    printf "  ${G}✓${N} %-12s ${D}%s${N}\n" "$label" "$used"
  else
    printf "  ${R}✗${N} %-12s ${Y}%s${N}  ${D}(needed by %s)${N}\n" "$label" "$(hint "$key")" "$used"
    missing=$((missing + 1))
  fi
}

note() { printf "  ${Y}!${N} %-12s ${D}%s${N}\n" "$1" "$2"; }
ok()   { printf "  ${G}✓${N} %-12s ${D}%s${N}\n" "$1" "$2"; }
info() { printf "  ${D}·${N} %-12s ${D}%s${N}\n" "$1" "$2"; }

printf "\n${B}video-editor — prerequisites${N}  ${D}(%s)${N}\n\n" "$OSLABEL"

if [ "$OS" = other ]; then
  printf "  ${R}Unsupported shell/OS detected ($UNAME).${N}\n"
  printf "  ${Y}On Windows, run this from Git Bash (installed with Git for Windows), not PowerShell/cmd. See SETUP.md \"Windows\".${N}\n\n"
fi

# Package-manager preamble
if [ "$OS" = mac ] && ! command -v brew >/dev/null 2>&1; then
  # Homebrew lands in /opt/homebrew (Apple Silicon) or /usr/local (Intel), neither on the
  # default PATH — so "not on PATH" and "not installed" are different situations.
  BREW_OFF=""
  for b in /opt/homebrew/bin /usr/local/bin; do [ -x "$b/brew" ] && { BREW_OFF="$b"; break; }; done
  if [ -n "$BREW_OFF" ]; then
    printf "  ${Y}Homebrew is installed at %s but not on this shell's PATH${N} — ./setup.sh fixes that\n" "$BREW_OFF"
    printf "  ${D}(it adds Homebrew's shellenv line to your login profile); or run once:${N}  ${B}eval \"\$(%s/brew shellenv)\"${N}\n\n" "$BREW_OFF"
  else
    printf "  ${Y}Homebrew not found${N} — most installs below use it. Install it first, then re-run ./setup.sh (it finds the new Homebrew and puts it on PATH):\n"
    printf "    ${B}/bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"${N}\n\n"
  fi
elif [ "$OS" = linux ] && ! { command -v ffmpeg && command -v node && command -v uv; } >/dev/null 2>&1; then
  printf "  ${D}Installs below use apt. Refresh the index once first:${N}  ${B}sudo apt update${N}\n\n"
elif [ "$OS" = windows ] && ! { command -v ffmpeg && command -v node && command -v uv; } >/dev/null 2>&1; then
  printf "  ${D}Installs below use winget (built into Windows 11 / App Installer). After the installs,${N}\n"
  printf "  ${D}restart Claude Code once so it sees the new tools.${N}\n\n"
fi

printf "${B}Core${N} (the raw → exported pipeline — every job needs these):\n"
check ffmpeg  ffmpeg  ffmpeg  "every audio/video pass: rough-cut, captions, music"
check ffprobe ffprobe ffmpeg  "duration/format probing"
check uv      uv      uv      "rough-cut — builds the WhisperX transcribe venv (also gives uvx)"
check node    node    node    "graphics render engine — npx hyperframes"
check npx     npx     node    "runs the hyperframes CLI"
# git is probed by RUNNING it: on a Mac whose Command Line Tools are missing or broken (common after a macOS
# upgrade), /usr/bin/git is a stub that exists and fails.
if git --version >/dev/null 2>&1; then
  printf "  ${G}✓${N} %-12s ${D}%s${N}\n" git "updates — update.py merges each new version in without touching your changes"
else
  printf "  ${R}✗${N} %-12s ${Y}%s${N}  ${D}(needed by %s)${N}\n" git "$(hint git)" "updates (update.py)"
  missing=$((missing + 1))
fi

# Python — probed by RUNNING it, not command -v: Windows installs Python as `python`
# (no python3 name), and ships a fake `python3` Store stub that only opens the Microsoft
# Store. Every pipeline script uses this same python3-then-python probe.
PYBIN=""
if python3 -c '' >/dev/null 2>&1; then PYBIN=python3
elif python -c '' >/dev/null 2>&1; then PYBIN=python; fi
if [ -n "$PYBIN" ]; then
  ok "python" "TikTok/raw caption overlays + the pipeline scripts (runs as \`$PYBIN\`)"
else
  printf "  ${R}✗${N} %-12s ${Y}%s${N}  ${D}(needed by %s)${N}\n" "python" "$(hint python3)" "TikTok/raw caption overlays + the pipeline scripts"
  missing=$((missing + 1))
fi

# node version (HyperFrames CLI wants a modern node; 22+)
if command -v node >/dev/null 2>&1; then
  NODE_MAJOR="$(node -p 'process.versions.node.split(".")[0]' 2>/dev/null || echo 0)"
  if [ "${NODE_MAJOR:-0}" -lt 22 ]; then
    if [ "$OS" = mac ]; then
      if brew list node >/dev/null 2>&1; then up="brew upgrade node"; else up="brew install node"; fi
    else up="$(hint node)"; fi
    note "node version" "found v$(node -v | tr -d v) — HyperFrames wants node ≥ 22 ($up)"
    missing=$((missing + 1))
  fi
fi

# Pillow (PIL) — the TikTok/raw caption PNG overlays. ffmpeg here has no drawtext/libass, so
# PIL is mandatory for those. (Explainer captions render through HyperFrames, not PIL.)
if [ -n "$PYBIN" ]; then
  if "$PYBIN" -c "import PIL" >/dev/null 2>&1; then
    ok "Pillow (PIL)" "TikTok/raw caption overlays"
  else
    note "Pillow (PIL)" "missing — run: $(hint pillow)   (TikTok/raw caption overlays)"
    missing=$((missing + 1))
  fi
fi

# Hardware is informational only: the pipeline auto-picks the fastest reliable
# path per machine (rough-cut's transcribe.sh does the same probe at run time,
# with a full runtime fallback to CPU), so nothing here can count as "missing".
printf "\n${B}Hardware${N}  ${D}(auto-detected; transcription picks the fastest reliable path)${N}:\n"
if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi -L >/dev/null 2>&1; then
  GPUNAME="$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -n1)"
  # An existing WhisperX venv says what it was VERIFIED for (.mode, written from a torch
  # probe by transcribe.sh). A venv built CPU-only before this GPU was set up used to pass
  # as "runs CUDA" here while every transcription ran on CPU (2026-09-27).
  WXV="${VIDEO_EDITOR_WHISPERX_VENV:-$HOME/.cache/video-editor/whisperx-venv}"
  if [ -e "$WXV/.deps-ok" ] && [ "$(cat "$WXV/.mode" 2>/dev/null || echo cpu)" != cuda ]; then
    if [ -e "$WXV/.cuda-tried" ]; then
      note "GPU" "NVIDIA${GPUNAME:+ · $GPUNAME}, but CUDA torch did not take in the WhisperX venv: CPU (update the driver, then rm \"$WXV/.cuda-tried\")"
    else
      note "GPU" "NVIDIA${GPUNAME:+ · $GPUNAME}; the WhisperX venv is CPU-only: the next transcription upgrades it to CUDA in place (~3 GB, once)"
    fi
  else
    ok "GPU" "NVIDIA${GPUNAME:+ · $GPUNAME}: WhisperX runs CUDA float16 (automatic, with CPU fallback)"
  fi
elif [ "$OS" = mac ]; then
  ok "GPU" "Apple Silicon: WhisperX runs CPU int8 (the reliable path; GPU torch is still flaky here)"
else
  ok "GPU" "no NVIDIA GPU: WhisperX runs CPU int8 (works everywhere, just slower)"
fi

printf "\n${B}Fonts${N}  ${D}(bundled, plus one system font)${N}:\n"
# the Talking Head Explainer's caption mono (presets/instagram/talking-head-explainer/captions.py): probed in
# load_font()'s own order (SF Mono, then the bundled stand-in, then FALLBACK_MONO). A fallback is reported, not counted: captions.py draws
# in it and says so. NO mono at all is counted missing: captions.py then exits 2 ("no caption font") at step 5.
WINFONTS="${WINDIR:-C:/Windows}"; WINFONTS="${WINFONTS//\\//}/Fonts"
CAPMONO=""
for f in /System/Library/Fonts/Menlo.ttc "$WINFONTS/consolab.ttf" \
         /usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf /usr/share/fonts/dejavu/DejaVuSansMono-Bold.ttf; do
  if [ -f "$f" ]; then CAPMONO="$f"; break; fi
done
if [ -f /System/Library/Fonts/SFNSMono.ttf ]; then
  ok "caption mono" "SF Mono (/System/Library/Fonts/SFNSMono.ttf) — Talking Head Explainer captions"
elif [ -f "$REPO/assets/fonts/IBMPlexMono-Bold.ttf" ]; then
  ok "caption mono" "bundled stand-in: IBM Plex Mono Bold (assets/fonts/), drawn at SF Mono's advance and box, so every line and box is the locked size"
elif [ -n "$CAPMONO" ]; then
  ok "caption mono" "fallback: $(basename "$CAPMONO") — no SF Mono here, so captions.py draws in $CAPMONO and names it (not the locked look)"
else
  note "caption mono" "no SF Mono and no fallback mono (Menlo, Consolas or DejaVu Sans Mono Bold): Talking Head Explainer captions will fail. $(hint mono-font)"
  missing=$((missing + 1))
fi
if [ -f "$REPO/assets/fonts/Inter-Regular.otf" ]; then
  ok "Inter" "bundled in assets/fonts/ — the display fallback for every PIL/HTML builder"
else
  note "Inter" "missing from assets/fonts/ — graphics display font. Re-download from https://rsms.me/inter"
  missing=$((missing + 1))
fi
if [ "$OS" = mac ]; then
  if ls /Library/Fonts/SF-Pro-Display-*.otf >/dev/null 2>&1 || [ -f /System/Library/Fonts/SFNS.ttf ]; then
    ok "SF Pro (system)" "installed — used wherever a preset names it; bundled Inter stands in everywhere else"
  else
    note "SF Pro (system)" "not installed (optional) — bundled Inter stands in. Prefer SF Pro? https://developer.apple.com/fonts"
  fi
else
  ok "display font" "bundled Inter is the display font on $OSLABEL (SF Pro is macOS-only, not needed)"
fi

printf "\n${B}Bundled assets${N}  ${D}(shipped with the repo — nothing to download)${N}:\n"
# YuNet face detection — a HARD dep of chin-line.py (the low-band floor every long-form job
# measures) and face-frame.py (the Talking Head Explainer framing), so a miss counts against `missing`.
if [ -f "$REPO/assets/models/face_detection_yunet_2023mar.onnx" ]; then
  ok "face model" "assets/models/ — chin-line.py (low-band floor) + face-frame.py (Talking Head Explainer framing)"
else
  note "face model" "missing from assets/models/ — chin-line.py and face-frame.py need face_detection_yunet_2023mar.onnx"
  missing=$((missing + 1))
fi
# SFX + LUT libraries: advisory only. A job can be finished without either (hand-place the cut
# sheet, skip the Look), so neither may ever fail the core count.
if [ -d "$REPO/assets/sfx" ] && [ -n "$(ls "$REPO/assets/sfx" 2>/dev/null)" ]; then
  ok "SFX library" "assets/sfx/ — step 6 sound design"
else
  note "SFX library" "assets/sfx/ empty or absent — step 6 has nothing to place (hand-place, or restore the library)"
fi
# The grade Look is a Premiere-lane mechanic (grade-lut.py replays the .lookparams), so only
# mention it on a Premiere install — the lane is recorded in .setup-complete as `lane=`.
LANE=""
[ -f "$REPO/.setup-complete" ] && LANE="$(sed -n 's/^lane=//p' "$REPO/.setup-complete" | head -n1)"
if [ "$LANE" = premiere ] || [ -z "$LANE" ]; then
  if [ -f "$REPO/assets/luts/rec709/Autumn-Rec709.lookparams" ]; then
    ok "house Look" "assets/luts/rec709/Autumn-Rec709.lookparams — step 4 grade (Premiere lane)"
  else
    note "house Look" "Autumn-Rec709.lookparams absent — grade-lut.py cannot replay the house Look; apply it by hand"
  fi
fi

printf "\n${B}Optional${N} (only if you use the feature):\n"
# Optional items report with ok/note, NEVER with check(): check() increments the CORE
# missing counter, which made an all-green install report "1 core item(s) missing" and
# exit non-zero (breaking setup.sh's verify step) over a b-roll-only tool.
if command -v higgsfield >/dev/null 2>&1; then
  ok "higgsfield" "AI b-roll (step 5b)"
else
  note "higgsfield" "not installed; only needed for AI b-roll: $(hint higgsfield)"
fi
# yt-dlp: pulling reference clips / YouTube research (creative-moves.md, Premiere lab-notes).
# Nothing in the pipeline calls it — it's a hand tool for sourcing edit material.
if command -v yt-dlp >/dev/null 2>&1; then
  ok "yt-dlp" "downloading reference clips + YouTube research"
else
  note "yt-dlp" "not installed; only needed to download reference clips: $(hint yt-dlp)"
fi
# Premiere finishing lane: the pinned vendored engine, installed by ./setup-premiere.sh.
# NEVER suggest the retired premiere-pro-mcp npm package (knockoff republish, broken CEP shim).
# Inside ./setup.sh (VE_SETUP_RUNNING=1) this check runs BEFORE the lane installer, so a
# missing engine is expected there and the note must not send the user to run it by hand.
# Inside ./setup.sh the lane block right after this check reports the lanes itself, and on a machine whose
# lane is recorded, another app's engine is not a to-do.
if [ -d "$(dirname "$0")/vendor/premiere-mcp" ]; then
  ok "premiere-mcp" "vendored engine present (Premiere finishing lane)"
elif [ -n "${VE_SETUP_RUNNING:-}" ]; then
  :
elif [ -n "$LANE" ] && [ "$LANE" != premiere ] && [ "$LANE" != pending ]; then
  info "premiere-mcp" "not installed; not needed on this machine (its lane is $LANE)"
elif [ -f "$REPO/setup.sh" ]; then
  info "premiere-mcp" "not installed; ./setup.sh --lane premiere installs it once Premiere is the pick"
else
  note "premiere-mcp" "not installed — the Premiere finishing lane needs it. Run: ./setup-premiere.sh"
fi
# Resolve finishing lane: Resolve 21.1's own ResolveMCP when .mcp.json points at it (Studio),
# otherwise the pinned vendored MCP, installed by ./setup-resolve.sh.
if grep -q 'ResolveMCP' "$(dirname "$0")/.mcp.json" 2>/dev/null; then
  ok "davinci-resolve" "Resolve's official ResolveMCP wired (Resolve finishing lane)"
elif [ -d "$(dirname "$0")/vendor/davinci-resolve-mcp" ]; then
  ok "davinci-resolve-mcp" "vendored engine present (Resolve finishing lane)"
elif [ -n "${VE_SETUP_RUNNING:-}" ]; then
  :
elif [ -n "$LANE" ] && [ "$LANE" != resolve ] && [ "$LANE" != pending ]; then
  info "davinci-resolve-mcp" "not installed; not needed on this machine (its lane is $LANE)"
elif [ -f "$REPO/setup.sh" ]; then
  info "davinci-resolve-mcp" "not installed; ./setup.sh --lane resolve installs it once Resolve is the pick"
else
  note "davinci-resolve-mcp" "not installed — the Resolve finishing lane needs it. Run: ./setup-resolve.sh"
fi
# Final Cut finishing lane (macOS): SpliceKit's patched copy of Final Cut, the house-look cube and the splicekit
# MCP, installed by ./setup-finalcut.sh (the patch itself is one click in SpliceKit).
if [ "$OS" = mac ] && [ -d "$(dirname "$0")/lanes/finalcut" ]; then
  FCP_PATCHED="$(ls -d "$HOME/Applications/SpliceKit/"Final\ Cut\ Pro*.app 2>/dev/null | head -n 1)"
  FCP_STORE=""
  for c in "/Applications/Final Cut Pro.app" /Applications/Final\ Cut\ Pro*.app; do [ -d "$c" ] && { FCP_STORE="$c"; break; }; done
  fcv() { /usr/bin/defaults read "$1/Contents/Info" CFBundleShortVersionString 2>/dev/null; }
  if [ -n "$FCP_PATCHED" ] && grep -qs '"splicekit"' "$(dirname "$0")/.mcp.json" \
     && [ -f "$HOME/Library/Application Support/ProApps/Custom LUTs/house-Autumn-Rec709-80-120.cube" ]; then
    if [ -n "$FCP_STORE" ] && [ "$(fcv "$FCP_STORE")" != "$(fcv "$FCP_PATCHED")" ]; then
      note "splicekit" "Final Cut was updated ($(fcv "$FCP_STORE")), the patched copy is $(fcv "$FCP_PATCHED"): run ./setup.sh --lane finalcut (one click in SpliceKit)"
    else
      ok "splicekit" "patched Final Cut + house LUT + MCP present (Final Cut finishing lane; launch the copy in ~/Applications/SpliceKit/)"
    fi
  elif [ "${VE_SETUP_RUNNING:-}" = 1 ]; then
    :
  elif [ -n "$LANE" ] && [ "$LANE" != finalcut ] && [ "$LANE" != pending ]; then
    info "splicekit" "not installed; not needed on this machine (its lane is $LANE)"
  elif [ "$LANE" = pending ] || ! compgen -G "/Applications/Final Cut Pro*.app" >/dev/null 2>&1; then
    info "splicekit" "not installed; ./setup.sh --lane finalcut installs it once Final Cut is the pick"
  elif [ -f "$REPO/setup.sh" ]; then
    info "splicekit" "not installed; ./setup.sh --lane finalcut installs it once Final Cut is the pick"
  else
    note "splicekit" "not installed — the Final Cut finishing lane needs it. Run: ./setup-finalcut.sh"
  fi
fi
# transcript-QA wordlist (the suspect scan in rough-cut). macOS ships one; minimal Ubuntu doesn't;
# Windows has no system wordlist, and scan-transcript.py brings its own there: the `english-words` package, a win32
# inline dependency uv installs on first use, carries the same web2 list (L23; this line said "skips" until 2026-09-27).
if [ -f /usr/share/dict/words ] || [ -f /usr/share/dict/web2 ] || [ -f /usr/share/dict/american-english ]; then
  ok "wordlist" "present — rough-cut transcript-QA suspect scan"
elif [ "$OS" = linux ]; then
  note "wordlist" "absent — transcript-QA scan will skip. Enable it: sudo apt install -y wamerican"
elif [ "$OS" = windows ]; then
  ok "wordlist" "bundled for Windows — the english-words package (web2), installed by uv on the first transcript-QA scan"
fi
# On macOS swift drives workflows/window-grab.sh (screenshot an editor window without fronting it), screen-record.sh
# and pii-scan.py (an inline Apple Vision OCR shim). On Windows the same three run through uv alone (wincap.py for
# the window, ocr_shim.py's RapidOCR for the text; 2026-09-27), so there is nothing to probe beyond uv.
if [ "$OS" = mac ]; then
  if command -v swift >/dev/null 2>&1; then
    ok "swift" "present — workflows/window-grab.sh + screen-record.sh (window capture / recording) + pii-scan.py (on-screen secret sweep)"
  else
    note "swift" "not installed — window-grab.sh, screen-record.sh and pii-scan.py need it. Install Xcode command line tools: xcode-select --install"
  fi
fi
# an installed Google Chrome drives workflows/page-record.mjs (headless page captures for screen-rec cells);
# the renderer's own browser (hyperframes browser ensure) is a different binary and is not looked at.
if [ -n "${CHROME_PATH:-}" ] && [ -x "${CHROME_PATH}" ]; then
  ok "chrome" "CHROME_PATH set — workflows/page-record.mjs (headless page capture)"
elif [ -x "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" ] || [ -x "/Applications/Chromium.app/Contents/MacOS/Chromium" ] \
  || [ -x "C:/Program Files/Google/Chrome/Application/chrome.exe" ] || command -v google-chrome >/dev/null 2>&1 || command -v chromium >/dev/null 2>&1; then
  ok "chrome" "present — workflows/page-record.mjs (headless page capture)"
else
  note "chrome" "no Google Chrome / Chromium found — page-record.mjs (URL captures) needs one, or set CHROME_PATH"
fi

# ── version drift: checked BEFORE the verdict, so the verdict and the exit code agree ──
HF_WANT="$(grep -o 'HF_PIN="[0-9.]*"' "$REPO/setup.sh" 2>/dev/null | head -n 1 | tr -cd '0-9.')"
HF_HAVE="$(cat "$REPO/.setup-hyperframes-ok" 2>/dev/null | tr -cd '0-9.')"
[ -f "$REPO/.setup-hyperframes-ok" ] && [ -z "$HF_HAVE" ] && HF_HAVE=0.8.16   # every setup before 2026.09.25.3
HF_DRIFT=0
if [ -f "$REPO/.setup-hyperframes-ok" ] && [ -n "$HF_WANT" ] && [ "$HF_HAVE" != "$HF_WANT" ]; then
  HF_DRIFT=1
  printf "  ${R}✗${N} ${B}Render engine${N} — set up for hyperframes@%s, this version needs %s: run ./setup.sh.\n" "$HF_HAVE" "$HF_WANT"
  missing=$((missing + 1))
fi
# The recorded lane's engine against this version's installer pin (client package only: the installers sit at
# its root). A missing build stamp counts as current, so an install from before the stamps is not told to reinstall.
pin_of() { grep -o 'PIN="[0-9a-f]*"' "$1" 2>/dev/null | head -n 1 | tr -cd '0-9a-f'; }
engine_drift() {   # engine_drift <label> <installer> <clone> <build stamp>
  local want head stamp have
  want="$(pin_of "$2")"; [ -n "$want" ] && [ -d "$3/.git" ] || return 0
  head="$(git -C "$3" rev-parse HEAD 2>/dev/null)"; stamp="$(cat "$4" 2>/dev/null)"
  have=""
  [ -n "$head" ] && [ "$head" != "$want" ] && have="$head"
  [ -z "$have" ] && [ -n "$stamp" ] && [ "$stamp" != "$want" ] && have="$stamp"
  if [ -n "$have" ]; then
    printf "  ${R}✗${N} ${B}%s${N} — %s, this version needs %s: run ./setup.sh\n" "$1" "$(printf '%s' "$have" | cut -c1-7)" "$(printf '%s' "$want" | cut -c1-7)"
    missing=$((missing + 1))
  fi
}
case "$LANE" in
  premiere)
    [ -f "$REPO/setup-premiere.sh" ] && engine_drift "Premiere engine is" "$REPO/setup-premiere.sh" \
      "$REPO/vendor/premiere-mcp" "$REPO/vendor/premiere-mcp/.built-from" ;;
  resolve)
    if [ -f "$REPO/setup-resolve.sh" ] && ! grep -qs 'ResolveMCP' "$REPO/.mcp.json"; then
      engine_drift "Resolve engine is" "$REPO/setup-resolve.sh" "$REPO/vendor/davinci-resolve-mcp" \
        "$REPO/vendor/davinci-resolve-mcp/venv/.built-from"
    fi ;;
  finalcut)
    SK_WANT="$(sed -n 's/^SK_VERSION="\([0-9.]*\)".*/\1/p' "$REPO/setup-finalcut.sh" 2>/dev/null | head -n 1)"
    SK_HAVE="$(/usr/bin/defaults read /Applications/SpliceKit.app/Contents/Info CFBundleShortVersionString 2>/dev/null)"
    if [ -n "$SK_WANT" ] && [ -n "$SK_HAVE" ] && [ "$SK_HAVE" != "$SK_WANT" ]; then
      if [ "$(printf '%s\n%s\n' "$SK_HAVE" "$SK_WANT" | sort -t. -k1,1n -k2,2n -k3,3n -k4,4n | head -n 1)" = "$SK_HAVE" ]; then
        printf "  ${R}✗${N} ${B}SpliceKit${N} — %s, this version needs %s: run ./setup.sh\n" "$SK_HAVE" "$SK_WANT"
        missing=$((missing + 1))
      else
        note "SpliceKit" "$SK_HAVE is newer than the $SK_WANT the lane was proven on (fine; not downgraded)"
      fi
    fi ;;
esac

printf "\n"
if [ "$missing" -eq 0 ]; then
  printf "${G}${B}Core tools present.${N} You're ready to edit.\n"
else
  printf "${R}${B}%d core item(s) missing.${N} Run the commands shown above, then re-run this script.\n" "$missing"
fi

printf "\n${B}One-time, on first use${N} (happens automatically / once):\n"
printf "  ${D}•${N} ${B}WhisperX transcription${N} — rough-cut builds its venv + downloads large-v3 (~3–5 GB) on the first edit. Needs network + a few minutes. One time.\n"
if [ "$HF_DRIFT" -eq 1 ]; then
  :   # named above, before the verdict
elif [ -f "$REPO/.setup-hyperframes-ok" ]; then
  printf "  ${G}✓${N} ${B}Render engine${N} — bootstrapped (hyperframes@${HF_HAVE:-0.8.16}, pinned to the version the locked presets were built against).\n"
else
  # setup.sh only exists in a client package (packaging/overlay/ writes it) — in the source
  # repo the bare command IS the bootstrap, so don't point at a script that isn't here.
  if [ -f "$REPO/setup.sh" ]; then BOOT="./setup.sh does it; by hand, once from the project root:"; else BOOT="run once from the project root:"; fi
  printf "  ${D}•${N} ${B}Render engine bootstrap${N} — %s  ${B}npx hyperframes@${HF_WANT:-0.8.16} browser ensure${N}  (downloads the headless browser the graphics renderer uses; pinned to the version the locked presets were built against).\n" "$BOOT"
  if [ "$IS_WSL" -eq 1 ]; then
    printf "      ${D}On WSL, if the renderer reports a missing shared library, install the headless-Chrome deps it names, e.g.:${N}\n"
    printf "      ${B}sudo apt install -y libnss3 libatk-bridge2.0-0 libgtk-3-0 libgbm1 libasound2t64${N}\n"
  fi
fi
if [ -f "$REPO/brand-kit.md" ] && ! grep -q '<<YOUR_NAME>>' "$REPO/brand-kit.md"; then
  printf "  ${G}✓${N} ${B}Brand${N}: brand-kit.md is filled in (after a change to it or to a preset, say \"apply my brand kit\").\n\n"
elif [ -f "$REPO/brand-kit.md" ]; then
  printf "  ${D}•${N} ${B}Brand${N} (optional): the editor works out of the box with the bundled neutral look. Whenever you want captions and graphics to carry YOUR brand, fill in ${B}brand-kit.md${N} (see SETUP.md).\n\n"
else
  printf "  ${D}•${N} ${B}Brand${N} (optional): client packages ship a ${B}brand-kit.md${N} to fill in; in this tree the brand lives in CLAUDE.md and the presets.\n\n"
fi

[ "$missing" -eq 0 ]
