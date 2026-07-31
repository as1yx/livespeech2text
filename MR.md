# feat: LiveSpeech2Text v3 - i18n UI + real-time translation

## TL;DR

- Adds a Chinese / English UI language switch (English by default; brand name "LiveSpeech2Text" stays as-is)
- Adds explicit recognition-language selection (Chinese / Chinese-English / English-Chinese / English / Auto)
- Adds a real-time translation pane next to the notes pane, with 4 translation modes
- Drops the unused CLI version (`start.bat`, `note_taker.py`) - Web UI is the single entry point
- Translators: Helsinki-NLP/opus-mt-zh-en + opus-mt-en-zh, FP16, lazy-loaded only when translation is enabled

## Why

The Web UI (v2) only had one language for both ASR and the UI itself. A user wanted to:

1. Switch the whole UI between English and Chinese without losing any functionality
2. Tell the model explicitly which language to expect (cleaner output, less hallucination)
3. See a live translation next to the original transcript so they could review a Chinese meeting while reading English, or vice versa

The earlier CLI version (`note_taker.py` + `start.bat`) duplicated everything the Web UI did and was unusable when both were loaded (8 GB VRAM only fits one Qwen3-ASR-1.7B instance). Removed to reduce surface area.

## What Changed

### New

- **`web_ui.py` v3** - rebuilt UI with i18n dict; locale switch updates all labels in place via `gr.update()`
- **`Translator` class** - lazy-loads `MarianMTModel` on first use, thread-pool for non-blocking translation
- **`langdetect`** dependency (50 KB, used to decide "mostly Chinese" vs "mostly English" cases)
- **`sacremoses`** dependency (Marian tokenizer dependency)
- **`translations.md`** output file - translations appended with timestamps, kept separate from `notes.md`
- **Translation models** - downloaded from ModelScope mirror to `_tmp_ms/Helsinki-NLP/opus-mt-{zh-en,en-zh}/` (gitignored)

### Changed

- **`README.md`** - English version on top, Chinese below, with a `<a name="中文版">` anchor for cross-link
- **`MR.md`** - this file (replaces the v1 draft)
- **`.gitignore`** - added `notes.md` and `translations.md` (privacy: never push user transcripts)

### Removed

- `start.bat` - dead-code CLI launcher (couldn't run alongside the Web UI on 8 GB VRAM)
- `note_taker.py` - the script it called; Web UI covers all of its functionality

## How to Test

### Prerequisites (already met on the original dev machine)
- NVIDIA GPU 8 GB+ (RTX 3060 / 4060 or better)
- Python 3.12
- Windows 10 / 11

### 1. Install new dependencies
```bash
venv\Scripts\python.exe -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple langdetect sacremoses
```

### 2. Download translation models (~600 MB total, automatic on first translation)
The translator lazy-loads on first use; no manual download needed. Models are cached under `_tmp_ms/Helsinki-NLP/`.

### 3. Run
```cmd
:: Double-click start_webui.bat
:: A PowerShell window appears with a loading spinner
:: Browser opens to http://localhost:7860 (auto)
:: Click the microphone icon, allow browser mic permission
:: Speak, pause 1-2 s
```

### 4. Verify the new controls
- Top-right: switch `UI Language` between `English` and `中文` - all labels update in place
- Left column: pick `Recognition Language` from 5 options
- Left column: pick `Translation` from 5 options:
  - `Off` (default)
  - `Mostly Chinese -> English` - only translates when the segment is mostly Chinese
  - `Mostly English -> Chinese` - vice versa
  - `All -> English` / `All -> Chinese` - unconditional
- Right column: a `Translation` textbox shows up, growing as translations arrive

### 5. Verify file outputs
- `notes.md` - timestamped original-language transcripts
- `translations.md` - timestamped translations, one line per translated segment

## File Layout

```
livespeech2text/
├── web_ui.py              # v3, i18n + translation (only entry point)
├── start_webui.bat        # double-click launcher
├── start_webui.ps1        # PowerShell script with loading spinner
├── check_audio.py         # lists available input devices
├── smoke_test.py          # one-shot ASR sanity check
├── MR.md                  # this file
├── README.md              # English (top) + Chinese (below)
├── .gitignore             # excludes venv/, *.log, *.safetensors, notes.md, translations.md
├── translations.md        # git-ignored, runtime output
├── notes.md               # git-ignored, runtime output
└── venv/                  # git-ignored, Python env with all deps (~5 GB)
```

## Known Limitations

- **First-time model load is slow** - Qwen3-ASR-1.7B is 4.5 GB; first launch needs 30-70 s on a typical NVMe. Subsequent launches benefit from OS file cache (5-10 s).
- **Only one ASR instance fits in 8 GB VRAM** - the Web UI and the (now-removed) CLI share the same 1.7 B model. Running both simultaneously OOMs.
- **Web UI is 2-second segmented, not sub-second streaming** - audio is sliced every ~2 s before ASR. Sub-second word-by-word streaming would need vLLM, which doesn't install on Windows; WSL2 works but is out of scope here.
- **opus-mt quality is decent but not SOTA** - longer sentences sometimes lose nuance, especially for code-switched Chinese-English text. If quality matters, swap to a larger translation model (e.g. NLLB-200-distilled-600M) - the Translator class is the only place that needs to change.
- **No speaker diarization** - overlapping speakers in one recording become a single muddled transcript.
- **Windows PowerShell 5.1 renders UTF-8 Chinese as mojibake** - use Git Bash or PowerShell 7+ for terminal work. The Gradio UI itself is rendered by the browser and is fine.
- **Translation fires on every recognized segment** - 1-2 s after each ASR chunk. Not strictly "real-time" (word-level) but feels real-time in normal speech.

## Out-of-scope (deferred)

- WSL2 + vLLM for true streaming
- Speaker diarization (pyannote.audio)
- Translation glossary / custom term dictionary
- Exporting notes to SRT / VTT for video subtitles
- Tauri / Electron desktop wrapper to drop the browser

## Rollback

All changes are in `web_ui.py`, `README.md`, `MR.md`, and `.gitignore`. The deleted `start.bat` and `note_taker.py` are still in the recycle bin. Reverting is a single `git revert` on the PR commit.

## Checklist for the reviewer

- [ ] `pip install -i https://pypi.tuna.tsinghua.edu.cn/simple langdetect sacremoses` succeeds
- [ ] Translation models download on first use (no manual step)
- [ ] Switching `UI Language` updates every label in the UI
- [ ] Switching `Recognition Language` to `English` makes the model prefer English output
- [ ] Setting `Translation` to `All -> English` produces English text in the translation box within 1-2 s of each Chinese utterance
- [ ] `notes.md` and `translations.md` are git-ignored
- [ ] `venv/`, `*.log`, `_tmp_ms/`, `*.safetensors` are all git-ignored
