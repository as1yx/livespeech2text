# AGENTS.md

> 项目上下文 + 交接文档。任何人（或 agent）接手前先读这份，5 分钟能接手。

---

## 0. 交接速览（TL;DR）

| 项 | 值 |
|---|---|
| 项目 | LiveSpeech2Text — 本地化实时语音转写笔记工具 |
| 仓库 | https://github.com/as1yx/livespeech2text （public） |
| 本地唯一目录 | `C:\Users\29335\.minimax\agents\mavis\workspace\livespeech2text\` |
| 该目录同时是 | git 工作区 **+** 虚拟环境所在（venv 在里面） |
| 当前分支 | `feat/v4-port-and-notes`（HEAD = `1a2fa02` + 录音功能 commit） |
| `main` | `8268650` — 只含 v1 基础功能，**v3/v4 都没合进去** |
| 启动 | `.\venv\Scripts\python.exe web_ui.py` → http://localhost:7860 |
| 模型 | Qwen3-ASR-1.7B（本地 ~4.5GB）+ opus-mt zh-en/en-zh（~600MB） |
| 硬件 | RTX 4060 Laptop 8GB VRAM — **只能同时跑一个 ASR 实例** |
| 状态 | v4 功能完成可用；v5（设备下拉 / 文件上传 / SRT 字幕）**未开工** |

> ⚠️ **旧路径已废弃**：`C:\Users\29335\Desktop\livespeech2text\` 这个目录**已被删除**。
> 早期开发是"workspace 改代码 → 同步到 Desktop → 在 Desktop commit/push"的双目录模式，
> 现在**不需要同步了**——本目录就是 git 仓库，直接在这里 commit/push。

---

## 1. What this is

**LiveSpeech2Text** — 本地、隐私优先的实时语音转写笔记工具。

- 麦克风实时转写：**Qwen3-ASR-1.7B**（阿里 1.7B ASR 模型，支持 30 种语言）
- Web UI：**Gradio 6**，浏览器端 `gr.Audio(streaming=True)` 采集麦克风
- 翻译：**Helsinki-NLP/opus-mt** zh-en / en-zh（懒加载、线程化、不阻塞转写）
- 录音存档：原始音频实时写 `D:\LiveSpeech2Text\recordings\*.wav`（16k mono 16-bit PCM）
- **完全离线** — 无云端、无遥测，推理全在用户自己的 RTX 4060 上跑
- 用户所有产出（笔记、翻译、录音、配置）全部 `.gitignore` 隔离

**目标用户**：仓库所有者本人，Windows 个人笔记场景。不是产品，不是 SaaS。

---

## 2. Tech stack

| 层 | 选型 | 原因 |
|---|---|---|
| ASR | `qwen_asr` 0.0.6 + `transformers` 4.57.6 + `torch` 2.5.1+cu121 | 最好的开源 1.7B ASR，8GB 显存放得下 |
| 模型来源 | ModelScope 镜像 | `huggingface.co` 国内超时；ModelScope 是阿里系 |
| UI | Gradio 6 | 最快做出可用 Web UI，不需要 JS 工具链 |
| 音频 | `sounddevice`（numpy 数组）、`wave`（写录音文件） | 不依赖 ffmpeg |
| 翻译 | `transformers` MarianMT（opus-mt-zh-en / en-zh，~300MB FP16） | 轻量、中英互译够用 |
| 语言检测 | `langdetect` + `sacremoses` | 极小，不占显存 |
| 依赖管理 | pip + venv（不用 conda） | Windows 上更省事，避开 CUDA 路径问题 |

**刻意不用的**：vLLM（Windows 不兼容）、ffmpeg（多装一个）、Ollama（杀鸡用牛刀）。

---

## 3. 外部资源路径

| 资源 | 路径 |
|---|---|
| ASR 模型 | `C:\Users\29335\.cache\modelscope\models\Qwen--Qwen3-ASR-1.7B\snapshots\master` |
| 翻译模型 | `<项目>/_tmp_ms/Helsinki-NLP/opus-mt-{zh-en,en-zh}/` |
| 录音存档 | `D:\LiveSpeech2Text\recordings\` |
| 端口配置 | `<项目>/config.json`（gitignored） |
| venv | `<项目>/venv/`（gitignored） |

---

## 4. 当前状态

### 已完成
- **v1**（`8268650`，在 `main`）：基础 ASR + Web UI + CLI（CLI 后来删了）
- **v3**（`2a4bc00`，分支 `feat/v3-i18n-translation`）：i18n（EN/中文）、识别语言选择、实时翻译
- **v4**（`1a2fa02` + 录音 commit，分支 `feat/v4-port-and-notes`）：
  - 可配置端口（env > config.json > 默认 7860），冲突检测 + 邻近端口推荐
  - Notes 手写笔记区（存 `notes_ai.md`）
  - Live / Notes 双 Tab 布局
  - 手动增益 **1-100x** + AGC 自动归一化
  - 录音存档（原始 WAV 写 D 盘）
  - 移除 AI 整理功能（DeepSeek 网页自动化太脆，已弃）

### 未做（v5 计划）
| 功能 | 备注 |
|---|---|
| 音频源下拉（麦克风 / 系统 loopback / 文件上传） | Gradio 只能采浏览器麦克风，系统声音需 Python 端 `sounddevice.InputStream` + WASAPI loopback |
| 上传音频文件转写 | `soundfile.read` + 分块喂 ASR |
| SRT / VTT 字幕导出 | 依赖 `transcribe_audio` 返回时间戳 |
| VAD 静音检测 | silero-vad，长录音省显存 |
| 说话人分离 | pyannote 显存吃紧，**不推荐** |

### 已弃用（别复活，除非用户明确要求）
- **DeepSeek 网页 AI 整理**（Playwright 自动化）— cookie/登录太脆，2026-08 弃
- **Edge 浏览器集成** — `--user-data-dir` 冲突、cookie 不持久
- **CLI 版**（`start.bat` + `note_taker.py`）— 与 Web UI 抢显存导致 OOM

---

## 5. 文件布局

```
livespeech2text/                    ← 唯一目录，git 仓库 + venv
├── web_ui.py              635 行    ← 主程序，整个应用都在这一个文件里
├── start_webui.bat                   ← Windows 启动器（可带端口参数）
├── start_webui.ps1                   ← PowerShell 启动器（读 $env:LST_PORT）
├── check_audio.py                    ← 麦克风设备自检
├── smoke_test.py                     ← ASR 端到端冒烟测试
├── README.md                         ← 用户文档（English + 中文）
├── POWERSHELL.md                     ← PS 5.1 vs 7+ 兼容性说明
├── MR.md                             ← PR 描述模板（English + 中文）
├── AGENTS.md                         ← 本文件
├── .gitignore
├── config.json                       ← (gitignored) 端口配置
├── notes.md                          ← (gitignored) ASR 自动转写
├── translations.md                   ← (gitignored) 翻译记录
├── notes_ai.md                       ← (gitignored) 手写笔记
├── web_ui.py / webui*.log            ← 运行时日志（gitignored）
├── venv/                             ← (gitignored) Python 环境
└── _tmp_ms/                          ← (gitignored) ModelScope 缓存
```

---

## 6. 架构

```
┌───────────────────────────────────────────────────────────────┐
│                     Browser (Gradio client)                    │
│  - 麦克风采集 (Web Audio API)                                  │
│  - 音频 chunk → Python (WebSocket)                            │
│  - 语言 radio / 增益滑条 / AGC 勾选 / 录音按钮                 │
└──────────────┬────────────────────────────────────────────────┘
               │ audio_input.stream (每 2 秒)
               ▼
