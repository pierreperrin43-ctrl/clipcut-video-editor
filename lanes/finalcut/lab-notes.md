# Final Cut lane — lab notes (the locks true only on Final Cut + SpliceKit)

Measured on FCP 12.3 (Creator Studio, build 450152), SpliceKit 3.3.9, macOS 27.0, 2026-09-25, on the lane tests: a
finished Premiere short ported over, then a Talking Head Explainer and a long-form job built fresh from their files. Each lock names the
code that holds it.

1. **Import through Final Cut, never through SpliceKit's `fcpxml.import`.** Its "internal" path writes the XML to the
   GENERAL PASTEBOARD (the user's clipboard is overwritten) and on 12.3 threw `attempt to insert nil object` and
   left a "Which library do you want to import (null) into?" sheet. `open -a <patched app> file.fcpxml` with an
   `<import-options>` block (`library location` = a NEW `.fcpbundle`, `copy assets` 0, `suppress warnings` 1) creates
   the library with no dialog. A `<library location=…>` naming a FOLDER raises the same library picker. `import.py`.
2. **Write FCPXML 1.14.** The same Custom LUT element imported as 1.13 came back with its LUT choice DROPPED (only
   Input/Output survived); as 1.14 it survives. `fcpxml_writer.py`. FCP's DTDs live in the app bundle:
   `Contents/Frameworks/Interchange.framework/Versions/A/Resources/FCPXMLv1_14.dtd`.
3. **`srcEnable` is ignored on import, and so is an `<audio>` story element.** A video-only spine clip came back with
   its audio playing (dialogue doubled under the A1 copy) and an audio-only `<clip><audio>` vanished. So the dialogue
   rides ON its V1 clip and a J/L cut is a split edit (`audioStart` / `audioDuration`, which FCP keeps). An unpaired
   V1 clip gets `-96dB`; an unpaired dialogue clip is a connected clip whose picture sits hidden under V1 (warned).
4. **A file's EMBEDDED TIMECODE is its start.** Broadcast-WAV `time_reference` (`Pop 1.wav` = 01:00:00:00, `Bell Ding`
   = 238.82 s) or a timecode track: FCP counts source time from it, Premiere's in-points are zero-based, and a clip
   written from `0s` is DROPPED on import without a word (50 of 103 SFX, every one a timecoded WAV). The writer adds
   the probed timecode to every asset start, clip start, split-edit start and key time.
5. **No time with a denominator past 32 bits.** `122070796932671/254016000000s` (a Premiere tick time) was read as
   122070796932671 SECONDS. Times are rounded onto 1/2400000 s (divisible by 24000 and 48000). A frame-rate clip start
   off the 1001/24000 grid is also snapped by FCP to the frame below.
6. **The Custom LUT choice cannot be written by hand.** Its `LUT` param is Ozone XML holding a `*`-encoded blob that
   names the cube (by name: the decoded blob is about 30 bytes longer than "None", no path). Choose the cube ONCE in
   the inspector on any clip, `fcpxml.export`, and keep the `<filter-video>` as `templates/house-lut-filter.xml`. The
   cube must be in `~/Library/Application Support/ProApps/Custom LUTs/` under the same name on the machine that imports.
