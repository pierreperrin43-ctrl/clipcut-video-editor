"""The active-project guard every Premiere lane writer runs before its first readback or write.

Every lane script reads and writes `app.project.activeSequence`, which is whatever project the operator last
clicked. With two versions of one job open (v1 active, v2 behind it, 2026-09-13) the graphics placer laid all
37 of the v2 job's graphics over the v1 timeline, splitting v1's own graphics underneath; the damage never
reached disk only because the run was interrupted before its save, and v1 was reverted by closing without
saving. So the ACTIVE project must be THIS job's before anything is read or written: a .prproj under
`projects/<job>/` (the lane keeps it in `projects/<job>/premiere/`), or one named after the job folder. The
guard refuses, it never picks a project: making the right one active is the operator's click.

The right PROJECT is not enough (2026-09-22): `app.project.path` was one job's .prproj while
`app.project.activeSequence` was another open project's timeline, and a project holding a job's organic
sequence beside its AD clone takes the organic plans onto the AD whenever the AD is active. So after the
project check, the SEQUENCE RULE (the same rule premiere-bridge.mjs runs), with S = app.project.activeSequence:
  (a) no S: refuse.
  (b) S is not one of app.project.sequences: refuse, it belongs to another open project. Proved by the
      sequenceID AND by the project file S's own projectItem.treePath names (`\\<file>.prproj\\...`): a
      Save-As copy keeps every sequenceID (live 2026-09-23), so the ID alone passed the original's timeline
      with the copy active. Another open project of the SAME file name holding S (a Finder copy) is
      ambiguous and refuses too: close the other copy.
  (c) a requested name (`sequence`, else env VE_SEQUENCE): S.name must equal it, else refuse naming both.
  (d) otherwise, if the project holds a sequence named exactly the job folder and S.name differs: refuse,
      and name VE_SEQUENCE='<S.name>' as the way to target S deliberately.
  (e) otherwise pass.

    from job_guard import require_job_project
    require_job_project(es, job)          # es = the script's own bridge runner (script -> result string)

Owner of the rule: lanes/premiere/lab-notes.md § The active project is checked before every write.
"""
import json, os, sys
from pathlib import Path

GUARD_ES = r"""(function(){ var o = {path: app.project ? app.project.path : "", open: [], active: null, activeInProject: false, sequences: [], ambiguous: []};
  var B = String.fromCharCode(92);
  function fileOf(x) { x = String(x); return x.substring(Math.max(x.lastIndexOf("/"), x.lastIndexOf(B)) + 1); }
  try { for (var i = 0; i < app.projects.numProjects; i++) o.open.push(app.projects[i].path); } catch (e) {}
  if (app.project) { var s = app.project.activeSequence, file = fileOf(o.path), own = false;
    if (s) { o.active = {name: s.name, sequenceID: s.sequenceID};
      try { own = String(s.projectItem.treePath).indexOf(B + file + B) === 0; } catch (e) {} }
    for (var j = 0; j < app.project.sequences.numSequences; j++) { var q = app.project.sequences[j];
      o.sequences.push(q.name);
      if (s && own && q.sequenceID === s.sequenceID) o.activeInProject = true; }
    if (o.activeInProject) { try { for (var k = 0; k < app.projects.numProjects; k++) { var p = app.projects[k];
        if (p.path === o.path || fileOf(p.path) !== file) continue;
        for (var m = 0; m < p.sequences.numSequences; m++) if (p.sequences[m].sequenceID === s.sequenceID) { o.ambiguous.push(p.path); break; } } }
      catch (e) { o.ambiguous.push("an open project whose sequences could not be read"); } } }
  return JSON.stringify(o); })()"""


def job_root(job):
    """The `projects/<job>` folder that owns a path: a section sub-job (`projects/<job>/sections/<s>`, the
    multi-section pattern) shares its parent's .prproj, so the guard walks up to the child of `projects/`."""
    job = Path(job).resolve()
    for anc in [job, *job.parents]:
        if anc.parent.name == 'projects':
            return anc
    return job


def require_job_project(es, job, sequence=None):
    job = job_root(job)
    o = json.loads(es(GUARD_ES))
    p = Path(o.get('path') or '')
    if not o.get('path') or not (str(p.resolve()).startswith(str(job) + os.sep) or p.stem == job.name):
        sys.exit(f"the ACTIVE Premiere project is {o.get('path') or 'none'}, not this job's ({job.name}/premiere/*.prproj): nothing touched.\n"
                 f"  open projects: {', '.join(o.get('open') or []) or 'none'}\n"
                 "  Make the job's project active (click its timeline, or close the other) and re-run.")
    s, want, names = o.get('active'), sequence or os.environ.get('VE_SEQUENCE') or None, o.get('sequences') or []
    if not s:
        sys.exit(f"there is no active sequence in {o['path']}: nothing touched.\n"
                 "  Open the job's timeline and re-run.")
    if not o.get('activeInProject'):
        sys.exit(f"the active sequence {s['name']} belongs to another open project, not {o['path']}: nothing touched.\n"
                 f"  open projects: {', '.join(o.get('open') or []) or 'none'}\n"
                 "  Click this job's timeline (or close the other project) and re-run.")
    if o.get('ambiguous'):
        sys.exit(f"the active sequence {s['name']} is also in {', '.join(o['ambiguous'])}, another open project with the same file name,"
                 " so which copy it belongs to cannot be proven: nothing touched.\n"
                 "  Close the other copy and re-run.")
    if want and s['name'] != want:
        sys.exit(f"the active sequence is {s['name']}, not the requested {want}: nothing touched.\n"
                 f"  sequences in this project: {', '.join(names) or 'none'}\n"
                 "  Open the requested sequence (or change VE_SEQUENCE) and re-run.")
    if not want and job.name in names and s['name'] != job.name:
        sys.exit(f"the active sequence is {s['name']}, not the job's own sequence {job.name}: nothing touched.\n"
                 f"  To target {s['name']} deliberately, set VE_SEQUENCE='{s['name']}' and re-run.")
    return o['path']