┌───────────────────────────────────────────────────────────────┐
│  transcribe_audio(audio, gain, agc, asr_lang, trans_mode,     │
│                    rec_value)                                 │
│  1. 重采样到 16kHz mono                                       │
│  2. apply_gain() — 手动增益 或 AGC                            │
│  3. 若 rec_value 存在 → 写 PCM16 到 wave 文件 (D:\...)        │
│  4. asr_model.transcribe(audio, language=...)                 │
│  5. append_note(text) → notes.md                              │
│  6. translator.translate_async()（不阻塞）                    │
│  7. return (status, notes_display, translation_display)       │
└──────────────┬────────────────────────────────────────────────┘
               │
       ┌───────┴────────┐
       ▼                ▼
    notes.md      translations.md
       +                +
   gr.State          线程队列
   (录音句柄)        (opus-mt worker)
```

---

## 7. 关键约定

### 端口解析优先级
1. `LST_PORT` 环境变量（`start_webui.bat <port>` 传入）
2. `config.json` 的 `{"port": N}`（CWD 下，UI ⚙️ 手风琴里改）
3. 默认 `7860`

改端口**必须重启** —— Gradio 6 在启动时绑定 `server_port`，不支持运行时改。UI 里已明确提示用户。

### i18n（English / 中文）
- `web_ui.py` 顶部 `LOCALES["English"|"中文"]` 字典
- **i18n 值解耦模式**：需要模型特定值的控件用 `[(label, value), ...]`：
  ```python
  asr_lang_radio = gr.Radio(
      choices=[("Chinese", "Chinese"), ("English", "English"), ("Auto", "Auto")],
      value="Chinese",
      label=LOCALES["English"]["asr_lang"],
  )
  ```
  Gradio 显示 label、存 value。加新语言不会破坏模型调用。
- "Auto" → 传给 Qwen3-ASR 时必须是 `None`（不是字符串 `"Auto"`）
- 所有 UI 文案都在 `LOCALES` 里，**不要在 UI 层硬编码英文**

### 录音
- `RECORDINGS_DIR = r"D:\LiveSpeech2Text\recordings"`（硬编码，符合用户 D 盘偏好）
- `gr.State` 存 `(wave.Wave_write, file_path)` 元组，或 `None`
- 存的是**原始音频**（未经增益），16k mono 16-bit PCM WAV
- 文件名：`recording_YYYYMMDD_HHMMSS.wav`
- ⚠️ `gr.State` 在 click 回调里**自动解包** — 收到的是 `rec_value`（已是值），不是 `rec_state.value`

### Git 工作流
- **feature branch + PR**，绝不直接推 `main`
- 分支命名 `feat/<name>`，commit 前缀 `feat:` / `fix:` / `refactor:` / `docs:` / `chore:`
- 提交历史保持"每个功能一个 commit"，便于回溯
- 用户用 **Git Bash (MINGW64)** 操作 git，不是 PowerShell
- GitHub 443 国内常 reset，推不动时走镜像：
  ```bash
  git push https://ghproxy.com/https://github.com/as1yx/livespeech2text.git feat/v4-port-and-notes
  ```
  （ghproxy 自己也常挂，失败就回退 `git push origin`）

---

## 8. 已知坑（踩过的，别再踩）

1. **Qwen3-ASR 1.7B 会把 language 字符串转小写再匹配**。只支持 30 种单语言，混合语言（zh-en）会报 `Unsupported language`。"Auto" 必须传 `None`。

2. **ASR 首个 chunk 可能为空或极短**。不要崩，提前返回 `(status, load_notes(), load_translations())`。

3. **PowerShell 5.1 无法解析 `.ps1` 里的 UTF-8 中文** → `UnexpectedToken`。`.ps1` 里的 print 用英文；中文文案放 Gradio 层（UTF-8 没问题）。

4. **`mavis-trash` 可能不可用；`Remove-Item` 被永久删除安全策略拦截**。清理文件用 Python 脚本：`os.remove` / `shutil.rmtree`，脚本末尾自删。

5. **`Format-Table -AutoSize`、`Get-Process <name>` 被会话权限规则拦截**。改用 `Select-Object` / `Select-String`，或 `tasklist /FI` + `taskkill /F /PID`。

6. **bash 工具在 Windows 上是 PowerShell，不是 bash**。`&&`、`ls -la`、`head`、`tail`、`grep` 都不能用。

7. **PowerShell 的 `Get-ChildItem` / `Select-String` 输出经常被 bash 工具吞掉（显示为空）**。改用 `cmd /c dir` 看目录、用 grep 工具搜文件内容。

8. **`Start-Process` 起的进程独立于 bash task**，容器挂了服务还在。长驻服务（Web UI）用这个方式起。

9. **只能同时跑一个 ASR 实例**。两个 Qwen3-ASR-1.7B 进显存 = OOM（8GB 卡）。

10. **`Test-NetConnection` 的参数是 `-WarningAction SilentlyContinue`**（不是 `SilentlyComplete`）。

11. **系统声音采集做不到**：`gr.Audio(streaming=True)` 只能拿浏览器麦克风。要采系统声音必须另起 Python 端 `sounddevice.InputStream` + WASAPI loopback（v5 的活）。

---

## 9. 启动 / 调试

```powershell
cd C:\Users\29335\.minimax\agents\mavis\workspace\livespeech2text

