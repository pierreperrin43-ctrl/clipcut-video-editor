#!/usr/bin/env bash
# check-ae.sh: report-only check that this machine can build graphics in After Effects from a script.
# Installs nothing and changes nothing; every ✗ line carries its fix.
#
#   bash lanes/aftereffects/check-ae.sh [--fonts "Family One,Family Two"]
#
# --fonts takes the font FAMILIES the job's builders use (a client's brand fonts): each is looked up
# in the fonts this machine has installed. A font activated through Adobe Fonts is not a file on disk,
# so a family that is not found is a warning, never a failure: confirm it in After Effects' font menu.
#
#   exit 0  ready            exit 1  something to fix (a ✗ line)            exit 2  no After Effects on this OS
#
#   macOS: proven. Windows (Git Bash): written and NOT YET RUN on a Windows machine.
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
FONTS=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --fonts)   FONTS="${2:-}"; shift 2 ;;
    -h|--help) sed -n '2,13p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *)         shift ;;
  esac
done

bad=0
ok()   { printf '  ✓ %s\n' "$*"; }
no()   { printf '  ✗ %s\n' "$*"; bad=1; }
warn() { printf '  ⚠ %s\n' "$*"; }
squash() { tr -d ' _-' | tr '[:upper:]' '[:lower:]'; }

case "$(uname -s)" in
  Darwin)       OS=mac ;;
  MINGW*|MSYS*) OS=win ;;
  *)            printf '  ✗ After Effects runs on macOS and Windows only.\n'; exit 2 ;;
esac

printf 'After Effects\n'

# 1. installed
if [[ "$OS" == mac ]]; then
  apps="$(ls -d /Applications/Adobe\ After\ Effects\ [0-9][0-9][0-9][0-9]/Adobe\ After\ Effects\ [0-9][0-9][0-9][0-9].app 2>/dev/null | sed 's#.*/##; s#\.app$##' | sort)"
  prefroot="$HOME/Library/Preferences/Adobe/After Effects"
  settings="Settings"
else
  apps="$(ls -d "/c/Program Files/Adobe/Adobe After Effects "[0-9][0-9][0-9][0-9]"/Support Files/AfterFX.exe" 2>/dev/null | sed 's#/Support Files/AfterFX.exe$##; s#.*/##' | sort)"
  prefroot="$(cygpath -u "${APPDATA:-}" 2>/dev/null)/Adobe/After Effects"
  settings="Edit > Preferences"
fi
if [[ -z "$apps" ]]; then
  no "After Effects is not installed. Install it from Creative Cloud, open it once, then run this again."
  exit 1
fi
newest="$(printf '%s\n' "$apps" | tail -n 1)"
ok "installed: $(printf '%s' "$apps" | tr '\n' ',' | sed 's/,/, /g')"

# 2. the scripting permission, read from the newest preferences folder (the file name is localised:
#    "Prefs.txt", "Préfs.txt"; its lines end in CR on macOS)
ver="$(ls "$prefroot" 2>/dev/null | grep -E '^[0-9]+(\.[0-9]+)*$' | sort -t. -k1,1n -k2,2n -k3,3n | tail -n 1)"
pref=""
if [[ -n "$ver" ]]; then
  pref="$(ls "$prefroot/$ver"/*.txt 2>/dev/null | grep -v -e '-effects' -e '-indep-' -e '-paint' -e '-text' -e 'Interpretation Rules' -e 'Trace Database' | head -n 1)"
fi
if [[ -z "$pref" ]]; then
  warn "no After Effects preferences found yet: open After Effects once, then run this again."
else
  val="$(tr '\r' '\n' < "$pref" | sed -n 's/.*"Pref_SCRIPTING_FILE_NETWORK_SECURITY" = "\([0-9]*\)".*/\1/p' | head -n 1)"
  if [[ "$val" == "1" ]]; then
    ok "scripts may write files ($ver preferences)"
  else
    no "scripts may not write files. In After Effects: $settings > Scripting & Expressions > tick \"Allow Scripts to Write Files and Access Network\", then quit and reopen After Effects ($ver preferences)."
  fi
fi

# 3. the bridge itself, only when After Effects is open (this check never launches it)
if [[ "$OS" == mac ]]; then
  running="$(ps -axo comm= | sed -n 's#^.*/\(Adobe After Effects [0-9]\{4\}\)\.app/Contents/MacOS/After Effects$#\1#p' | sort -u | tail -n 1)"
else
  running=""; tasklist //FI "IMAGENAME eq AfterFX.exe" 2>/dev/null | grep -qi 'AfterFX.exe' && running="After Effects"
fi
if [[ -z "$running" ]]; then
  warn "After Effects is not open, so the script bridge was not tried. Open $newest and run this again."
else
  ping="$(mktemp "${TMPDIR:-/tmp}/ae-ping.XXXXXX")"
  printf 'app.version;\n' > "$ping"
  ans="$(bash "$HERE/ae-run.sh" "$ping" --timeout 30 2>&1)"; rc=$?
  rm -f "$ping"
  if [[ $rc -eq 0 ]]; then
    ok "script bridge answers: $running, version ${ans#OK }"
  else
    no "script bridge did not answer from $running: $(printf '%s' "$ans" | tail -n 1)"
  fi
fi

# 4. the job's fonts, when asked
if [[ -n "$FONTS" ]]; then
  printf 'Fonts\n'
  have=""
  command -v fc-list >/dev/null 2>&1 && have="$(fc-list : family 2>/dev/null | squash)"
  if [[ "$OS" == mac ]]; then
    files="$(find /Library/Fonts "$HOME/Library/Fonts" /System/Library/Fonts -type f 2>/dev/null | squash)"
  else
    files="$(find /c/Windows/Fonts "$(cygpath -u "${LOCALAPPDATA:-}" 2>/dev/null)/Microsoft/Windows/Fonts" -type f 2>/dev/null | squash)"
  fi
  IFS=',' read -r -a fams <<< "$FONTS"
  for f in "${fams[@]}"; do
    f="$(printf '%s' "$f" | sed 's/^ *//; s/ *$//')"; [[ -n "$f" ]] || continue
    key="$(printf '%s' "$f" | squash)"
    # a substring test, not a pipe into grep -q: under pipefail the early exit reads as "not found"
    if [[ "$have"$'\n'"$files" == *"$key"* ]]; then
      ok "$f"
    else
      warn "$f: not found on disk. If it comes from Adobe Fonts, check it is active in After Effects' font menu; otherwise install it."
    fi
  done
fi

if [[ $bad -eq 0 ]]; then printf 'After Effects is ready.\n'; exit 0; fi
printf 'Fix the ✗ lines above, then run this again.\n'
exit 1
