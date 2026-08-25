---
name: video-use-install
description: Install video-use into the current agent (Claude Code, Codex, Hermes, Openclaw, etc.) and wire up ffmpeg + local free Whisper transcription so the user can start editing immediately — no API keys, no paid services.
---

# video-use install

Use this file only for first-time install or reconnect. For daily editing, read `SKILL.md`. Always read `helpers/` — that's where the scripts live.

## What you're doing

You're setting up a conversation-driven video editor for the user. After install, the user drops raw footage into any folder, runs their agent (`claude`, `codex`, etc.) there, and says "edit these into a launch video." You do the rest by reading `SKILL.md`.

Everything in this install is free and runs locally — no ElevenLabs, no paid transcription API, no account required. Transcription uses `faster-whisper` (open-source Whisper) on-device.

Four things must exist on this machine:

1. The `video-use` repo cloned somewhere stable.
2. `ffmpeg` + `ffprobe` on `$PATH` (plus optional `yt-dlp` for online sources).
3. Python deps installed, including `faster-whisper` (local, free, offline transcription — no API key needed).
4. The Remotion CLI installed globally (`@remotion/cli`), so Remotion animation slots don't pay a first-use install tax every time. HyperFrames and Manim stay lazy (installed the first time a slot actually needs them) since they're heavier/less commonly used.

And one thing must be true about the current agent:

5. It can discover `SKILL.md` — either via a global skills directory (`~/.claude/skills/`, `~/.codex/skills/`) or via a `CLAUDE.md` / system-prompt import.

## Install prompt contract

- Do everything yourself. Nothing here requires asking the user for a key or account — only confirmation before `brew install`/`apt install`, and (rarely) which Whisper model size to use if disk/CPU is tight.
- Prefer a stable clone path like `~/Developer/video-use` (not `/tmp`, not `~/Downloads`).
- The skill references helpers by bare name (`transcribe.py`, `render.py`). That works because SKILL.md and `helpers/` ship together — keep them as siblings when you register the skill.
- After install, verify by running one real command against one real file. Don't declare success on file-existence checks alone.

## Steps

### 1. Clone to a stable path

```bash
test -d ~/Developer/video-use || git clone https://github.com/browser-use/video-use ~/Developer/video-use
cd ~/Developer/video-use
```

If the repo is already there, `git pull --ff-only` and continue.

### 2. Install Python deps

```bash
# Prefer uv if available; fall back to pip.
command -v uv >/dev/null && uv sync || pip install -e .
```

`pyproject.toml` lists `faster-whisper`, `librosa`, `matplotlib`, `pillow`, `numpy`. No console scripts — helpers are invoked directly as `python helpers/<name>.py`. The first transcription call downloads the chosen Whisper model weights once (cached under `~/.cache`); after that everything runs fully offline.

### 3. Install ffmpeg (+ optional yt-dlp)

`ffmpeg` and `ffprobe` are hard requirements. `yt-dlp` is only needed if the user wants to pull sources from URLs.

```bash
command -v ffmpeg >/dev/null && command -v ffprobe >/dev/null && echo "ffmpeg OK" || {
  # macOS
  command -v brew >/dev/null && brew install ffmpeg
  # Debian / Ubuntu (root or sudo)
  command -v apt-get >/dev/null && (apt-get update -qq && apt-get install -y ffmpeg)
  # Arch
  command -v pacman >/dev/null && pacman -S --noconfirm ffmpeg
}
command -v yt-dlp >/dev/null || brew install yt-dlp 2>/dev/null || pip install yt-dlp  # optional
```

If a package manager requires a sudo prompt you can't satisfy non-interactively, tell the user the exact command and wait. Do not invent a password. Verify afterwards with `ffmpeg -version` and `ffprobe -version`.

### 4. Install Remotion CLI globally + verify a real render

Remotion is one of the animation engines (see `SKILL.md` → Animations). Installing its CLI globally at setup time means the first Remotion slot in any session doesn't stall on an install:

```bash
command -v remotion >/dev/null || npm install -g @remotion/cli
remotion --version
```

HyperFrames and Manim stay lazy (installed per-slot, first use only) — Remotion is the one engine worth having ready globally because `npx create-video@latest` + `remotion render` are the most commonly reached-for path.