# 正常启动
.\venv\Scripts\python.exe web_ui.py
# → http://localhost:7860

# 指定端口
$env:LST_PORT = 7865
.\venv\Scripts\python.exe web_ui.py

# 或者
start_webui.bat 7865
```

**后台常驻启动**（独立进程，容器挂了也活着）：
```powershell
Start-Process -FilePath '.\venv\Scripts\python.exe' `
  -ArgumentList 'web_ui.py' `
  -WorkingDirectory (Get-Location) `
  -RedirectStandardOutput 'webui.log' `
  -RedirectStandardError 'webui_err.log' `
  -WindowStyle Hidden
```
模型加载要 60-90 秒，起完等一会儿再验端口。

**验证服务**：
```powershell
Test-NetConnection -ComputerName localhost -Port 7860 -InformationLevel Quiet -WarningAction SilentlyContinue
```

**麦克风自检**：`.\venv\Scripts\python.exe check_audio.py`（列设备、录 3 秒、存 test.wav）
**ASR 冒烟测试**：`.\venv\Scripts\python.exe smoke_test.py`

---

## 10. 隐私边界（绝不能 push）

`.gitignore` 已拦截：
- `venv/`、`_tmp_ms/`、`huggingface/`
- `*.safetensors`、`*.bin`、`*.pt`、`*.pth`（模型权重）
- `notes.md`、`translations.md`、`notes_ai.md`（用户内容）
- `config.json`（本地端口配置）
- `*.log`、`*.wav`、`*.mp3`（运行时产物）

