#!/usr/bin/env bash
# ae-run.sh: run ONE ExtendScript file inside the After Effects that is already open, and print what
# it returned. The script is evaluated inside a try/catch, so an error comes back as text instead of
# raising After Effects' modal alert (that alert blocks every later script until someone clicks it).
#
#   bash lanes/aftereffects/ae-run.sh <script.jsx> [--timeout <seconds>] [--app "<app name or AfterFX.exe path>"]
#
#   exit 0  the script ran; stdout is "OK <its last value>"
#   exit 1  the script threw; stdout is "ERROR <message> @line <n>"
#   exit 2  usage, or an OS with no After Effects
#   exit 3  After Effects did not answer (a dialog is open in it, or the OS refused the control request)
#   exit 4  After Effects is not running: open it, and the project to build into, first
#
#   macOS:            AppleScript's DoScript, proven on After Effects 2026.
#   Windows (native): AfterFX.exe -r, from Git Bash. WRITTEN FROM ADOBE'S DOCUMENTATION AND NOT YET RUN
#                     ON A WINDOWS MACHINE: prove it with check-ae.sh there before a job relies on it.
#
# The app is the After Effects that is running; --app or AE_APP names one when several are installed.
set -uo pipefail

say()  { printf '%s\n' "$*"; }
fail() { printf 'ERROR: %s\n' "$2" >&2; exit "$1"; }

SCRIPT=""; TIMEOUT=600; APP="${AE_APP:-}"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --timeout) TIMEOUT="${2:-}"; shift 2 ;;
    --app)     APP="${2:-}"; shift 2 ;;
    -h|--help) sed -n '2,19p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *)         SCRIPT="$1"; shift ;;
  esac
done

case "$(uname -s)" in
  Darwin)       OS=mac ;;
  MINGW*|MSYS*) OS=win ;;
  *)            fail 2 "After Effects runs on macOS and Windows only." ;;
esac
[[ -n "$SCRIPT" ]] || fail 2 "usage: bash lanes/aftereffects/ae-run.sh <script.jsx> [--timeout <seconds>] [--app \"<app>\"]"
[[ -f "$SCRIPT" ]] || fail 2 "no such script: $SCRIPT"
[[ "$TIMEOUT" =~ ^[0-9]+$ ]] || fail 2 "--timeout takes a number of seconds"
SCRIPT="$(cd "$(dirname "$SCRIPT")" && pwd)/$(basename "$SCRIPT")"

TMP="$(mktemp -d "${TMPDIR:-/tmp}/ae-run.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

# ExtendScript reads a path as a JS string: forward slashes on both systems (C:/Users/... on Windows).
jspath() { local p="$1"; [[ "$OS" == win ]] && p="$(cygpath -m "$p")"; p="${p//\\/\\\\}"; printf '%s' "${p//\"/\\\"}"; }

cat > "$TMP/wrap.jsx" <<JSX
(function () {
  var out = new File("$(jspath "$TMP/result.txt")"), r;
  out.encoding = "UTF-8"; out.lineFeed = "Unix";
  try { r = \$.evalFile(new File("$(jspath "$SCRIPT")")); r = "OK " + ((r === undefined || r === null) ? "" : String(r)); }
  catch (e) { r = "ERROR " + e.toString() + " @line " + String(e.line) + (e.fileName ? " in " + e.fileName : ""); }
  out.open("w"); out.write(r); out.close();
})();
JSX

err=""; rc=0
if [[ "$OS" == mac ]]; then
  if [[ -z "$APP" ]]; then
    APP="$(ps -axo comm= | sed -n 's#^.*/\(Adobe After Effects [0-9]\{4\}\)\.app/Contents/MacOS/After Effects$#\1#p' | sort -u | tail -n 1)"
    [[ -n "$APP" ]] || fail 4 "After Effects is not running. Open it, and the project to build into, then run this again."
  fi
  # mktemp's folder has no space and no quote on macOS, so the wrapper's path goes in as it is.
  err="$(osascript \
    -e "with timeout of $TIMEOUT seconds" \
    -e "tell application \"$APP\" to DoScript \"\$.evalFile(new File('$TMP/wrap.jsx'))\"" \
    -e "end timeout" 2>&1 >/dev/null)"; rc=$?
else
  tasklist //FI "IMAGENAME eq AfterFX.exe" 2>/dev/null | grep -qi 'AfterFX.exe' \
    || fail 4 "After Effects is not running. Open it, and the project to build into, then run this again."
  if [[ -z "$APP" ]]; then
    APP="$(ls -d "/c/Program Files/Adobe/Adobe After Effects "[0-9][0-9][0-9][0-9]"/Support Files/AfterFX.exe" 2>/dev/null | sort | tail -n 1)"
    [[ -n "$APP" ]] || fail 2 "AfterFX.exe not found under C:\\Program Files\\Adobe. Name it: --app \"<path to AfterFX.exe>\"."
  fi
  # -r hands the file to the running After Effects and returns at once: the result file is the signal.
  err="$("$APP" -r "$(cygpath -w "$TMP/wrap.jsx")" 2>&1 >/dev/null)"; rc=$?
  waited=0
  while [[ ! -s "$TMP/result.txt" && $waited -lt $TIMEOUT ]]; do sleep 1; waited=$((waited + 1)); done
fi

if [[ ! -s "$TMP/result.txt" ]]; then
  [[ -n "$err" ]] && printf '%s\n' "$err" >&2
  if [[ "$OS" == mac ]]; then
    fail 3 "$APP did not answer (osascript exit $rc). A dialog may be open in After Effects, or macOS has not allowed this app to control it (System Settings > Privacy & Security > Automation)."
  fi
  fail 3 "After Effects did not answer within $TIMEOUT s (AfterFX.exe exit $rc). A dialog may be open in it."
fi

res="$(cat "$TMP/result.txt")"
say "$res"
[[ "$res" == OK* ]] && exit 0
exit 1
