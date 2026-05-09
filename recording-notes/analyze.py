#!/usr/bin/env python3
"""
Recording Analyzer
------------------
Transcribes an m4a (or any audio) file using local OpenAI Whisper,
optionally diarizes speakers with pyannote.audio, then uses Anthropic
Claude to produce a structured note including:
  - Full transcript
  - Summary / key points
  - Action items

Usage:
    python analyze.py <audio_file> [options]

Options:
    --model       Whisper model size: tiny, base, small, medium, large  (default: base)
    --hf-token    HuggingFace token for pyannote speaker diarization (optional)
    --output      Output file path (.md or .txt).  Defaults to <audio_file>.notes.md
    --no-diarize  Skip speaker diarization even if --hf-token is provided
"""

import argparse
import os
import sys
import json
import textwrap
from pathlib import Path


# ---------------------------------------------------------------------------
# Helper: pretty section header
# ---------------------------------------------------------------------------
def section(title: str) -> str:
    bar = "-" * len(title)
    return f"\n{title}\n{bar}"


# ---------------------------------------------------------------------------
# Step 1: Transcribe with local Whisper
# ---------------------------------------------------------------------------
def transcribe(audio_path: str, model_size: str = "base") -> dict:
    print(f"[1/3] Loading Whisper model '{model_size}' ...")
    import whisper  # type: ignore

    model = whisper.load_model(model_size)
    print(f"[1/3] Transcribing '{audio_path}' ...")
    result = model.transcribe(audio_path, verbose=False)
    print("[1/3] Transcription complete.")
    return result  # keys: text, segments, language


# ---------------------------------------------------------------------------
# Step 2: Speaker diarization with pyannote (optional)
# ---------------------------------------------------------------------------
def diarize(audio_path: str, hf_token: str) -> list[dict]:
    """Return list of {start, end, speaker} dicts."""
    print("[2/3] Running speaker diarization ...")
    from pyannote.audio import Pipeline  # type: ignore
    import torch

    pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization-3.1",
        use_auth_token=hf_token,
    )

    device = "cuda" if torch.cuda.is_available() else "cpu"
    pipeline.to(torch.device(device))

    diarization = pipeline(audio_path)
    turns = []
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        turns.append({"start": turn.start, "end": turn.end, "speaker": speaker})

    print(f"[2/3] Diarization complete – found {len(set(t['speaker'] for t in turns))} speaker(s).")
    return turns


def assign_speakers(segments: list[dict], turns: list[dict]) -> list[dict]:
    """Assign a speaker label to each Whisper segment via overlap."""
    def best_speaker(seg_start, seg_end):
        best, best_overlap = "Unknown", 0.0
        for t in turns:
            overlap = min(seg_end, t["end"]) - max(seg_start, t["start"])
            if overlap > best_overlap:
                best_overlap = overlap
                best = t["speaker"]
        return best

    enriched = []
    for seg in segments:
        enriched.append(
            {
                "start": seg["start"],
                "end": seg["end"],
                "text": seg["text"].strip(),
                "speaker": best_speaker(seg["start"], seg["end"]),
            }
        )
    return enriched


def format_transcript(segments: list[dict], has_speakers: bool) -> str:
    lines = []
    current_speaker = None
    for seg in segments:
        ts = f"[{int(seg['start']//60):02d}:{int(seg['start']%60):02d}]"
        if has_speakers:
            spk = seg.get("speaker", "Unknown")
            if spk != current_speaker:
                current_speaker = spk
                lines.append(f"\n**{spk}**")
            lines.append(f"  {ts} {seg['text']}")
        else:
            lines.append(f"{ts} {seg['text']}")
    return "\n".join(lines).strip()


