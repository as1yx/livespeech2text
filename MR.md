# feat: LiveSpeech2Text v4 - configurable port, Notes section, tabbed UI

## TL;DR

- **Port selection** — three priority sources (`LST_PORT` env > `config.json` > default 7860), with an in-UI ⚙️ "Port settings" accordion that writes to `config.json`. Change port without editing code.
- **Notes section** — a new textbox + Save button in the right column that writes to `notes_ai.md`, designed as the landing pad for the future real-time AI organization feature.
- **Tabbed UI** — the right column is now split into two tabs: `🎤 Live / 实时` (existing ASR + 实时笔记 + 翻译) and `📝 Notes / 笔记` (new manual notes + AI 整理 hint).
- **AI 整理 hint** — top of the Notes tab explains how to run `ai_organize.py` (Playwright + DeepSeek web) locally, with step-by-step and a "what if the web AI is gone" section. The actual scripts live outside the repo (gitignored).
- **`POWERSHELL.md`** — a 3.7 KB standalone doc with PS 5.1 vs PS 7+ compatibility, how to upgrade via `winget`, and a drop-in replacement `start_webui.bat` body that prefers `pwsh.exe`.
- **`config.json`** — new optional config file, gitignored (user-portable port setting).
- `start_webui.bat` accepts the port as `%1`; `start_webui.ps1` reads `LST_PORT` from env and threads it to the Python child.

## Why

After v3 shipped with i18n + real-time translation, the user hit three practical pain points during real use and asked for two future-proofing hooks:

1. **Pain point: 7860 was hard-coded** — every port conflict required editing `web_ui.py`. They wanted "no-code" port selection: ideally from the UI, with env var and config file as fallbacks.
2. **Pain point: no place for manual notes** — `notes.md` is auto-appended by ASR. They wanted somewhere to paste a meeting agenda, write down a thought, or pre-seed a discussion. They also wanted a stable UI location for the future real-time web-based AI organizer to plug into.
3. **Pain point: PowerShell 5.1 mojibake** — v3's PR description already mentioned this; v4 ships a proper upgrade doc.
4. **Future hook: AI 整理入口** — the user explicitly asked to "support entering an API on the page to auto-organize notes, defaulting to the web version" (方案二: 浏览器自动化). v4 lays the file/UI groundwork + a `### 🤖 AI 整理` markdown block in the Notes tab; actual `ai_organize.py` lives outside the repo (gitignored) and is invoked from the terminal.
5. **Future hook: clearer page structure** — the right column was getting busy (实时笔记 + 翻译 + 笔记 + AI 整理). Splitting into two tabs makes the Live/Notes dichotomy obvious.

## What Changed

### New

- **`config.json`** — runtime config, created on first port change via the UI. Format: `{"port": 7860}`. **Gitignored** by default (each user picks their own port).
- **UI: "⚙️ Port settings" accordion** (top of page, folded) — `gr.Number` (1024-65535) + primary "Apply & Save to config.json" button. In-place validation: rejects out-of-range, rejects in-use (suggests next free), rejects no-op, confirms save + tells the user to restart.
- **UI: "🎤 Live / 实时" tab** — the existing ASR + 实时笔记 (`notes.md`) + 翻译 (`translations.md`), moved into a `gr.TabItem` with `id="live"`. Notes/Translation textboxes grew from 20/15 to 25/12 lines to use the freed vertical space.
- **UI: "📝 Notes / 笔记" tab** — new `gr.TabItem` with `id="notes"`. Contains:
  - A `### Manual notes` intro explaining this is for the user's own content (not touched by ASR)
  - A 25-row `gr.Textbox` for manual notes, with placeholder "AI 整理功能即将上线 — 在此输入或粘贴笔记,点 Save 保存"
  - A "Save" primary button + status markdown that writes to `notes_ai.md`
  - A `### 🤖 AI 整理 (DeepSeek 网页版)` markdown block with 操作步骤 / 注意事项 / 备用方案
