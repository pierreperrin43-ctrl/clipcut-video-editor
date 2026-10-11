"""replace-clips.py — swap normalized audio under a LOCKED Resolve timeline, safely.

Runs INSIDE Resolve's embedded Python via the davinci-resolve MCP:

    script_plugin run_inline {language: py, source:
      "import io; JOB='/abs/path/to/projects/<job>'; "
      "exec(io.open('<abs>/replace-clips.py', encoding='utf-8').read())"}

Pass JOB in from the wrapper as above (or export RESOLVE_JOB before launching Resolve).
Expects normalized copies already rendered by workflows/normalize-sections.sh into
<JOB>/audio-normalized/, matched to media pool clips BY FILENAME.

WHY ReplaceClip AND NOT A RE-EDIT. The timeline references media pool CLIPS, not files, so
repointing a clip's media leaves every cut, trim, slip and hand edit exactly where it is.
That is what makes an audio pass safe to run on a timeline that has already been hand-cut —
which is the only time you should be running one.

WHY THE BEFORE/AFTER SNAPSHOT. "Nothing moved" is a claim, and on a 200-clip timeline nobody
can eyeball it. Every track's (name, start, duration) is captured before the swap and diffed
after; the pass is only correct if every track reports UNCHANGED.

REVERT. Each clip's original path is written to audio-normalized/REVERT.json as it is
replaced. To undo, set REVERT = True in the wrapper beside JOB (or RESOLVE_REVERT=1). A clip already
on its target is skipped, and a re-run merges into an existing map, so the originals are never lost.

Resolve's embedded Python opens files as ASCII — io.open(..., encoding='utf-8') everywhere.
"""
import io
import json
import os

try:
    JOB                  # noqa: F821 — pre-set by the run_inline wrapper (see docstring)
except NameError:
    JOB = os.environ.get("RESOLVE_JOB", "")
if not JOB:
    raise SystemExit("set JOB in the run_inline wrapper (or RESOLVE_JOB env) "
                     "to the absolute projects/<job> folder")
try:
    REVERT              # noqa: F821 — True = put the original media back from REVERT.json (set in the wrapper)
except NameError:
    REVERT = os.environ.get("RESOLVE_REVERT", "") == "1"

NORM = os.path.join(JOB, "audio-normalized")
MAP = os.path.join(NORM, "REVERT.json")

pm = resolve.GetProjectManager()          # noqa: F821
proj = pm.GetCurrentProject()
mp = proj.GetMediaPool()
tl = proj.GetCurrentTimeline()
print("project :", proj.GetName())
print("timeline:", tl.GetName(), tl.GetStartFrame(), "->", tl.GetEndFrame())


def snapshot():
    s = {}
    for kind, n_tracks in (("V", tl.GetTrackCount("video")), ("A", tl.GetTrackCount("audio"))):
        for t in range(1, n_tracks + 1):
            items = sorted(tl.GetItemListInTrack("video" if kind == "V" else "audio", t) or [],
                           key=lambda i: i.GetStart())
            s["%s%d" % (kind, t)] = [(c.GetName(), c.GetStart(), c.GetDuration()) for c in items]
    return s


def walk(folder, acc):
    for c in (folder.GetClipList() or []):
        acc.append(c)
    for f in (folder.GetSubFolderList() or []):
        walk(f, acc)
    return acc


before = snapshot()
items = walk(mp.GetRootFolder(), [])

if REVERT:
    if not os.path.exists(MAP):
        raise SystemExit("no revert map at " + MAP)
    want = json.load(io.open(MAP, encoding="utf-8"))
    print("\nREVERTING from", MAP)
else:
    if not os.path.isdir(NORM):
        raise SystemExit("no normalized dir at " + NORM + " — run workflows/normalize-sections.sh first")
    want = dict((f, os.path.join(NORM, f)) for f in sorted(os.listdir(NORM))
                if f.lower().endswith((".mp4", ".mov")))
    print("\nnormalized files available:", len(want))

revert, done, missing = {}, [], []
for c in items:
    n = c.GetName()
    if n not in want:
        continue
    target = want[n]
    if not os.path.exists(target):
        missing.append(n)
        continue
    old = c.GetClipProperty("File Path")
    if os.path.normpath(old) == os.path.normpath(target):
        continue        # already on its target: recording it would overwrite the true original in the map
    ok = c.ReplaceClip(target)
    new = c.GetClipProperty("File Path")
    revert[n] = old
    done.append((n, bool(ok), old != new))

print("\n--- ReplaceClip ---")
for n, ok, changed in done:
    print("  %s %-30s path changed: %s" % ("OK " if ok else "BAD", n, changed))
print("replaced:", len(done))
if missing:
    print("MISSING on disk, skipped:", missing)

if not REVERT and revert:
    if os.path.exists(MAP):     # a re-run adds to the map; an entry already there holds the true original
        prior = json.load(io.open(MAP, encoding="utf-8"))
        prior.update(dict((k, v) for k, v in revert.items() if k not in prior))
        revert = prior
    io.open(MAP, "w", encoding="utf-8").write(json.dumps(revert, indent=2))
    print("revert map ->", MAP)

after = snapshot()
print("\n--- timeline integrity ---")
moved = 0
for k in sorted(before):
    same = before[k] == after[k]
    if not same:
        moved += 1
    print("  %-4s %4d items  %s" % (k, len(after[k]), "UNCHANGED" if same else "*** MOVED ***"))
print("timeline range:", tl.GetStartFrame(), "->", tl.GetEndFrame())
if moved:
    print("\n*** %d track(s) MOVED — the swap was not clean. Revert and investigate. ***" % moved)
else:
    print("\nclean: every track identical before and after.")
print("save:", pm.SaveProject())
