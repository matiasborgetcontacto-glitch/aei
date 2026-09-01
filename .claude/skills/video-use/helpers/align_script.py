"""Place a written script against the narration it was written for.

Use this when you have a list of lines (one per shot, scene or image) and need
to know *when* each one is spoken, so cuts land on the right sentence. It does
not assume a constant speaking rate — that is what makes hand-timed edits drift
further and further out as a video goes on.

How it works:

  1. Voice activity from ffmpeg's `silencedetect` splits the audio into
     utterances with exact start/end times.
  2. Each utterance is transcribed with Whisper running locally through
     onnxruntime (`sherpa-onnx`), so every transcribed word carries a real
     timestamp. Weights come from the sherpa-onnx GitHub release, not from
     Hugging Face, which matters on networks where only github.com is reachable.
  3. The script is aligned to the transcript with Needleman-Wunsch. A global
     alignment is required, not `difflib`: a script that returns at the end to
     the scene it opened with defeats difflib's longest-block-first search,
     which then throws away every genuine match before it.
  4. Words that agree become timing anchors; lines whose wording differs get
     interpolated between the anchors around them. So the script may be a
     paraphrase of what is actually said and this still works.

Usage:
    python helpers/align_script.py <media> <script.txt> [-o boundaries.json]

`script.txt` holds one line per phrase, blank lines ignored. The output is a
JSON list of len(lines)+1 times: the start of each line, plus the end of the
last one.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tarfile
import unicodedata
import urllib.request
from pathlib import Path

MODEL_URL = ("https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/"
             "sherpa-onnx-whisper-{size}.tar.bz2")
CACHE = Path.home() / ".cache" / "video-use" / "asr"
SR = 16000
TAIL = 0.8      # silence kept after the last word
MIN_GAP = 0.4   # keep boundaries strictly increasing even where lines collide


def sh(cmd: list[str]) -> str:
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if r.returncode != 0:
        sys.exit(f"FAILED: {' '.join(cmd)}\n{r.stdout.decode(errors='replace')[-2000:]}")
    return r.stdout.decode(errors="replace")


def extract_audio(media: Path, out: Path) -> None:
    sh(["ffmpeg", "-y", "-v", "error", "-i", str(media), "-vn", "-ac", "1",
        "-ar", str(SR), "-c:a", "pcm_s16le", str(out)])


def speech_segments(wav: Path, noise: str = "-32dB", d: float = 0.5) -> list[tuple[float, float]]:
    log = sh(["ffmpeg", "-v", "info", "-i", str(wav),
              "-af", f"silencedetect=noise={noise}:d={d}", "-f", "null", "-"])
    starts = [float(m) for m in re.findall(r"silence_start: ([\d.]+)", log)]
    ends = [float(m) for m in re.findall(r"silence_end: ([\d.]+)", log)]
    dur = float(sh(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                    "-of", "csv=p=0", str(wav)]).strip())
    segs, cur = [], 0.0
    for s, e in zip(starts, ends + [dur]):
        if s > cur + 0.05:
            segs.append((cur, s))
        cur = e
    if dur > cur + 0.05:
        segs.append((cur, dur))
    return segs


def fetch_model(size: str) -> Path:
    d = CACHE / f"sherpa-onnx-whisper-{size}"
    if d.is_dir():
        return d
    CACHE.mkdir(parents=True, exist_ok=True)
    tar = CACHE / f"{size}.tar.bz2"
    print(f"descargando modelo whisper-{size} ...", flush=True)
    urllib.request.urlretrieve(MODEL_URL.format(size=size), tar)
    with tarfile.open(tar) as t:
        t.extractall(CACHE)
    tar.unlink()
    return d


def transcribe(wav: Path, segs, size: str, language: str) -> list[dict]:
    import librosa
    import sherpa_onnx

    m = fetch_model(size)
    rec = sherpa_onnx.OfflineRecognizer.from_whisper(
        encoder=str(m / f"{size}-encoder.int8.onnx"),
        decoder=str(m / f"{size}-decoder.int8.onnx"),
        tokens=str(m / f"{size}-tokens.txt"),
        language=language, task="transcribe", num_threads=4)

    y, _ = librosa.load(wav, sr=SR)
    words = []
    for k, (s, e) in enumerate(segs):
        st = rec.create_stream()
        st.accept_waveform(SR, y[int(s * SR):int(e * SR)])
        rec.decode_stream(st)
        toks = re.findall(r"\w+", st.result.text, re.UNICODE)
        if not toks:
            continue
        # spread the utterance over its words in proportion to how long each is
        lens = [len(t) + 1 for t in toks]
        tot, acc = sum(lens), 0
        for t, L in zip(toks, lens):
            w0 = s + (e - s) * acc / tot
            acc += L
            words.append({"w": t.lower(), "s": round(w0, 3),
                          "e": round(s + (e - s) * acc / tot, 3)})
        if k % 25 == 0:
            print(f"  transcrito {k}/{len(segs)}", flush=True)
    return words


def norm(w: str) -> str:
    w = unicodedata.normalize("NFD", w.lower())
    return "".join(c for c in w if unicodedata.category(c) != "Mn")


def _score(a: str, b: str) -> int:
    if a == b:
        return 3
    if len(a) >= 4 and len(b) >= 4 and a[:4] == b[:4]:
        return 1
    return -2


def nw_align(a: list[str], b: list[str], gap: int = -1) -> list[tuple[int, int]]:
    """Needleman-Wunsch; returns the (i, j) pairs that actually matched."""
    n, m = len(a), len(b)
    H = [[0] * (m + 1) for _ in range(n + 1)]
    P = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        H[i][0], P[i][0] = i * gap, 1
    for j in range(1, m + 1):
        H[0][j], P[0][j] = j * gap, 2
    for i in range(1, n + 1):
        Hi, Hp, Pi, ai = H[i], H[i - 1], P[i], a[i - 1]
        for j in range(1, m + 1):
            d, u, l = Hp[j - 1] + _score(ai, b[j - 1]), Hp[j] + gap, Hi[j - 1] + gap
            if d >= u and d >= l:
                Hi[j], Pi[j] = d, 0
            elif u >= l:
                Hi[j], Pi[j] = u, 1
            else:
                Hi[j], Pi[j] = l, 2
    out, i, j = [], n, m
    while i > 0 and j > 0:
        if P[i][j] == 0:
            if _score(a[i - 1], b[j - 1]) > 0:
                out.append((i - 1, j - 1))
            i, j = i - 1, j - 1
        elif P[i][j] == 1:
            i -= 1
        else:
            j -= 1
    return out[::-1]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("media")
    ap.add_argument("script")
    ap.add_argument("-o", "--out", default="boundaries.json")
    ap.add_argument("--model", default="small", help="whisper size: tiny/base/small/medium")
    ap.add_argument("--language", default="es")
    args = ap.parse_args()

    import numpy as np

    media, out = Path(args.media), Path(args.out)
    lines = [l.strip() for l in Path(args.script).read_text(encoding="utf-8").splitlines() if l.strip()]

    wav = out.parent / f".{media.stem}.16k.wav"
    if not wav.exists():
        extract_audio(media, wav)
    segs = speech_segments(wav)
    print(f"{len(segs)} tramos de habla, {len(lines)} frases de guion")

    cache = out.parent / f".{media.stem}.words.json"
    if cache.exists():
        words = json.loads(cache.read_text())
    else:
        words = transcribe(wav, segs, args.model, args.language)
        cache.write_text(json.dumps(words, ensure_ascii=False))

    stok, starts = [], []
    for p in lines:
        starts.append(len(stok))
        stok += [norm(w) for w in re.findall(r"\w+", p, re.UNICODE)]
    starts.append(len(stok))
    ttok = [norm(w["w"]) for w in words]

    pairs = nw_align(stok, ttok)
    print(f"{len(stok)} palabras de guion, {len(ttok)} transcritas, "
          f"{len(pairs)} anclas ({100 * len(pairs) / max(1, len(stok)):.0f}%)")

    ts = np.array([w["s"] for w in words])
    xs = np.array([0] + [i for i, _ in pairs] + [len(stok)], dtype=float)
    ys = np.array([ts[0]] + [ts[j] for _, j in pairs] + [words[-1]["e"]], dtype=float)
    b = np.interp(np.array(starts, dtype=float), xs, ys)
    b[0], b[-1] = 0.0, words[-1]["e"] + TAIL
    for i in range(1, len(b)):
        b[i] = max(b[i], b[i - 1] + MIN_GAP)

    out.write_text(json.dumps(b.tolist()))
    d = np.diff(b)
    print(f"-> {out}  0.0 .. {b[-1]:.1f}s | por frase min {d.min():.2f} "
          f"med {np.median(d):.2f} max {d.max():.2f}")


if __name__ == "__main__":
    main()