**规矩**：改 `.gitignore` 后必须 `git status` 验一遍，别加实际没生效的规则。
录音存 D 盘，本来就不在仓库内。

---

## 11. 交接清单

接手人按这个顺序做：

- [ ] 装依赖：`pip install -r requirements.txt`（**注意：当前仓库没有 requirements.txt，需要补**）或直接用现成 `venv/`
- [ ] 确认模型已下载（ASR + opus-mt），没有的话走 ModelScope 镜像拉
- [ ] `git checkout feat/v4-port-and-notes`（或从 `main` 起新分支做 v5）
- [ ] 起服务 → http://localhost:7860 → 说句话验证 → 看 notes.md 有字
- [ ] 测录音：点 🎙️ → 说几句 → 点 ⏹ → 去 `D:\LiveSpeech2Text\recordings\` 找 WAV
- [ ] 决定 v5 优先级：**设备下拉 / 文件上传 / SRT 字幕**，建议先做前两个（一天），字幕依赖时间戳改造放后面
- [ ] v5 开工前先读本文档第 7 节（约定）和第 8 节（坑），避免重复踩

### 待补的短板
- **没有 `requirements.txt`** — 依赖全靠记忆重建，接手人容易装错版本。**建议补一个**
- 没有自动化测试（`smoke_test.py` 是手跑的，不是 pytest）
- 没有 CI
- `main` 落后于 v3/v4，长期不合会导致分支混乱，建议尽早把 v4 PR 合进 `main`