- **`POWERSHELL.md`** — 3.7 KB standalone doc: required version (PS 7+ recommended), how to check, `winget install Microsoft.PowerShell`, drop-in `.bat` body that prefers `pwsh.exe`, PS 5.1 quirks (BOM, Chinese paths, `chcp 65001`).
- **`notes_ai.md`** — runtime output (gitignored), created automatically with a header on first run; saves only on Save-button click, not auto-on-keystroke.
- **i18n** — both English and 中文 `LOCALES` dicts got: `tab_live`, `tab_notes`, `notes_ai_intro`, `ai_organize_hint`. `switch_ui()` updates the new tab labels and the AI hint when toggling UI language.

### Changed

- **`web_ui.py`** (v3 → v4, +12 KB):
  - `import json`, `import socket`
  - `load_config()` / `save_config()` helpers
  - `_parse_port()` — three-source priority: LST_PORT env > config.json > default 7860
  - `_is_port_in_use()` and `_suggest_port()` for startup validation and the Apply flow
  - `USER_NOTES_PATH = "notes_ai.md"` + `load_user_notes()` / `save_user_notes()`
  - `clear_files()` no longer clears `notes_ai.md` (it's a separate, manually-managed file)
  - `build_ui()` wrapped the right column in `gr.Tabs` with two `gr.TabItem`s
  - `switch_ui()` also resets `notes_ai_intro` and `ai_organize_hint` markdown on language toggle
  - `__main__` block now calls `_parse_port()` and `_is_port_in_use()` before `app.launch()` with a clear "Try: set LST_PORT=XXXX" hint if the chosen port is busy
  - Internal version label: "v3" → "v4" in the startup banner print
- **`start_webui.bat`** (398 B) — added `if not "%1"=="" set LST_PORT=%1` so `start_webui.bat 8080` works.
- **`start_webui.ps1`** (4.7 KB, was 3.9 KB) — reads `$env:LST_PORT` at the top, threads it into `ProcessStartInfo.EnvironmentVariables`, replaced hard-coded `7860` in port checks and the browser URL.
- **`.gitignore`** — added `notes_ai.md`, `config.json` (user-portable), `ai_organize.py` (local-only, the actual DeepSeek web driver), `test_deepseek.py` (改版检测), `.deepseek_browser_data/` (Playwright persistent context for DeepSeek login), `deepseek_test_screenshot.png` (test artifact).
- **`README.md`** — English + Chinese "限制" sections now link to `POWERSHELL.md` for the PS upgrade path.

### Removed

Nothing. (v3 already removed the CLI.)

## How to Test

### Prerequisites (already met on the original dev machine)
- NVIDIA GPU 8 GB+ (RTX 3060 / 4060 or better)
- Python 3.12
- Windows 10 / 11
- v3 deps (`langdetect`, `sacremoses`) — no new Python deps in v4

### 1. Run (no env var, no config = default 7860)
```cmd
start_webui.bat
```
Browser opens to `http://localhost:7860`. Top banner should read:
> 🟢 **Server Port:** `7860` (config.json 端口=7860)

You should see two tabs at the top: `🎤 Live / 实时` (default) and `📝 Notes / 笔记`.

### 2. Test the new Notes tab
1. Click the `📝 Notes / 笔记` tab
2. You should see:
   - `### Manual notes` intro
   - `### 🤖 AI 整理 (DeepSeek 网页版)` instructions
   - A textbox with the AI 整理 placeholder
   - A blue `Save` button
3. Type a few lines, click **Save** → status should show "Saved to notes_ai.md"
4. Verify `notes_ai.md` content

### 3. Test port change via the UI
1. Back in the Live tab (or anywhere), open the **⚙️ Port settings** accordion
2. Change `7860` to `8080` (or any free port in 1024-65535)
3. Click **Apply & Save to config.json**
4. Status should read:
   > ✅ 已保存。下次启动会用端口 **8080**。关闭本窗口,重新双击 `start_webui.bat` 生效。提示: 启动脚本可以传端口参数盖过 config.json: `start_webui.bat 8080`
5. Verify `config.json` was written (and is NOT tracked by git):
   ```cmd
   type config.json
   :: {"port": 8080}
   git status    :: config.json should not appear (gitignored)
   ```
6. Close browser tab + Ctrl+C the PowerShell window
7. Re-launch with `start_webui.bat` — banner should now show port `8080`

### 4. Test port change via env var (overrides config.json)
```cmd
set LST_PORT=9090
start_webui.bat
```
Banner: `🟢 Server Port: 9090 (环境变量 LST_PORT=9090)`

### 5. Test port conflict detection
- Apply a port that something else is already listening on → "❌ 端口 X 已被占用,试试 Y"
- Apply `1234` or `99999` → "❌ 端口 X 越界,需要 1024-65535"

### 6. Test the ASR + translation still works (regression)
- Click the Live tab → record something → text appears in 实时笔记
- Toggle translation mode → translation shows up below

### 7. Test UI language toggle
- Switch `UI Language` to 中文 → all labels (including tab labels, AI 整理 hint) re-render

## File Layout

```
livespeech2text/
├── web_ui.py              # v4, i18n + translation + port + notes + tabbed UI
├── start_webui.bat        # double-click launcher; accepts port as %1
├── start_webui.ps1        # PowerShell with spinner; reads LST_PORT
├── check_audio.py         # lists available input devices
├── smoke_test.py          # one-shot ASR sanity check
├── config.json            # NEW, runtime config (port); created on first Apply, gitignored
├── POWERSHELL.md          # NEW, PS 5.1 vs PS 7+ upgrade guide
├── MR.md                  # this file
├── README.md              # English (top) + Chinese (below); points to POWERSHELL.md
├── .gitignore             # excludes venv/, *.log, *.safetensors, notes*.md, _tmp_ms/, huggingface/, config.json
├── notes.md               # git-ignored, ASR runtime output
├── translations.md        # git-ignored, translation runtime output
├── notes_ai.md            # git-ignored, manual notes runtime output
└── venv/                  # git-ignored, Python env with all deps (~5 GB)

# Local-only (gitignored, not pushed):
# ├── ai_organize.py       # Playwright driver for DeepSeek web
# ├── test_deepseek.py     # 改版检测
# ├── .deepseek_browser_data/  # Playwright persistent context (DeepSeek login)
# └── deepseek_test_screenshot.png
```

## Known Limitations

- **First-time model load is slow** — Qwen3-ASR-1.7B is 4.5 GB; first launch 30-70 s on NVMe, 5-10 s on subsequent.
- **Only one ASR instance fits in 8 GB VRAM** — running the v4 Web UI alongside a leftover v3 process OOMs. Kill the old one before starting v4.
- **Web UI is 2-second segmented, not sub-second streaming** — see v3 PR notes; WSL2 + vLLM remains out of scope.
- **opus-mt quality is decent but not SOTA** — code-switched Chinese-English sometimes loses nuance. Swap the Translator class for a larger model if needed.
- **Port change requires restart** — Gradio 6 binds `server_port` at `app.launch()` and doesn't support rebinding at runtime. v4 saves the user's choice and shows a clear "restart to apply" message. An in-process `app.close()` + `app.launch(new_port)` was tried and abandoned (Gradio's internal queue races).
- **No speaker diarization** — overlapping speakers still become a single muddled transcript.
- **Windows PowerShell 5.1 renders UTF-8 Chinese as mojibake** — see `POWERSHELL.md` for the upgrade path. Gradio UI is fine.
- **AI 整理 is local-only by design** — the user explicitly asked for "no upload to GitHub". `ai_organize.py` + `test_deepseek.py` + the Playwright browser data are all gitignored. The web UI's Notes tab has a markdown block explaining the manual workflow and what to do if DeepSeek's web UI breaks.

## Out-of-scope (deferred)

- Real-time web-based AI organization of the new Notes section (this PR lays the UI + file groundwork; the AI integration is a follow-up)
- In-page API-key input (the user said "default to the web version" — so we keep `ai_organize.py` as the entry point and don't put a key field in the UI yet)
- WSL2 + vLLM for true streaming
- Speaker diarization (pyannote.audio)
- Translation glossary / custom term dictionary
- Exporting notes to SRT / VTT
- Tauri / Electron desktop wrapper

## Rollback

All changes are in `web_ui.py`, `start_webui.bat`, `start_webui.ps1`, `README.md`, `MR.md`, `.gitignore`. New files: `POWERSHELL.md`. Reverting is a single `git revert` on the PR commit. `config.json` and `notes_ai.md` are gitignored and stay local.

## Checklist for the reviewer

- [ ] Two tabs visible at the top: `🎤 Live / 实时` (default) and `📝 Notes / 笔记`
- [ ] Notes tab has the `### Manual notes` intro, the `### 🤖 AI 整理 (DeepSeek 网页版)` block, the textbox, and the Save button
- [ ] Saving in the Notes tab writes to `notes_ai.md` (gitignored)
- [ ] ASR + translation still work in the Live tab (no regression)
- [ ] Switching UI language re-renders the tab labels and the AI hint
- [ ] `config.json` does not exist on a fresh checkout; it appears only after the first port change via the UI
- [ ] Setting `LST_PORT=8080` and starting `start_webui.bat` (no `config.json`) makes the banner show 8080
- [ ] Setting `LST_PORT=8080` and having `config.json` with `"port": 9090` makes the banner show 8080 (env wins)
- [ ] Removing `LST_PORT` and having `config.json` with `"port": 9090` makes the banner show 9090
- [ ] Removing both makes the banner show 7860
- [ ] ⚙️ Port settings accordion exposes a number input and an Apply button
- [ ] Applying a port already in use shows "❌ 已被占用" and does NOT touch `config.json`
- [ ] Applying a port out of range shows "❌ 越界" and does NOT touch `config.json`
- [ ] Applying a valid free port writes `config.json` and shows the restart hint
- [ ] Restarting after Apply lands on the new port
- [ ] `notes.md` and `translations.md` continue to update as before
- [ ] `notes_ai.md` is NOT touched by ASR
- [ ] `POWERSHELL.md` exists at the project root and is linked from both English and Chinese sections of `README.md`
- [ ] `config.json` is gitignored
- [ ] All v3 functionality (i18n, recognition language, translation) still works

---

# 中文版

## TL;DR（简述）

- **端口选择** — 三档优先级：`LST_PORT` 环境变量 > `config.json` > 默认 7860。页面顶部加了 ⚙️ Port settings 折叠区，改端口不用动代码。
- **笔记区** — 右栏新增 textbox + Save 按钮，写到 `notes_ai.md`，为以后接实时 AI 整理功能打底。
- **Tab 拆分** — 右栏拆成两个 tab：`🎤 Live / 实时`（现有 ASR + 实时笔记 + 翻译）和 `📝 Notes / 笔记`（新的手动笔记 + AI 整理 hint）。
- **AI 整理 hint** — Notes tab 顶部说明怎么本地跑 `ai_organize.py`（Playwright + DeepSeek 网页版），含操作步骤和"网页 AI 不能用了怎么办"。脚本本身在仓库外（.gitignore）。
- **`POWERSHELL.md`** — 3.7 KB 独立文档，讲 PS 5.1 vs PS 7+ 兼容性、`winget` 升级方法、`.bat` 改用 `pwsh.exe` 的写法。
- **`config.json`** — 新增可选配置文件，gitignore 了（用户自带端口配置）。
- `start_webui.bat` 接受端口作为 `%1`；`start_webui.ps1` 从 `LST_PORT` 环境变量读，传给 Python 子进程。

## Why（为什么要做）

v3 上线了 i18n + 实时翻译之后，用户在实际使用中遇到三个痛点，并要求两个未来扩展的口子：

1. **痛点：7860 写死了** — 每次端口冲突都得去改 `web_ui.py`。用户要"不改代码就能改端口"：理想是 UI 改，环境变量和配置文件做后备。
2. **痛点：没有手动笔记的地方** — `notes.md` 是 ASR 自动追加的，没地方贴会议议程、随手记、或者提前准备一段讨论。用户也想给未来的实时网页 AI 整理留个稳定的 UI 入口。
3. **痛点：PowerShell 5.1 中文乱码** — v3 的 PR 描述里提过；v4 直接给一份完整的升级文档。
4. **未来扩展：AI 整理入口** — 用户明确要求"页面支持输入 API 自动整理笔记，默认还是接网页版"（方案二：浏览器自动化）。v4 做了 UI/文件的底子 + Notes tab 里的 `### 🤖 AI 整理` markdown 块；`ai_organize.py` 实际在仓库外（gitignore），从终端调用。
5. **未来扩展：页面结构更清晰** — 右栏内容越来越多（实时笔记 + 翻译 + 笔记 + AI 整理），拆成两个 tab 让"实时"和"笔记"的分工一目了然。

## What Changed（改了什么）

### 新增

- **`config.json`** — 运行时配置，第一次在 UI 改端口时自动生成。格式：`{"port": 7860}`。**默认 gitignore**（每个用户用自己的端口）。
- **UI: "⚙️ Port settings" 折叠区**（页面顶部，默认折叠）— `gr.Number`（1024-65535）+ 主按钮 "Apply & Save to config.json"。原地校验：拒绝超界、拒绝被占用（建议下一个空闲）、拒绝无变化、确认保存并提示用户重启。
- **UI: "🎤 Live / 实时" tab** — 原来的 ASR + 实时笔记（`notes.md`）+ 翻译（`translations.md`），包进 `gr.TabItem`（`id="live"`）。笔记/翻译框从 20/15 行扩到 25/12 行（因为没 AI 整理占空间了）。
- **UI: "📝 Notes / 笔记" tab** — 新的 `gr.TabItem`（`id="notes"`）。包含：
  - `### Manual notes` 说明这是用户自己的笔记（ASR 不会动它）
  - 25 行的 `gr.Textbox`，占位符 "AI 整理功能即将上线 — 在此输入或粘贴笔记,点 Save 保存"
  - 蓝色 Save 主按钮 + 状态 markdown，写到 `notes_ai.md`
  - `### 🤖 AI 整理 (DeepSeek 网页版)` markdown 块，含 操作步骤 / 注意事项 / 备用方案
- **`POWERSHELL.md`** — 3.7 KB 独立文档：推荐 PS 7+、怎么查版本、`winget install Microsoft.PowerShell`、`.bat` 改用 `pwsh.exe` 的现成代码、PS 5.1 的坑（BOM、中文路径、`chcp 65001` 冲突）。
- **`notes_ai.md`** — 运行时输出（gitignore），首次启动自动建好带 header；只在点 Save 时写入，不是边输入边自动存。
- **i18n** — 英文和中文 `LOCALES` 都加了：`tab_live`、`tab_notes`、`notes_ai_intro`、`ai_organize_hint`。`switch_ui()` 切语言时也会更新新加的 tab 标签和 AI 提示。

### 修改

- **`web_ui.py`**（v3 → v4，+12 KB）：
  - 加 `import json`、`import socket`
  - `load_config()` / `save_config()` 辅助函数
  - `_parse_port()` — 三档优先级：LST_PORT 环境变量 > config.json > 默认 7860
  - `_is_port_in_use()` 和 `_suggest_port()`，启动校验和 Apply 流程用
  - `USER_NOTES_PATH = "notes_ai.md"` + `load_user_notes()` / `save_user_notes()`
  - `clear_files()` 不再清 `notes_ai.md`（它是独立的手动文件）
  - `build_ui()` 把右栏包进 `gr.Tabs`，两个 `gr.TabItem`
  - `switch_ui()` 切语言时同时刷新 `notes_ai_intro` 和 `ai_organize_hint`
  - `__main__` 块调用 `_parse_port()` 和 `_is_port_in_use()`，端口被占时给 "Try: set LST_PORT=XXXX" 的提示
  - 内部版本号 "v3" → "v4"（启动 banner print）
- **`start_webui.bat`**（398 B）— 加了 `if not "%1"=="" set LST_PORT=%1`，支持 `start_webui.bat 8080`。
- **`start_webui.ps1`**（4.7 KB，原 3.9 KB）— 顶部读 `$env:LST_PORT`，传给 `ProcessStartInfo.EnvironmentVariables`，端口检查和浏览器 URL 里的硬编码 `7860` 全部替换。
- **`.gitignore`** — 加了 `notes_ai.md`、`config.json`（用户数据）、`ai_organize.py`（本地 DeepSeek 驱动）、`test_deepseek.py`（改版检测）、`.deepseek_browser_data/`（Playwright 持久化 DeepSeek 登录态）、`deepseek_test_screenshot.png`（测试产物）。
- **`README.md`** — 英文和中文的"限制"章节都加了 `POWERSHELL.md` 链接。

### 删除

没有。v3 的时候 CLI 已经删了。

## 怎么测

### 前置条件（开发机上已经满足）
- NVIDIA GPU 8 GB+（RTX 3060 / 4060 或更高）
- Python 3.12
- Windows 10 / 11
- v3 的依赖（`langdetect`、`sacremoses`）— v4 没加新 Python 依赖

### 1. 直接跑（无环境变量、无 config = 默认 7860）
```cmd
start_webui.bat
```
浏览器自动开 `http://localhost:7860`。顶部 banner 应该显示：
> 🟢 **Server Port:** `7860` (config.json 端口=7860)

应该看到两个 tab 在顶部：`🎤 Live / 实时`（默认）和 `📝 Notes / 笔记`。

### 2. 测新 Notes tab
1. 点 `📝 Notes / 笔记` tab
2. 应该看到：
   - `### Manual notes` 说明
   - `### 🤖 AI 整理 (DeepSeek 网页版)` 操作指南
   - 文本框有 AI 整理占位符
   - 蓝色 Save 按钮
3. 输几行字 → 点 **Save** → 状态显示 "Saved to notes_ai.md"
4. 验证 `notes_ai.md` 内容

### 3. 测 UI 改端口
1. 回到 Live tab（或者任何地方都行），打开 **⚙️ Port settings** 折叠区
2. 把 `7860` 改成 `8080`（或 1024-65535 任意空闲端口）
3. 点 **Apply & Save to config.json**
4. 状态显示：
   > ✅ 已保存。下次启动会用端口 **8080**。关闭本窗口,重新双击 `start_webui.bat` 生效。提示: 启动脚本可以传端口参数盖过 config.json: `start_webui.bat 8080`
5. 验证 `config.json` 写好了（且**没**被 git 跟踪）：
   ```cmd
   type config.json
   :: {"port": 8080}
   git status    :: config.json 不应出现（已 gitignore）
   ```
6. 关浏览器 tab + Ctrl+C 那个 PowerShell 窗口
7. 重启 `start_webui.bat` — banner 应该显示 8080

### 4. 测环境变量覆盖 config
```cmd
set LST_PORT=9090
start_webui.bat
```
Banner：`🟢 Server Port: 9090 (环境变量 LST_PORT=9090)`

### 5. 测端口冲突检测
- Apply 一个被占的端口 → "❌ 端口 X 已被占用,试试 Y"
- Apply `1234` 或 `99999` → "❌ 端口 X 越界,需要 1024-65535"

### 6. 回归测（ASR + 翻译不能坏）
- Live tab → 录音 → 文字进实时笔记
- 切翻译模式 → 翻译出在下框

### 7. 切语言
- 把 UI Language 切到 中文 → 所有标签（包括 tab、🤖 AI 整理 hint）应该跟着换

## 文件结构

```
livespeech2text/
├── web_ui.py              # v4, i18n + 翻译 + 端口 + 笔记 + tab 拆分
├── start_webui.bat        # 双击启动；接受 %1 端口参数
├── start_webui.ps1        # PowerShell 加载动画；读 LST_PORT
├── check_audio.py         # 列出可用音频输入设备
├── smoke_test.py          # ASR 单次冒烟测试
├── config.json            # 新增,运行时配置(端口);首次 Apply 时生成,gitignore
├── POWERSHELL.md          # 新增,PS 5.1 vs PS 7+ 升级指南
├── MR.md                  # 本文件
├── README.md              # 英文(上)+ 中文(下);指向 POWERSHELL.md
├── .gitignore             # 排除 venv/、*.log、*.safetensors、notes*.md、_tmp_ms/、huggingface/、config.json
├── notes.md               # gitignore,ASR 实时输出
├── translations.md        # gitignore,翻译输出
├── notes_ai.md            # gitignore,手动笔记
└── venv/                  # gitignore,Python 环境(~5 GB)

# 本地私有(gitignore,不进仓库):
# ├── ai_organize.py       # Playwright 驱动 DeepSeek 网页
# ├── test_deepseek.py     # 改版检测
# ├── .deepseek_browser_data/  # Playwright 持久化 DeepSeek 登录
# └── deepseek_test_screenshot.png
```

## 已知限制

- **首次模型加载慢** — Qwen3-ASR-1.7B 4.5 GB；首次 30-70s，之后 5-10s
- **8GB 显存只能跑一个 ASR 实例** — v3 和 v4 不能同时跑，OOM
- **Web UI 是 2 秒分段流式，不是子秒级** — 真正的字级流式要 WSL2 + vLLM
- **opus-mt 翻译质量一般** — 中英混合偶尔丢细节，换大模型直接改 Translator 类
- **改端口要重启** — Gradio 6 在 `app.launch()` 时绑端口，运行时改不了
- **不做说话人分离** — 多人混说会糊
- **Windows PS 5.1 中文乱码** — 看 `POWERSHELL.md` 升级
- **AI 整理故意只本地用** — 用户明确说"不上传 GitHub"；`ai_organize.py` + `test_deepseek.py` + 浏览器数据全 gitignore

## 不做（deferred）

- 实时网页版 AI 整理（本 PR 只铺 UI 和文件的底子，AI 集成是后续）
- 页面内 API key 输入（用户说"默认接网页版"，所以 ai_organize.py 仍走终端入口，没把 key 字段放 UI）
- WSL2 + vLLM 真流式
- 说话人分离（pyannote.audio）
- 翻译术语表 / 自定义词典
- 导出 SRT / VTT 字幕
- Tauri / Electron 桌面壳

## 回滚

所有改动都在 `web_ui.py`、`start_webui.bat`、`start_webui.ps1`、`README.md`、`MR.md`、`.gitignore`。新文件 `POWERSHELL.md`。一次 `git revert` 即可。`config.json` 和 `notes_ai.md` 都在 gitignore，本地保留。

## Reviewer 自查清单

- [ ] 顶部两个 tab 可见：`🎤 Live / 实时`（默认）和 `📝 Notes / 笔记`
- [ ] Notes tab 有 `### Manual notes` 说明、`### 🤖 AI 整理 (DeepSeek 网页版)` 块、文本框、Save 按钮
- [ ] Notes tab 点 Save 写到 `notes_ai.md`（gitignore）
- [ ] Live tab 的 ASR + 翻译仍工作（没回归）
- [ ] 切语言时 tab 标签和 AI hint 都重新渲染
- [ ] `config.json` 默认不存在；首次 UI 改端口时才会出现
- [ ] 设 `LST_PORT=8080` 且没 `config.json` → banner 显示 8080
- [ ] 设 `LST_PORT=8080` + `config.json` 写 9090 → banner 显示 8080（环境变量优先）
- [ ] 没环境变量 + `config.json` 写 9090 → banner 显示 9090
- [ ] 都没 → banner 显示 7860
- [ ] ⚙️ Port settings 折叠区有数字输入框和 Apply 按钮
- [ ] Apply 被占的端口 → "❌ 已被占用" 且不写 `config.json`
- [ ] Apply 越界端口 → "❌ 越界" 且不写 `config.json`
- [ ] Apply 合法空闲端口 → 写 `config.json` + 提示重启
- [ ] 重启后端口生效
- [ ] `notes.md` 和 `translations.md` 仍正常更新
- [ ] `notes_ai.md` 不被 ASR 碰
- [ ] `POWERSHELL.md` 存在且 README 中英文都链了
- [ ] `config.json` 在 gitignore 里
- [ ] v3 所有功能（i18n、识别语言、翻译）仍工作
