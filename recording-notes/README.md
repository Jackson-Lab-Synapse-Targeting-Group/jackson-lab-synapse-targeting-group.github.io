# Recording Analyzer

Transcribes an audio file (m4a, mp3, wav, mp4, …), optionally labels speakers, and uses **Anthropic Claude** to produce a structured Markdown note with:

- Full transcript (with timestamps)
- Summary
- Key points
- Action items

---

## Requirements

- Python 3.9+
- [ffmpeg](https://ffmpeg.org/download.html) installed and on your PATH (required by Whisper for m4a files)

---

## Setup

```bash
cd recording-notes
pip install -r requirements.txt
```

Set your Anthropic API key:

```bash
# Windows (PowerShell)
$env:ANTHROPIC_API_KEY = "sk-ant-..."

# macOS / Linux
export ANTHROPIC_API_KEY="sk-ant-..."
```

---

## Usage

### Basic (transcript + AI notes, no speaker labels)

```bash
python analyze.py meeting.m4a
```

Output is saved as `meeting.notes.md` next to the script.

### With speaker diarization

Speaker diarization uses [pyannote.audio](https://github.com/pyannote/pyannote-audio) and requires:

1. A free [HuggingFace](https://huggingface.co) account
2. Accept the model license at: https://huggingface.co/pyannote/speaker-diarization-3.1
3. A HuggingFace access token

```bash
python analyze.py meeting.m4a --hf-token hf_...
# or set env var HF_TOKEN and just run:
python analyze.py meeting.m4a
```

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `--model` | `base` | Whisper model size: `tiny`, `base`, `small`, `medium`, `large` |
| `--hf-token` | `$HF_TOKEN` | HuggingFace token for speaker diarization |
| `--no-diarize` | off | Skip speaker diarization |
| `--output` | `<audio>.notes.md` | Custom output file path |

### Larger / more accurate transcription

```bash
python analyze.py lecture.m4a --model medium
```

---

## Output format

The generated `.notes.md` file looks like:

```markdown
# Recording Notes: meeting.m4a

## Summary
...

## Key Points
- ...

## Action Items
- [ ] ...

## Transcript
[00:00] Hello, welcome to the meeting...
```

---

## Notes

- First run downloads the Whisper model weights (~75 MB for `base`, ~1.5 GB for `large`).
- Diarization model is ~1 GB and requires a GPU or will run slowly on CPU.
- No audio data is sent to any cloud service during transcription — Whisper runs entirely locally.
- Only the **text transcript** is sent to Anthropic Claude for note generation.