# ---------------------------------------------------------------------------
# Step 3: Generate notes with Claude
# ---------------------------------------------------------------------------
def generate_notes(transcript: str) -> dict:
    print("[3/3] Generating summary, key points, and action items with Claude ...")
    import anthropic  # type: ignore

    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env

    system_prompt = textwrap.dedent("""
        You are an expert meeting/recording analyst.
        Given a transcript, produce a JSON object with exactly these keys:
        {
          "summary": "2-4 sentence overview of the recording",
          "key_points": ["bullet 1", "bullet 2", ...],
          "action_items": ["action 1", "action 2", ...]
        }
        Return ONLY the JSON – no markdown fences, no extra text.
        If there are no action items, return an empty list.
    """).strip()

    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": f"TRANSCRIPT:\n\n{transcript}"}],
    )

    raw = message.content[0].text.strip()
    try:
        notes = json.loads(raw)
    except json.JSONDecodeError:
        # Fallback: return raw text in a structured dict
        notes = {"summary": raw, "key_points": [], "action_items": []}

    print("[3/3] Notes generated.")
    return notes


# ---------------------------------------------------------------------------
# Compose final Markdown document
# ---------------------------------------------------------------------------
def compose_markdown(audio_path: str, transcript_text: str, notes: dict) -> str:
    fname = Path(audio_path).name
    lines = [f"# Recording Notes: {fname}", ""]

    # Summary
    lines += [f"## Summary", "", notes.get("summary", ""), ""]

    # Key points
    lines += ["## Key Points", ""]
    for kp in notes.get("key_points", []):
        lines.append(f"- {kp}")
    lines.append("")

    # Action items
    lines += ["## Action Items", ""]
    action_items = notes.get("action_items", [])
    if action_items:
        for ai in action_items:
            lines.append(f"- [ ] {ai}")
    else:
        lines.append("_No action items identified._")
    lines.append("")

    # Transcript
    lines += ["## Transcript", "", transcript_text, ""]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Analyze an audio recording and produce structured notes."
    )
    parser.add_argument("audio", help="Path to audio file (m4a, mp3, wav, mp4, ...)")
    parser.add_argument(
        "--model",
        default="base",
        choices=["tiny", "base", "small", "medium", "large"],
        help="Whisper model size (default: base)",
    )
    parser.add_argument(
        "--hf-token",
        default=os.environ.get("HF_TOKEN"),
        help="HuggingFace token for pyannote diarization (or set HF_TOKEN env var)",
    )
    parser.add_argument("--no-diarize", action="store_true", help="Skip speaker diarization")
    parser.add_argument("--output", default=None, help="Output file path (default: <audio>.notes.md)")

    args = parser.parse_args()

    audio_path = args.audio
    if not Path(audio_path).exists():
        print(f"Error: file not found: {audio_path}", file=sys.stderr)
        sys.exit(1)

    output_path = args.output or (Path(audio_path).stem + ".notes.md")

    # --- Transcribe ---
    result = transcribe(audio_path, model_size=args.model)
    segments = result.get("segments", [])
    plain_transcript = result.get("text", "").strip()

    # --- Diarize (optional) ---
    has_speakers = False
    if not args.no_diarize and args.hf_token:
        try:
            turns = diarize(audio_path, args.hf_token)
            segments = assign_speakers(segments, turns)
            has_speakers = True
        except Exception as exc:
            print(f"[2/3] Diarization failed ({exc}), continuing without speaker labels.")
    else:
        if not args.hf_token:
            print("[2/3] Skipping diarization (no HF_TOKEN). Pass --hf-token to enable.")
        else:
            print("[2/3] Diarization skipped via --no-diarize.")

    transcript_text = format_transcript(segments, has_speakers) if segments else plain_transcript

    # --- Generate notes ---
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    if not anthropic_key:
        print("Warning: ANTHROPIC_API_KEY not set. Skipping AI note generation.", file=sys.stderr)
        notes = {"summary": "", "key_points": [], "action_items": []}
    else:
        notes = generate_notes(plain_transcript)

    # --- Write output ---
    markdown = compose_markdown(audio_path, transcript_text, notes)
    Path(output_path).write_text(markdown, encoding="utf-8")
    print(f"\nDone! Notes saved to: {output_path}")


if __name__ == "__main__":
    main()
