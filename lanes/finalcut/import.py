#!/usr/bin/env python3
"""import.py: import a lane FCPXML into the patched Final Cut as a NEW library, then prove it landed clip for clip.

  uv run lanes/finalcut/import.py <built.fcpxml> [--timeout 120]

Final Cut's own import (NSWorkspace open of the .fcpxml with the patched app), never SpliceKit's `fcpxml.import`:
that routes the XML through the pasteboard (it overwrites the clipboard) and failed on FCP 12.3 with a nil-insert
exception, leaving a "Which library do you want to import (null) into?" sheet (2026-09-25). The FCPXML's
`<import-options>` names the library location, so FCP creates the library with no dialog.

It refuses when the target .fcpbundle already exists (FCP would ask which library to use), waits until the project
opens through the bridge, fails on a dialog still open 15 s later (a progress sheet is transient), then runs verify.py against the live export.
Exit: 0 imported and identical · 1 imported but different · 2 refused / not imported.
"""
import argparse, glob, os, re, subprocess, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sk import call, dismiss_notification_sheet, open_project  # noqa: E402
from share import stale_patch_note  # noqa: E402

APP = next(iter(sorted(glob.glob(os.path.expanduser('~/Applications/SpliceKit/Final Cut Pro*.app')))),
           os.path.expanduser('~/Applications/SpliceKit/Final Cut Pro.app'))   # the one-time purchase or Creator Studio


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('fcpxml')
    ap.add_argument('--timeout', type=float, default=120)
    a = ap.parse_args()
    x = Path(a.fcpxml).read_text(encoding="utf-8")
    lib = re.search(r'key="library location" value="file://([^"]+)"', x)
    proj = re.search(r'<project name="([^"]+)"', x)
    if not lib or not proj:
        print('✗ not a lane FCPXML: no library location / project', file=sys.stderr)
        return 2
    lib_path = lib.group(1).replace('%20', ' ')
    if os.path.exists(lib_path):
        print(f'✗ {lib_path} already exists: close it in FCP (File > Close Library) and move it aside first', file=sys.stderr)
        return 2
    app = APP if os.path.exists(APP) else None
    if not app:
        print(f'✗ no patched Final Cut at {APP}: run the SpliceKit patcher', file=sys.stderr)
        return 2
    note = stale_patch_note(APP)
    if note:
        print(note, flush=True)
    try:
        call('system.version', timeout=10)
    except Exception as ex:
        print(f'✗ no SpliceKit bridge ({ex}): launch the patched FCP first', file=sys.stderr)
        return 2
    dismiss_notification_sheet()
    subprocess.run(['open', '-a', app, os.path.abspath(a.fcpxml)], check=True)
    t0, ok = time.time(), False
    while time.time() - t0 < a.timeout:
        time.sleep(3)
        try:
            open_project(proj.group(1))
            ok = True
            break
        except Exception:
            pass
    for _ in range(6):            # an import leaves a transient progress sheet up for a few seconds
        dismiss_notification_sheet()
        dialogs = call('dialog.detect').get('dialogCount', 0)
        if not dialogs:
            break
        time.sleep(2.5)
    if not ok:
        print(f'✗ project "{proj.group(1)}" did not open within {a.timeout:.0f} s (dialogs open: {dialogs})', file=sys.stderr)
        return 2
    if dialogs:
        print(f'✗ imported, but {dialogs} dialog(s) are open in FCP: read them with sk.py dialog.detect', file=sys.stderr)
        return 2
    print(f'✓ imported "{proj.group(1)}" into {lib_path} in {time.time() - t0:.0f} s', flush=True)
    return subprocess.run([sys.executable, str(Path(__file__).resolve().parent / 'verify.py'), a.fcpxml]).returncode


if __name__ == '__main__':
    sys.exit(main())
