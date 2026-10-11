#!/usr/bin/env python
"""asr_cli.py: the slice-ASR engine behind cut-audit.py and cut-proof.py, on every OS.

Both tools shell out to an `mlx_whisper`-shaped CLI and read its JSON back. mlx-whisper runs only
on Apple Silicon, so on Windows and Linux every slice-ASR check silently degraded to envelope
heuristics ("ASR unavailable (needs uvx + mlx-whisper on macOS)", measured on a Windows RTX 5070
box 2026-09-27): no content gate, no --say, no gap verification, and no cut-proof at all.

`argv()` is what a caller runs:
  - macOS: `uvx --from mlx-whisper mlx_whisper` (unchanged, the calibrated engine)
  - elsewhere: THIS file under the WhisperX venv's python (transcribe.sh builds it; CUDA when the
    venv was verified for it), running faster-whisper large-v3-turbo, the same weights mlx uses.

As a script it takes the mlx_whisper flags the callers pass (--model, --word-timestamps,
--condition-on-previous-text, --output-format json, --output-dir, one audio file) and writes
mlx_whisper's JSON shape, {"text", "segments": [{"start", "end", "text", "words": [{"word",
"start", "end", "probability"}]}]}, named by the input's basename up to its FIRST dot, exactly as
mlx_whisper names it (both callers rely on that).
"""
import json
import os
import sys
from pathlib import Path

FW_MODEL = "large-v3-turbo"


def venv_python():
    # transcribe.sh's venv, by its own name (the client package renames both in one scrub)
    v = Path(os.environ.get("VIDEO_EDITOR_WHISPERX_VENV") or Path.home() / ".cache/video-editor/whisperx-venv")
    for p in (v / "Scripts" / "python.exe", v / "bin" / "python"):
        if p.exists():
            return str(p)
    return None


def argv():
    """The command prefix for one mlx_whisper-shaped call, or None when no engine exists here."""
    if sys.platform == "darwin":
        return ["uvx", "--from", "mlx-whisper", "mlx_whisper"]
    py = venv_python()
    return [py, str(Path(__file__).resolve())] if py else None


def unavailable_reason():
    if sys.platform == "darwin":
        return "needs uvx + mlx-whisper"
    return "needs the WhisperX venv (run transcribe.sh once to build it)"


def main(args):
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("audio")
    ap.add_argument("--model", default=FW_MODEL)            # an mlx repo id is mapped to the same weights
    ap.add_argument("--word-timestamps", default="True")
    ap.add_argument("--condition-on-previous-text", default="True")
    ap.add_argument("--output-format", default="json")
    ap.add_argument("--output-dir", default=".")
    a = ap.parse_args(args)
    from faster_whisper import WhisperModel
    device, ctype = "cpu", "int8"
    mode = Path(venv_python() or "").parents[1] / ".mode" if venv_python() else None
    if mode and mode.exists() and mode.read_text(encoding="utf-8").strip() == "cuda":
        device, ctype = "cuda", "float16"
    try:
        model = WhisperModel(FW_MODEL, device=device, compute_type=ctype)
    except Exception:                                        # a broken CUDA stack degrades, never blocks
        model = WhisperModel(FW_MODEL, device="cpu", compute_type="int8")
    segs, _ = model.transcribe(a.audio, word_timestamps=a.word_timestamps == "True",
                               condition_on_previous_text=a.condition_on_previous_text == "True",
                               vad_filter=False)
    out = {"text": "", "segments": []}
    for s in segs:
        out["segments"].append({
            "start": s.start, "end": s.end, "text": s.text,
            "words": [{"word": w.word, "start": w.start, "end": w.end, "probability": w.probability}
                      for w in (s.words or [])]})
    out["text"] = "".join(s["text"] for s in out["segments"])
    od = Path(a.output_dir)
    od.mkdir(parents=True, exist_ok=True)
    (od / (Path(a.audio).name.split(".")[0] + ".json")).write_text(json.dumps(out), encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1:])
