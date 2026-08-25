"""Transcribe a video with local, free Whisper (faster-whisper, CTranslate2 backend).

Extracts mono 16kHz audio via ffmpeg, runs it through a local Whisper model
with word-level timestamps, writes the result to
<edit_dir>/transcripts/<video_stem>.json in the same schema the rest of the
skill expects (a `words` list of {type, text, start, end, speaker_id}).

100% free and offline after the model weights are downloaded once (cached by
faster-whisper/huggingface under ~/.cache). No API key, no per-minute cost.

Optional free speaker diarization via `pyannote.audio` (needs a free
Hugging Face account + accepting the model's terms once, still no cost) —
enabled automatically if the package is importable and `HF_TOKEN` is set,
otherwise every word is written with `speaker_id: null` (single speaker).

Cached: if the output file already exists, transcription is skipped.

Usage:
    python helpers/transcribe.py <video_path>
    python helpers/transcribe.py <video_path> --edit-dir /custom/edit
    python helpers/transcribe.py <video_path> --language en
    python helpers/transcribe.py <video_path> --num-speakers 2
    python helpers/transcribe.py <video_path> --model small
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path


DEFAULT_MODEL = os.environ.get("WHISPER_MODEL", "small")


def extract_audio(video_path: Path, dest: Path) -> None:
    cmd = [
        "ffmpeg", "-y", "-i", str(video_path),
        "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le",
        str(dest),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def load_whisper_model(model_size: str):
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        sys.exit(
            "faster-whisper is not installed. Run `pip install faster-whisper` "
            "(or `uv sync` if this project uses uv) and try again."
        )
    # CPU-friendly int8 quantization; falls back to CUDA automatically if
    # a GPU + CUDA libs are available and `device="auto"` picks it up.
    return WhisperModel(model_size, device="auto", compute_type="int8")


def run_diarization(audio_path: Path, num_speakers: int | None) -> list[dict] | None:
    """Return a list of {start, end, speaker} turns via pyannote.audio, or
    None if diarization isn't available/configured. Fully optional — the
    skill works fine without it, just without per-word speaker labels.
    """
    hf_token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN")
    if not hf_token:
        return None
    try:
        from pyannote.audio import Pipeline
    except ImportError:
        return None

    try:
        pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1", use_auth_token=hf_token
        )
    except Exception as e:  # model not accepted yet, network, etc.
        print(f"  diarization unavailable ({e}); continuing without speaker labels", file=sys.stderr)
        return None

    kwargs = {}
    if num_speakers:
        kwargs["num_speakers"] = num_speakers
    diarization = pipeline(str(audio_path), **kwargs)

    turns = []
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        turns.append({"start": turn.start, "end": turn.end, "speaker": speaker})
    return turns


def speaker_at(turns: list[dict] | None, t: float) -> str | None:
    if not turns:
        return None
    for turn in turns:
        if turn["start"] <= t <= turn["end"]:
            return turn["speaker"]
    return None


def call_whisper(
    audio_path: Path,
    model_size: str,
    language: str | None = None,
    num_speakers: int | None = None,
) -> dict:
    model = load_whisper_model(model_size)
    segments, _info = model.transcribe(
        str(audio_path),
        language=language,
        word_timestamps=True,
        vad_filter=True,
    )

    turns = run_diarization(audio_path, num_speakers)

    words: list[dict] = []
    prev_end: float | None = None
    for segment in segments:
        for w in segment.words or []:
            if prev_end is not None and w.start - prev_end > 0.0:
                words.append({
                    "type": "spacing",
                    "text": "",
                    "start": prev_end,
                    "end": w.start,
                })
            words.append({
                "type": "word",
                "text": w.word.strip(),
                "start": w.start,
                "end": w.end,
                "speaker_id": speaker_at(turns, (w.start + w.end) / 2),
            })
            prev_end = w.end

    return {"words": words, "engine": "faster-whisper", "model": model_size}


def transcribe_one(
    video: Path,
    edit_dir: Path,
    api_key: str | None = None,  # unused, kept for call-site compatibility
    language: str | None = None,
    num_speakers: int | None = None,
    model_size: str = DEFAULT_MODEL,
    verbose: bool = True,
) -> Path:
    """Transcribe a single video. Returns path to transcript JSON.

    Cached: returns existing path immediately if the transcript already exists.
    """
    transcripts_dir = edit_dir / "transcripts"
    transcripts_dir.mkdir(parents=True, exist_ok=True)
    out_path = transcripts_dir / f"{video.stem}.json"

    if out_path.exists():
        if verbose:
            print(f"cached: {out_path.name}")
        return out_path

    if verbose:
        print(f"  extracting audio from {video.name}", flush=True)

    t0 = time.time()
    with tempfile.TemporaryDirectory() as tmp:
        audio = Path(tmp) / f"{video.stem}.wav"
        extract_audio(video, audio)
        size_mb = audio.stat().st_size / (1024 * 1024)
        if verbose:
            print(f"  transcribing {video.stem}.wav ({size_mb:.1f} MB) with whisper[{model_size}]", flush=True)
        payload = call_whisper(audio, model_size, language, num_speakers)

    out_path.write_text(json.dumps(payload, indent=2))
    dt = time.time() - t0

    if verbose:
        kb = out_path.stat().st_size / 1024
        print(f"  saved: {out_path.name} ({kb:.1f} KB) in {dt:.1f}s")
        if isinstance(payload, dict) and "words" in payload:
            print(f"    words: {len(payload['words'])}")

    return out_path


def main() -> None:
    ap = argparse.ArgumentParser(description="Transcribe a video with local Whisper (free, offline)")
    ap.add_argument("video", type=Path, help="Path to video file")
    ap.add_argument(
        "--edit-dir",
        type=Path,
        default=None,
        help="Edit output directory (default: <video_parent>/edit)",
    )
    ap.add_argument(
        "--language",
        type=str,
        default=None,
        help="Optional ISO language code (e.g., 'en'). Omit to auto-detect.",
    )
    ap.add_argument(
        "--num-speakers",
        type=int,
        default=None,
        help="Optional number of speakers when known. Improves diarization accuracy (requires pyannote + HF_TOKEN).",
    )
    ap.add_argument(
        "--model",
        type=str,
        default=DEFAULT_MODEL,
        help="Whisper model size: tiny/base/small/medium/large-v3 (default: small, or $WHISPER_MODEL)",
    )
    args = ap.parse_args()

    video = args.video.resolve()
    if not video.exists():
        sys.exit(f"video not found: {video}")

    edit_dir = (args.edit_dir or (video.parent / "edit")).resolve()

    transcribe_one(
        video=video,
        edit_dir=edit_dir,
        language=args.language,
        num_speakers=args.num_speakers,
        model_size=args.model,
    )


if __name__ == "__main__":
    main()
