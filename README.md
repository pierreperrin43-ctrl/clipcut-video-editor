# ClipCut video editor — team copy

Claude as your editing assistant, working inside your own Premiere Pro and After Effects. You point it at
raw footage and talk to it; it cuts, polishes audio, builds graphics and places them on your timeline.

This is a shared, read-only copy. Your footage and your edits stay on your machine: nothing in
`projects/` is ever uploaded.

## What you need

- **Claude Code** (the desktop app or the terminal one), signed in.
- **Premiere Pro.** After Effects too if you want graphics built natively in it.
- **Git.** Mac: already there, or macOS offers to install it the first time. Windows: install
  **Git for Windows** first (`winget install --exact --id Git.Git` in PowerShell), then restart Claude Code.

## Install (once)

1. **Clone it**, with the link Pierre sent you:

       git clone https://github.com/pierreperrin43-ctrl/clipcut-video-editor.git video-editor

   - **Mac:** anywhere, your home folder is fine.
   - **Windows:** a short path OUTSIDE Documents, Desktop, Pictures, Videos, Music and OneDrive, for
     example `C:\Users\<you>\video-editor`. Windows blocks writes in those folders, and the whole path
     must stay under 100 characters.

2. **Open that folder in Claude Code** and say: **set this up**

   Claude installs everything itself (ffmpeg, the render engine, the Premiere bridge and its panel). The
   first run takes 10 to 20 minutes. It may ask you to restart Claude Code, sometimes twice: quit it
   completely, reopen it on the same folder and say **continue setup**. Quit Premiere too when it says so.
   If Claude Code asks whether to enable this project's MCP servers, answer **yes**.

3. **After Effects (optional):** open After Effects, tick **Settings > Scripting & Expressions > Allow
   Scripts to Write Files and Access Network** (Windows: Edit > Preferences), restart it, then say:
   **check After Effects**

If setup says this folder is a "new download" of an editor you already have: you do, this is a second,
separate one. Tell Claude **make it a separate install**.

## Use it

Put a raw clip anywhere (Downloads is fine) and say what you want: **rough cut this**, **edit this
video**, **build this card in After Effects**. Claude tells you what it did and what it skipped.

## Get the latest version

Say **pull the latest team version** (or run `git pull` in the folder). Do not say "update" and do not
download the editor from anywhere else: new versions arrive through this repository only.

## Rules of the road

- Do not edit the files that came with this folder. A change of yours blocks the next `git pull`.
- After Effects scripting on **Windows is not proven yet**. The first Windows editor to try it: send
  Pierre exactly what **check After Effects** printed.
- Something broken or confusing: tell Pierre, with what you asked and what Claude answered.

---

## For Pierre: bringing in a new version

Not exercised yet; the first new version will prove it.

1. Update your own editor folder as usual (`uv run update.py` there). That lays the new version on its
   `upstream` branch.
2. In THIS folder: `git fetch source upstream:upstream`, then `git merge upstream`. Resolve any conflict
   (only the files added for the team can conflict: this README, `my-rules.md`, `.gitattributes`,
   `lanes/aftereffects/`, `.claude/skills/after-effects/`).
3. `git push origin main upstream`, then tell the team to pull.

Never run setup or edit videos in this folder: it is the publishing copy.
