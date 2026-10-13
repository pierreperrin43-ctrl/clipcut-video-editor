# My rules

Your own standing instructions for the editor: how you like your cuts, captions, graphics, music,
anything. Claude reads this file with CLAUDE.md in every session, and no update ever changes it, so a
rule written here survives every new version.

Write your rules below, one per line.

- This folder is ClipCut's shared copy of the editor, cloned from the team repository. A new version arrives by `git pull` only: when an editor asks to update, pull. Never run `uv run update.py` here and never merge in a download: Pierre brings each new version in and pushes it (README § For Pierre). A pull that stops on a conflict means a shipped file was edited locally: say which file, and send the editor to Pierre before changing anything.
- When setup reports this folder as a NEW DOWNLOAD of an editor already on the machine, it is not an update: it is the team copy, a second and separate install. Run `./setup.sh --new-install`.
- Never commit or push from this folder.
- After Effects work goes through the `after-effects` skill and `lanes/aftereffects/`. Its Windows path is not proven yet: on Windows, run `bash lanes/aftereffects/check-ae.sh` first and report exactly what it printed.