7. **The patched copy has its OWN settings.** Stock Final Cut is sandboxed (prefs in its container); the SpliceKit copy
   runs unsandboxed and reads `~/Library/Preferences/com.apple.FinalCutApp.plist`, so what was dismissed or chosen in
   the stock app (What's New, the notification sheet, share settings) comes back once in the copy.
8. **The notification sheet is modal and comes back on every export** until the macOS notification permission for
   the patched copy is answered once (Continue → Allow or Don't Allow; that answer is the creator's).
   `PENotificationWarmingSheetAndTCCWindowController shouldShowWarmingSheetForLastDismissalDate:…` answers YES for any
   dismissal count whenever the sheet is notification-triggered. `sk.py --dismiss` ("Not Now") clears it;
   `import.py` calls it.
9. **The share sheet's save panel is out of process.** No click or keystroke reaches it from the bridge, and
   `-[NSSavePanel ok:]` on its in-process half throws "not implemented"; `setDirectoryURL:` there changes nothing the
   remote panel reads. § 14 is how it is completed. Final Cut's H.264 has no bitrate control, hence the ProRes master
   and `export.py`.
10. **Wispr Flow's always-on-top overlay** (512×614 pt, bottom-centre of the active display, invisible) eats
    clicks on the share sheet's Action popup and the Next button. Use the bridge (`dialog.click`) or keys, or move the
    panel off the bottom centre.
11. **Re-patch after every Final Cut update** (SpliceKit's own caveat; the patched copy is a copy). The open crash report
    on 12.3 Creator Studio (SpliceKit #86, `CloudContentCatalog.updateCatalogAndRegistry`, sample-project download)
    did not fire here; the bridge reports that swizzle as `false`.
12. **The AAC encoder primes 1024 samples**: an audio null test against a Premiere `.mp4` master aligns at a lag of
    1024 (Final Cut's PCM master shows the same lag against it). Aligned, the rebuild's residual was 28 dB under the
    signal (median; worst second 14 dB under): every sound on its sample.
13. **The patched copy keeps stock Final Cut's bundle id** (`com.apple.FinalCutApp`), so `open -b` / `tell application
    id` can launch the unpatched app, which comes up with no bridge and no error. Launch it by PATH; a plain AppleScript
    `quit` closes it cleanly (the library writes continuously, there is no Save), never a force-kill (2026-09-25).
14. **The export needs no clicks: complete the save panel from inside Final Cut.** The share sheet's panel is an
    ordinary `NSSavePanel` in `NSApp.windows` (its delegate `FFShareExportPanelsHelperSingleItem`), and
    `completeWithReturnCode:url:urls:` (q, NSURL, NSArray) is what the out-of-process panel calls back when Save is
    pressed: called with 1 and the job's path, Final Cut renders there as from a click (a short's 3193 frames in
    30 s, a long-form's 13157 frames of 4K ProRes in 97 s, both = the timeline). The render is a background task:
    `share.py` opens Final Cut's Background Tasks window (⌘9) for its progress bar, with no save panel or other sheet
    left up (2026-09-25).
15. **The house zoom is matched as Premiere RENDERS it, not as it is keyed.** The bridge's `zoom` sets the Transform's
    Shutter Angle to 360, so each Premiere frame shows the move half a frame on and blurred across the frame. Keyed
    at Premiere's own values, Final Cut's ramp frames scored 26-38 dB PSNR against the long-form test's master; with the values
    half a frame ahead and Final Cut's Blur > Zoom keyed to 3.8 x the scale points moved in that frame
    (`templates/zoom-blur-filter.xml`, calibrated on the opening zoom-out), the main part scores 49.1 dB mean, 38.0
    worst. The Zoom effect's own default Amount is 32, so it is keyed to 0 outside the ramps. `replay.py` push_moves.
16. **Final Cut plays a MONO clip into L and R at -6.02 dB each** (a split, not a copy; measured on the long-form test's mono section:
    the file -21.9 dB RMS, Final Cut -27.9, Premiere -21.5). Premiere plays mono at -3 dB and `audio-polish.py` gives
    the dialogue that back, so `replay.py` gives mono dialogue +6.02 dB and a mono SFX or music clip +3.01 dB. The
    section went from -23.5 to -17.6 LUFS (Premiere -18.1).
17. **`project.open` matches a name by PREFIX.** With `<job>` and `<job>-v3` both open, `project.open "<job>"` opened
    `<job>-v3`. `import.py` and `share.py` refuse unless the project it answers is exactly the one asked for, and a
    library is closed (File > Close Library, on the ACTIVE project's library) only after that same check.
18. **Never pass a SELECTOR argument through the bridge.** `system.callMethodWithArgs` with `sendAction:to:` and a
    selector-typed arg crashed Final Cut outright (2026-09-25; it reopened only the library that was active, and its
    libraries were intact: they write continuously). A control's action is fired through its menu instead:
    `[popup.menu performActionForItemAtIndex:]` takes an int. `sk.py m()`.
19. **After a launch, Final Cut reopens its libraries UNLOADED.** `copyActiveLibraries` lists them, but
    `project.open` cannot see their projects until each event is loaded (a click in the Libraries sidebar does it).
    Scripted: `FFLibrary.events[i].loadPrimaryObject` → `loadProjectData`, then the open works. `sk.py
    load_libraries()`, which `open_project()` runs when a name is not found; `open -a <copy> <bundle>` alone did not.
20. **The export settings are set on every export, from inside Final Cut.** The Export File sheet's Settings tab
    (Format, Video Codec, Action) are `LKPopUpButton`s in `FFSharePanel.settingsView` (the tab control's target);
    choosing through each popup's menu updates the share model (the size estimate follows: 2.07 → 1.48 GB on
    ProRes 422 LT). `share.py configure_sheet()`: Video and Audio, ProRes 422, Save only, so a fresh install's
    first export needs nothing set by hand.
