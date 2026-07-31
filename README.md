# LiveSpeech2Text

> Speak, and it writes. Local, real-time speech-to-text notebook powered by an open-source ASR model.

A Windows desktop tool that turns your microphone into a real-time transcription assistant, built on top of Alibaba's **Qwen3-ASR-1.7B**. Speak naturally, see text appear in a browser UI, and watch your `notes.md` fill up automatically. Fully offline, no API fees, no data leaves your machine.

[中文版说明](#中文版) below.

## Features

- **Real-time transcription** — ~0.08 RTF (a 30-second clip finishes in ~2.3 seconds)
- **Browser-based Web UI** — zero install on the client side, just open `localhost:7860`
- **Built-in gain control** — manual gain (1x-8x) and automatic gain control (AGC) for quiet microphones
- **52 languages** — including Mandarin, English, Cantonese, and 22 Chinese dialects
- **Code-switching friendly** — Qwen3-ASR auto-detects language, handles mixed Chinese/English in one sentence
- **Auto-save to Markdown** — every recognized segment is timestamped and appended to `notes.md`
- **100% local** — all inference runs on your GPU; audio never leaves your machine

## Quick Start

### Prerequisites
- NVIDIA GPU with 8GB+ VRAM (RTX 3060 / 4060 or better)
- Python 3.12
- Windows 10 / 11

### Run the Web UI (recommended)

Double-click `start_webui.bat`. A PowerShell window will appear showing a loading spinner; once ready (30-60s on first run, 5-10s on subsequent runs), your browser will open automatically to `http://localhost:7860`. Click the microphone icon, allow browser mic access, and start speaking. Text appears in real time on the right; press `Ctrl+C` in the PowerShell window (or just close it) to stop.

### Run the CLI version

Double-click `start.bat`. The console shows a `[mic] start recording` prompt; speak and your text lands in `notes.md`. Press `Ctrl+C` to stop.

## Microphone too quiet?

Two knobs in the Web UI:

- **Manual gain** slider (1x to 8x) - try 2x to 5x first
- **Auto Normalize (AGC)** checkbox - automatically pulls volume to a target level; overrides the manual slider

The status panel shows `orig RMS -> boosted RMS`. Normal conversational speech lands in the 0.05 to 0.3 RMS range.

## Installation (clean machine)

```bash
# 1. Create and activate a virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate

# 2. Install PyTorch with CUDA 12.1 (matches the RTX 4060 + driver 591.74 sweet spot)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# 3. Install the rest of the stack (use a Chinese mirror if you're behind the GFW)
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple \
    transformers accelerate soundfile librosa sounddevice qwen-asr gradio modelscope
```

On first run the model (~4.5 GB) downloads automatically from the ModelScope mirror. After that, fully offline.

## Project Layout

| File | Purpose |
|------|---------|
| `web_ui.py` | Gradio Web UI (main entry point) |
| `note_taker.py` | CLI version for terminal-only setups |
| `smoke_test.py` | One-shot diagnostic test (3-second record + transcribe) |
| `check_audio.py` | Lists available audio input devices |
| `start_webui.bat` | Launches the Web UI with a loading spinner in PowerShell |
| `start_webui.ps1` | PowerShell script behind the launcher |
| `start.bat` | Launches the CLI version |
| `MR.md` | PR / merge request description draft |
| `notes.md` | Your live transcript output (git-ignored, stays local) |

## Tech Stack

- **Model**: [Qwen3-ASR-1.7B](https://huggingface.co/Qwen/Qwen3-ASR-1.7B) (Alibaba, Apache 2.0)
- **Inference**: PyTorch 2.5.1 + CUDA 12.1
- **Transformers**: 4.57.6 (qwen-asr pin)
- **UI**: Gradio 6.17
- **Audio I/O**: sounddevice (PortAudio), librosa (resampling)
- **Model source**: ModelScope mirror (avoids the `huggingface.co` connection issue in mainland China)

## Performance

Tested on an RTX 4060 Laptop (8 GB VRAM, driver 591.74, CUDA 13.1):

| Metric | Value |
|--------|-------|
| First-time GPU load | 30-70 s |
| Inference RTF (real-time factor) | ~0.08 |
| VRAM footprint (FP16) | ~3.5 GB |
| Mandarin accuracy (informal test) | 90%+ |

## Known Limitations

- First launch needs internet access to download the 4.5 GB model
- The web UI segments audio every ~2 seconds; this is **near** real-time, not sub-second word-by-word
- No speaker diarization - overlapping speakers in one recording will be transcribed as a mash
- Windows PowerShell 5.1 renders UTF-8 Chinese as mojibake; open the project in **Git Bash** (recommended) or PowerShell 7+ instead. See [POWERSHELL.md](POWERSHELL.md) for details and how to upgrade.
- 8 GB VRAM is enough for **one** 1.7B model; running two ASR instances in parallel will OOM

## License

Code: MIT.
Model weights (Qwen3-ASR-1.7B): Apache 2.0.

---

# 中文版

> 本地化实时语音转写笔记工具 —— 说话即出字,自动保存

基于阿里通义千问 **Qwen3-ASR-1.7B** 开源语音识别模型,Windows 本地部署。
麦克风说话 → 浏览器 Web UI 实时显示文字 → 自动写入 `notes.md`。
全程离线,零 API 费用,数据不出本机。

## ✨ 特性

- 🎙️ **实时拾音** — 说话停顿 1-2 秒自动识别,RTF ≈ 0.08(30s 音频 2.3s 出结果)
- 🌐 **Web UI** — 浏览器打开即用,带增益控制
- 📝 **自动笔记** — 每次识别自动追加到 `notes.md`,带时间戳
- 🇨🇳 **中英混合** — Qwen3-ASR 自动检测语种,中英混说也能识别
- 🌍 **52 种语言** — 包括 22 种中文方言
- 🔒 **完全本地** — 数据不外传,适合敏感内容

## 🚀 快速开始

### 前置
- NVIDIA GPU 8GB+(RTX 3060 / 4060 及以上)
- Python 3.12
- Windows 10/11

### 启动 Web UI(推荐)
双击 `start_webui.bat`,PowerShell 窗口会显示加载动画;首次 30-60 秒,以后 5-10 秒;起来后浏览器自动开 `http://localhost:7860`。点 🎤 麦克风,允许浏览器权限,说话。文字实时进右边笔记框。Ctrl+C 退出。

### 命令行版
双击 `start.bat`,看到 `[mic] 开始录音` 就说话,Ctrl+C 退出。

## 🔧 麦克风声音小怎么办

Web UI 里两个开关:
- **手动增益** 滑块 (1x-8x) — 先试 2x-5x
- **自动归一化 (AGC)** 复选框 — 勾选后自动拉音量,会覆盖手动

状态栏会显示 `原 RMS -> 放大后 RMS`。正常说话应在 0.05-0.3。

## 📦 新机器装一遍

```powershell
# 1. 创建 venv
python -m venv venv
venv\Scripts\activate

# 2. 装 PyTorch (CUDA 12.1)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# 3. 装其余依赖(国内用清华源)
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple transformers accelerate soundfile librosa sounddevice qwen-asr gradio modelscope
```

首次跑自动从 ModelScope 镜像下模型(~4.5GB),下完就完全离线。

## 📁 文件

| 文件 | 作用 |
|------|------|
| `web_ui.py` | Gradio Web UI 主入口 |
| `note_taker.py` | 命令行常驻版 |
| `smoke_test.py` | 单次冒烟测试 |
| `check_audio.py` | 列音频输入设备 |
| `start_webui.bat` / `start_webui.ps1` | Web UI 启动器(带 spinner) |
| `start.bat` | 命令行启动器 |
| `MR.md` | PR 描述草稿 |
| `notes.md` | 实时笔记输出(本地,git 忽略) |

## 🛠️ 技术栈

- 模型: [Qwen3-ASR-1.7B](https://huggingface.co/Qwen/Qwen3-ASR-1.7B) (Apache 2.0)
- 推理: PyTorch 2.5.1 + CUDA 12.1
- Transformers 4.57.6
- Gradio 6.17
- sounddevice (PortAudio) + librosa

## 📊 性能(RTX 4060 Laptop 8GB 实测)

| 指标 | 数值 |
|------|------|
| 首次 GPU 加载 | 30-70s |
| 推理 RTF | ~0.08 |
| 显存占用 | ~3.5GB (FP16) |
| 中文识别率 | 90%+ (主观) |

## ⚠️ 限制

- 首次启动需要联网下模型
- Web UI 是 2 秒分段流式,不是字级别延迟
- 不做说话人分离,多人混说会糊
- 8GB 显存装不下两份 1.7B 模型,只能开一个实例
- **强烈建议用 Git Bash 或 PowerShell 7+**,Windows PowerShell 5.1 中文会乱码。详见 [POWERSHELL.md](POWERSHELL.md)

## 📜 License

代码 MIT,模型 Apache 2.0。