Remotion renders through a headless Chromium. If this machine already has one provisioned for another tool (e.g. Playwright's `$PLAYWRIGHT_BROWSERS_PATH`), point Remotion at it instead of letting it download its own ~200MB copy:

```bash
# Look for an existing headless Chromium/headless_shell binary first
find "${PLAYWRIGHT_BROWSERS_PATH:-$HOME/.cache/ms-playwright}" -iname 'headless_shell' -o -iname 'chrome' 2>/dev/null | head -1
```

If found, remember that path — pass it as `--browser-executable <path>` on every `remotion render`/`still` call for the rest of the session (note it in `project.md`). If nothing is found, Remotion manages its own: `npx remotion browser ensure` downloads it once, cached for subsequent renders.

To confirm the whole chain actually works (don't just check `remotion --version` and call it done), scaffold a disposable throwaway project, render one still frame, and delete it:

```bash
cd /tmp && rm -rf remotion_verify
npx --yes create-video@latest --yes --blank --no-tailwind remotion_verify
cd remotion_verify && npm i --silent
npx remotion still src/index.ts MyComp out.png --frame=10 \
  ${BROWSER_EXEC:+--browser-executable="$BROWSER_EXEC"}
test -s out.png && echo "Remotion render OK"
cd .. && rm -rf remotion_verify
```

### 5. Register the skill with the current agent

Figure out which agent you are running under, and register once. A symlink of the whole repo directory is the right shape — helpers/ needs to sit next to SKILL.md.

- **Claude Code** (`~/.claude/` present):

    ```bash
    mkdir -p ~/.claude/skills
    ln -sfn ~/Developer/video-use ~/.claude/skills/video-use
    ```

- **Codex** (`$CODEX_HOME` set, or `~/.codex/` present):

    ```bash
    mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
    ln -sfn ~/Developer/video-use "${CODEX_HOME:-$HOME/.codex}/skills/video-use"
    ```

- **Hermes / Openclaw / another agent with a skills directory**: symlink `~/Developer/video-use` into that agent's skills directory under the name `video-use`. If the agent has no skills directory, add a line to its system prompt / config pointing at `~/Developer/video-use/SKILL.md` (e.g. an `@~/Developer/video-use/SKILL.md` import in a `CLAUDE.md`-equivalent).

If you can't tell which agent you're in, ask the user once: "which agent am I running under — Claude Code, Codex, or something else?" Then pick the right target.

### 6. Transcription (local, free — no API key)

Transcription runs entirely on-device via `faster-whisper`. No account, no key, no per-minute cost.

1. Confirm the package is importable after step 2:

    ```bash
    python -c "import faster_whisper; print('faster-whisper OK')"
    ```

    If it fails, `pip install faster-whisper` (or re-run `uv sync`).

2. Default model size is `small` (good accuracy/speed balance on CPU). Override with `WHISPER_MODEL=<size>` in `.env` (`tiny`/`base`/`small`/`medium`/`large-v3`) if the user wants faster (smaller) or more accurate (larger) transcription. Only ask the user about this if they bring it up — `small` is a sane default.

3. Optional: free speaker diarization via `pyannote.audio`. This needs a free Hugging Face account (accept the terms once at https://huggingface.co/pyannote/speaker-diarization-3.1, then create a free read token at https://huggingface.co/settings/tokens). Only set this up if the user explicitly wants per-speaker labels — the skill works fine without it:

    ```bash
    pip install 'pyannote.audio'
    printf 'HF_TOKEN=%s\n' "$TOKEN" >> ~/Developer/video-use/.env
    chmod 600 ~/Developer/video-use/.env
    ```

    Never echo the token back in tool output. Never commit `.env`.

### 7. Verify end-to-end

Run one real thing. Prefer the lightest verification that still proves the pipeline is wired up:

```bash
python ~/Developer/video-use/helpers/timeline_view.py --help >/dev/null && echo "helpers OK"
ffprobe -version | head -1
```

Full transcription test is optional at install time — it's free, but the first run downloads Whisper model weights (a few hundred MB), so it's still nicer to wait until the user hands you their first clip rather than doing it blind during install. The Remotion render check in step 4 already covers real end-to-end verification for the animation path, so don't repeat it here.

### 8. Hand off

Tell the user, in one short message:

- Where the skill is installed (`~/Developer/video-use`).
- That they should `cd` into their footage folder and start their agent there (e.g. `claude`).
- That a good first message is: *"edit these into a launch video"* or *"inventory these takes and propose a strategy."*
- That all outputs land in `<videos_dir>/edit/` — the repo stays clean.

## Keeping the skill current

- `cd ~/Developer/video-use && git pull --ff-only` pulls the latest code. The symlink auto-picks it up on the next run.
- If `pyproject.toml` changed deps, re-run `uv sync` / `pip install -e .` after pulling.

## Cold-start reminders

- Symlink the **whole directory**, not just `SKILL.md`. The helpers need to sit next to it.
- If `HF_TOKEN` exists in `.env` but is empty, treat it the same as missing (diarization silently disables itself in `transcribe.py`) — don't assume existence means validity.
- `ffmpeg` from static builds works fine. Any modern (≥ 4.x) build is enough.
- `yt-dlp` is optional. Don't block install on it; install lazily the first time a user asks to pull from a URL.
- Node.js/npm are only needed for HyperFrames or Remotion slots. HyperFrames currently requires Node.js 22+.
- HyperFrames, Remotion, and Manim are all optional *per-slot engines* — pick the one that fits each animation in `SKILL.md`, never default to one globally. The install-time global step only installs the Remotion **CLI** (`@remotion/cli`) so it's instantly available; it does not create a Remotion project or imply Remotion should be preferred. HyperFrames still scaffolds fresh per-slot via `npx --yes hyperframes ...`; Manim stays fully lazy.
- Don't skip the disposable-project render check in step 4 just because `remotion --version` printed something — a CLI that resolves but can't actually launch its headless browser (common in containers without the right libs, or when Remotion tries to download a browser blocked by network policy) fails silently until the first real render, which is a bad time to discover it.
- Transcription is free and local — no need to gate it behind user confirmation for cost reasons. The only thing worth mentioning is disk space/time for the first model download.
- If the user is on Linux without a package manager Claude recognizes, print the manual `ffmpeg` install URL and wait rather than guessing.
