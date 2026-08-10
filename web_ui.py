"""
LiveSpeech2Text Web UI v4
- v3: i18n, recognition language, real-time translation
- v4: configurable port (LST_PORT env var), Notes section for manual notes
"""

import os
import socket
import json
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

import gradio as gr
import numpy as np
import torch
import datetime
import threading
from queue import Queue
from concurrent.futures import ThreadPoolExecutor

# --- Constants ---
MODEL_DIR = r"C:\Users\29335\.cache\modelscope\models\Qwen--Qwen3-ASR-1.7B\snapshots\master"
TRANSLATION_MODEL_DIR = "./_tmp_ms"  # ModelScope cache
ZH_EN_MODEL = os.path.join(TRANSLATION_MODEL_DIR, "Helsinki-NLP", "opus-mt-zh-en")
EN_ZH_MODEL = os.path.join(TRANSLATION_MODEL_DIR, "Helsinki-NLP", "opus-mt-en-zh")
NOTES_PATH = "notes.md"
TRANSLATIONS_PATH = "translations.md"
USER_NOTES_PATH = "notes_ai.md"  # v4: user-typed notes (separate from ASR auto-notes)
SAMPLE_RATE = 16000
DEVICE = "cuda:0"

# --- Port selection (v4) ---
# Priority: LST_PORT env var > config.json > DEFAULT_PORT
DEFAULT_PORT = 7860
CONFIG_PATH = "config.json"


def load_config():
    """Load config.json; fall back to defaults on missing/corrupt."""
    defaults = {"port": DEFAULT_PORT}
    if not os.path.exists(CONFIG_PATH):
        return defaults
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        # 合并默认值
        merged = defaults.copy()
        if isinstance(cfg, dict):
            merged.update(cfg)
        # 校验 port
        try:
            p = int(merged.get("port", DEFAULT_PORT))
            if not (1024 <= p <= 65535):
                merged["port"] = DEFAULT_PORT
        except Exception:
            merged["port"] = DEFAULT_PORT
        return merged
    except Exception:
        return defaults


def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def _parse_port():
    """Resolve port: LST_PORT env > config.json > DEFAULT_PORT."""
    raw = os.environ.get("LST_PORT", "").strip()
    if raw:
        try:
            p = int(raw)
        except ValueError:
            cfg = load_config()
            return cfg["port"], f"⚠️ LST_PORT={raw!r} 不是数字,回退到 config.json 端口 {cfg['port']}"
        if not (1024 <= p <= 65535):
            cfg = load_config()
            return cfg["port"], f"⚠️ LST_PORT={p} 越界,回退到 config.json 端口 {cfg['port']}"
        return p, f"环境变量 LST_PORT={p}"
    # 没设 LST_PORT → 读 config.json
    cfg = load_config()
    return cfg["port"], f"config.json 端口={cfg['port']}"


def _is_port_in_use(port, host="127.0.0.1"):
    """Check if a TCP port is already in use."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.3)
    try:
        s.connect((host, port))
        s.close()
        return True
    except Exception:
        return False
    finally:
        try:
            s.close()
        except Exception:
            pass


def _suggest_port(start, max_tries=5):
    """Find next free port starting from `start`."""
    for p in range(start, start + max_tries):
        if not _is_port_in_use(p):
            return p
    return None


# Common port recommendations (displayed in UI)
COMMON_PORTS_HINT = """\
**常用端口 / Common ports:**
- `7860` — Gradio 默认,推荐首选
- `7861` `7862` `7863` — Gradio 自动回退,适合同时跑多个实例
- `8080` `8888` — 通用 Web 端口(可能与其他服务冲突)
- **避免**: 80/443(需管理员),< 1024(特权端口)

**改端口方法:** 启动前设环境变量 `LST_PORT=7861` (Windows: `set LST_PORT=7861`),然后重启服务。端口在运行时不可改。"""

# --- i18n ---
# Note: asr_lang_choices and trans_choices use [(label, value), ...] format
# so Gradio shows the label but stores the value.
#
# IMPORTANT: Qwen3-ASR 1.7B lowercases the language string before matching
# against its supported list. It only supports 30 single languages
# (Chinese, English, Cantonese, ...). It does NOT support mixed
# (e.g. Chinese-English) or "Auto" as a value. So:
#   - We pass `None` for "Auto" (model autodetects)
#   - We don't include any mixed options (model rejects them all)
LOCALES = {
    "English": {
        "subtitle": "**Speak naturally, pause 1-2 seconds.** Audio auto-segmented and recognized. Results save to `notes.md`.",
        "ui_lang": "UI Language",
        "asr_lang": "Recognition Language",
        "asr_lang_choices": [
            ("Chinese", "Chinese"),
            ("English", "English"),
            ("Auto (model detects)", "Auto"),
        ],
        "translation_mode": "Translation",
        "trans_choices": [
            ("Off", "off"),
            ("Mostly Chinese -> English", "mostly_zh_en"),
            ("Mostly English -> Chinese", "mostly_en_zh"),
            ("All -> English", "all_en"),
            ("All -> Chinese", "all_zh"),
        ],
        "gain_label": "Manual gain (1x - 100x)",
        "gain_info": "1=no change, 100=amplify 100x (mic too quiet? turn this up)",
        "agc_label": "Auto Normalize (AGC)",
        "agc_info": "Auto pull volume to target",
        "status": "Status (with RMS info)",
        "mic": "Microphone",
        "notes": "Notes (live, auto-saved to notes.md)",
        "translation": "Translation",
        "reload": "Reload",
        "clear": "Clear",
        "waiting": "Waiting...",
        "instructions": """---
**How to use:**
1. Click the microphone icon to start. Allow browser mic permission.
2. Speak, pause 1-2s. Text appears in the right Notes box.
3. Translation (if enabled) appears in the Translation box.

**If mic is too quiet:** increase Manual gain or enable AGC.""",
        "port_info": "Server Port",
        "user_notes": "Notes (manual)",
        "user_notes_placeholder": "Type or paste notes here. Click Save to write to notes_ai.md.",
        "user_notes_saved": "Saved to notes_ai.md",
        "user_notes_save": "Save",
        "tab_live": "🎤 Live / 实时",
        "tab_notes": "📝 Notes / 笔记",
        "notes_ai_intro": "### Manual notes\nThis area is for your own notes — anything you want to remember or refine.\n\n- Click **Save** to write to `notes_ai.md`\n- Not touched by the ASR stream (that's in the Live tab)",
    },
    "中文": {
        "subtitle": "**说话停顿 1-2 秒。** 音频自动分段识别,结果保存到 `notes.md`。",
        "ui_lang": "界面语言",
        "asr_lang": "识别语言",
        "asr_lang_choices": [
            ("中文", "Chinese"),
            ("英文", "English"),
            ("自动检测(模型自判)", "Auto"),
        ],
        "translation_mode": "翻译",
        "trans_choices": [
            ("不翻译", "off"),
            ("大量中文 → 英文", "mostly_zh_en"),
            ("大量英文 → 中文", "mostly_en_zh"),
            ("全部 → 英文", "all_en"),
            ("全部 → 中文", "all_zh"),
        ],
        "gain_label": "手动增益 (1x - 100x)",
        "gain_info": "1=不变,100=放大 100 倍(麦克风太小?调这个)",
        "agc_label": "自动归一化 (AGC)",
        "agc_info": "自动把音量拉到目标水平",
        "status": "状态(含 RMS 音量信息)",
        "mic": "麦克风",
        "notes": "笔记(实时更新,自动保存到 notes.md)",
        "translation": "翻译",
        "reload": "重新加载",
        "clear": "清空",
        "waiting": "等待开始...",
        "instructions": """---
**使用说明:**
1. 点麦克风图标开始录音,浏览器会请求麦克风权限(第一次点"允许")
2. 说话停顿 1-2 秒,文字出现在笔记框
3. 如果启用了翻译,翻译结果显示在翻译框

**声音小怎么办:** 调大"手动增益"或勾选"自动归一化(AGC)""",
        "port_info": "服务端口",
        "user_notes": "笔记（手动）",
        "user_notes_placeholder": "在此输入或粘贴笔记,点 Save 保存到 notes_ai.md",
        "user_notes_saved": "已保存到 notes_ai.md",
        "user_notes_save": "保存",
        "tab_live": "🎤 Live / 实时",
        "tab_notes": "📝 Notes / 笔记",
        "notes_ai_intro": "### 手动笔记\n这个区是给你自己写东西用的——任何想记住的、想整理的都可以。\n\n- 点 **Save** 自动存到 `notes_ai.md`\n- ASR 转写不会动这个文件(那是 Live tab 的事)",
    },
}


# --- Translator ---
class Translator:
    def __init__(self):
        self.models = {}  # direction -> (model, tokenizer)
        self.executor = ThreadPoolExecutor(max_workers=2)

    def _load(self, direction):
        if direction in self.models:
            return self.models[direction]
        model_path = {"zh-en": ZH_EN_MODEL, "en-zh": EN_ZH_MODEL}[direction]
        if not os.path.exists(model_path):
            return None
        from transformers import MarianMTModel, MarianTokenizer
        print(f"[translator] Loading {direction} model from {model_path}...")
        tokenizer = MarianTokenizer.from_pretrained(model_path)
        model = MarianMTModel.from_pretrained(model_path).to(DEVICE)
        # FP16 to save VRAM
        model = model.half()
        model.eval()
        self.models[direction] = (model, tokenizer)
        print(f"[translator] {direction} ready")
        return self.models[direction]

    def translate(self, text, direction):
        """Sync translate. Returns str."""
        if not text or not text.strip():
            return ""
        result = self._load(direction)
        if result is None:
            return f"[{direction} model not loaded]"
        model, tokenizer = result
        try:
            inputs = tokenizer([text], return_tensors="pt", padding=True, truncation=True, max_length=512).to(DEVICE)
            with torch.no_grad():
                outputs = model.generate(**inputs, max_length=512, num_beams=2, early_stopping=True)
            return tokenizer.decode(outputs[0], skip_special_tokens=True)
        except Exception as e:
            return f"[translate error: {e}]"

    def translate_async(self, text, direction, callback):
        """Async translate, calls callback(translated_str) on result."""
        def _run():
            result = self.translate(text, direction)
            callback(result)
        self.executor.submit(_run)


# --- Initialize models ---
print("=" * 60)
print("LiveSpeech2Text v4 - Web UI")
print("=" * 60)

print("[1/3] Loading ASR model...")
from qwen_asr import Qwen3ASRModel

asr_model = Qwen3ASRModel.from_pretrained(
    MODEL_DIR,
    dtype=torch.float16,
    device_map=DEVICE,
    max_inference_batch_size=1,
)
print("       ASR model ready")

print("[2/3] Initializing translator (loads on first use)...")
translator = Translator()
print("       Translator ready (lazy load)")

print("[3/3] All models ready")


# --- File helpers ---
def ensure_files():
    for path, title in [
        (NOTES_PATH, "# LiveSpeech2Text 笔记"),
        (TRANSLATIONS_PATH, "# LiveSpeech2Text 翻译"),
        (USER_NOTES_PATH, "# LiveSpeech2Text 笔记（手动）"),
    ]:
        if not os.path.exists(path):
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"{title} - {datetime.datetime.now():%Y-%m-%d %H:%M:%S}\n\n")


def load_notes():
    ensure_files()
    with open(NOTES_PATH, "r", encoding="utf-8") as f:
        return f.read()


def load_translations():
    ensure_files()
    with open(TRANSLATIONS_PATH, "r", encoding="utf-8") as f:
        return f.read()


def load_user_notes():
    ensure_files()
    with open(USER_NOTES_PATH, "r", encoding="utf-8") as f:
        return f.read()


def save_user_notes(text):
    """Overwrite notes_ai.md with new content."""
    with open(USER_NOTES_PATH, "w", encoding="utf-8") as f:
        f.write(text)
    return text


def append_note(text):
    if not text.strip():
        return load_notes()
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {text.strip()}"
    with open(NOTES_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    return load_notes()


def append_translation(text):
    if not text.strip():
        return load_translations()
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {text.strip()}"
    with open(TRANSLATIONS_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    return load_translations()


def clear_files():
    for path, title in [
        (NOTES_PATH, "# LiveSpeech2Text 笔记"),
        (TRANSLATIONS_PATH, "# LiveSpeech2Text 翻译"),
    ]:
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"{title} - {datetime.datetime.now():%Y-%m-%d %H:%M:%S}\n\n")
    return load_notes(), load_translations()


# --- Audio helpers ---
def apply_gain(audio_data: np.ndarray, gain: float, auto_norm: bool, target_rms: float = 0.1):
    orig_rms = float(np.sqrt(np.mean(audio_data.astype(np.float64) ** 2)))
    out = audio_data.astype(np.float32).copy()
    actual_gain = float(gain)
    if auto_norm and orig_rms > 1e-6:
        needed = target_rms / orig_rms
        actual_gain = float(np.clip(needed, 1.0, 100.0))
    out = out * actual_gain
    peak = float(np.max(np.abs(out)))
    if peak > 0.95:
        out = out * (0.95 / peak)
    return out, actual_gain, orig_rms


def detect_major_language(text):
    """Returns 'zh' or 'en' based on character ratio."""
    if not text:
        return "unknown"
    try:
        from langdetect import detect
        lang = detect(text)
        return "zh" if lang.startswith("zh") else "en"
    except Exception:
        # Fallback: count CJK chars
        cjk = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        return "zh" if cjk > len(text) * 0.3 else "en"


# --- Main callback ---
def transcribe_audio(audio, gain, auto_norm, asr_lang_value, trans_mode_value):
    if audio is None:
        return "Waiting...", load_notes(), load_translations()
    sr, audio_data = audio
    if audio_data is None or len(audio_data) == 0:
        return "Waiting...", load_notes(), load_translations()

    if audio_data.ndim > 1:
        audio_data = audio_data.mean(axis=1)
    audio_data = audio_data.astype(np.float32)
    if sr != SAMPLE_RATE:
        import librosa
        audio_data = librosa.resample(audio_data, orig_sr=sr, target_sr=SAMPLE_RATE)

    duration = len(audio_data) / SAMPLE_RATE
    if duration < 0.3:
        return f"({duration:.1f}s too short, skipped)", load_notes(), load_translations()

    boosted, actual_gain, orig_rms = apply_gain(audio_data, gain, auto_norm)
    new_rms = float(np.sqrt(np.mean(boosted.astype(np.float64) ** 2)))

    # ASR
    try:
        asr_lang_arg = None if asr_lang_value == "Auto" else asr_lang_value
        results = asr_model.transcribe(
            audio=(boosted, SAMPLE_RATE),
            language=asr_lang_arg,
        )
    except Exception as e:
        return f"ASR error: {e}", load_notes(), load_translations()

    if not results or not results[0].text.strip():
        return f"(no speech, RMS={orig_rms:.4f})", load_notes(), load_translations()

    text = results[0].text.strip()
    updated_notes = append_note(text)
    status = f"OK: {text}  |  RMS={orig_rms:.4f} -> x{actual_gain:.1f} -> {new_rms:.4f}"

    # Translation (async, doesn't block)
    if trans_mode_value and trans_mode_value != "off":
        direction = _resolve_direction(text, trans_mode_value)
        if direction:
            def _on_translate(result):
                if result and not result.startswith("["):
                    append_translation(result)
            translator.translate_async(text, direction, _on_translate)

    return status, updated_notes, load_translations()


def _resolve_direction(text, mode):
    """Map translation mode + text to (zh-en / en-zh / None)."""
    if mode == "all_en":
        return "zh-en"
    if mode == "all_zh":
        return "en-zh"
    if mode == "mostly_zh_en":
        if detect_major_language(text) == "zh":
            return "zh-en"
        return None
    if mode == "mostly_en_zh":
        if detect_major_language(text) == "en":
            return "en-zh"
        return None
    return None


# --- UI ---
ensure_files()


def build_ui():
    with gr.Blocks(title="LiveSpeech2Text") as app:
        with gr.Row():
            title_md = gr.Markdown("# LiveSpeech2Text")
            ui_lang_radio = gr.Radio(
                ["English", "中文"],
                value="English",
                label="UI Language",
                scale=0,
            )

        subtitle_md = gr.Markdown(LOCALES["English"]["subtitle"])

        # v4: Port info banner
        port_md = gr.Markdown(
            f"🟢 **{LOCALES['English']['port_info']}:** `{ACTIVE_PORT}` ({PORT_SOURCE_MSG})\n\n"
            f"{COMMON_PORTS_HINT}"
        )

        # v4: Port settings (change port via UI, takes effect on restart)
        with gr.Accordion("⚙️ Port settings / 端口设置", open=False):
            with gr.Row():
                port_input = gr.Number(
                    value=ACTIVE_PORT,
                    label="New port (生效需重启)",
                    minimum=1024,
                    maximum=65535,
                    step=1,
                    precision=0,
                    scale=2,
                )
                port_apply_btn = gr.Button(
                    "Apply & Save to config.json",
                    size="sm",
                    variant="primary",
                    scale=1,
                )
            port_apply_status = gr.Markdown("")

        # v4: Two tabs - Live (ASR + auto notes) / Notes (manual AI prep)
        with gr.Tabs():
            # ---- Tab 1: Live ----
            with gr.TabItem(LOCALES["English"]["tab_live"], id="live"):
                with gr.Row():
                    with gr.Column(scale=1):
                        audio_input = gr.Audio(
                            sources=["microphone"],
                            type="numpy",
                            streaming=True,
                            label=LOCALES["English"]["mic"],
                        )
                        asr_lang_radio = gr.Radio(
                            choices=LOCALES["English"]["asr_lang_choices"],
                            value="Chinese",
                            label=LOCALES["English"]["asr_lang"],
                        )
                        gain_slider = gr.Slider(1.0, 100.0, value=1.0, step=1.0,
                                                  label=LOCALES["English"]["gain_label"],
                                                  info=LOCALES["English"]["gain_info"])
                        auto_norm = gr.Checkbox(False,
                                                  label=LOCALES["English"]["agc_label"],
                                                  info=LOCALES["English"]["agc_info"])
                        trans_mode_radio = gr.Radio(
                            choices=LOCALES["English"]["trans_choices"],
                            value="off",
                            label=LOCALES["English"]["translation_mode"],
                        )
                        status = gr.Textbox(value=LOCALES["English"]["waiting"],
                                             label=LOCALES["English"]["status"],
                                             interactive=False, lines=3)
                        with gr.Row():
                            reload_btn = gr.Button(LOCALES["English"]["reload"], size="sm")
                            clear_btn = gr.Button(LOCALES["English"]["clear"], size="sm", variant="stop")

                    with gr.Column(scale=2):
                        notes_display = gr.Textbox(value=load_notes(),
                                                    label=LOCALES["English"]["notes"],
                                                    lines=25, max_lines=35, interactive=False)
                        translation_display = gr.Textbox(value=load_translations(),
                                                           label=LOCALES["English"]["translation"],
                                                           lines=12, max_lines=18, interactive=False)

            # ---- Tab 2: Notes (manual, AI prep) ----
            with gr.TabItem(LOCALES["English"]["tab_notes"], id="notes"):
                notes_ai_intro = gr.Markdown(LOCALES["English"]["notes_ai_intro"])
                user_notes_input = gr.Textbox(
                    value=load_user_notes(),
                    label=LOCALES["English"]["user_notes"],
                    placeholder=LOCALES["English"]["user_notes_placeholder"],
                    lines=25, max_lines=40,
                )
                with gr.Row():
                    save_notes_btn = gr.Button(
                        LOCALES["English"]["user_notes_save"],
                        size="sm", variant="primary"
                    )
                    user_notes_status = gr.Markdown("")

        instructions_md = gr.Markdown(LOCALES["English"]["instructions"])

        # ASR stream (Live tab)
        audio_input.stream(
            fn=transcribe_audio,
            inputs=[audio_input, gain_slider, auto_norm, asr_lang_radio, trans_mode_radio],
            outputs=[status, notes_display, translation_display],
            stream_every=2.0,
            time_limit=3600,
        )

        reload_btn.click(load_notes, outputs=notes_display)
        clear_btn.click(lambda: clear_files(), outputs=[notes_display, translation_display])

        # v4: Save user notes
        def _on_save_user_notes(text):
            save_user_notes(text)
            return LOCALES["English"]["user_notes_saved"]
        save_notes_btn.click(_on_save_user_notes, inputs=user_notes_input, outputs=user_notes_status)

        # v4: Apply new port (save to config.json, restart needed)
        def _on_port_apply(new_port):
            try:
                p = int(new_port)
            except (TypeError, ValueError):
                return f"❌ 端口必须是数字,收到: {new_port!r}"
            if not (1024 <= p <= 65535):
                return f"❌ 端口 {p} 越界,需要 1024-65535"
            if p == ACTIVE_PORT:
                return f"ℹ️ 端口已经是 {p},不用改"
            if _is_port_in_use(p):
                alt = _suggest_port(p + 1)
                hint = f" 试试 {alt}" if alt else " 这个段位也都被占了"
                return f"❌ 端口 {p} 已被占用,{hint}。换个别的"
            save_config({"port": p})
            return (
                f"✅ 已保存。下次启动会用端口 **{p}**。\n"
                f"👉 关闭本窗口,重新双击 `start_webui.bat` 生效。\n\n"
                f"提示: 启动脚本可以传端口参数盖过 config.json: `start_webui.bat {p}`"
            )
        port_apply_btn.click(_on_port_apply, inputs=port_input, outputs=port_apply_status)

        # UI language switch
        def switch_ui(lang):
            t = LOCALES[lang]
            return {
                subtitle_md: gr.update(value=t["subtitle"]),
                audio_input: gr.update(label=t["mic"]),
                asr_lang_radio: gr.update(choices=t["asr_lang_choices"], value="Chinese", label=t["asr_lang"]),
                gain_slider: gr.update(label=t["gain_label"], info=t["gain_info"]),
                auto_norm: gr.update(label=t["agc_label"], info=t["agc_info"]),
                trans_mode_radio: gr.update(
                    choices=t["trans_choices"],
                    value="off",
                    label=t["translation_mode"],
                ),
                status: gr.update(value=t["waiting"], label=t["status"]),
                notes_display: gr.update(label=t["notes"]),
                translation_display: gr.update(label=t["translation"]),
                reload_btn: gr.update(value=t["reload"]),
                clear_btn: gr.update(value=t["clear"]),
                instructions_md: gr.update(value=t["instructions"]),
                user_notes_input: gr.update(label=t["user_notes"], placeholder=t["user_notes_placeholder"]),
                save_notes_btn: gr.update(value=t["user_notes_save"]),
                notes_ai_intro: gr.update(value=t["notes_ai_intro"]),
                port_md: gr.update(
                    value=f"🟢 **{t['port_info']}:** `{ACTIVE_PORT}` ({PORT_SOURCE_MSG})\n\n{COMMON_PORTS_HINT}"
                ),
            }

        ui_lang_radio.change(switch_ui, inputs=ui_lang_radio,
                              outputs=[subtitle_md, audio_input, asr_lang_radio, gain_slider,
                                       auto_norm, trans_mode_radio, status, notes_display,
                                       translation_display, reload_btn, clear_btn, instructions_md,
                                       user_notes_input, save_notes_btn, notes_ai_intro, port_md])

    return app


if __name__ == "__main__":
    # v4: Resolve port from LST_PORT env var, validate availability
    ACTIVE_PORT, PORT_SOURCE_MSG = _parse_port()
    if _is_port_in_use(ACTIVE_PORT):
        alt = _suggest_port(ACTIVE_PORT + 1)
        print(f"⚠️  Port {ACTIVE_PORT} is in use.")
        if alt:
            print(f"   → Try: set LST_PORT={alt} and restart")
        else:
            print(f"   → No free port in range {ACTIVE_PORT+1}-{ACTIVE_PORT+5}; free up a port or pick a different one")
    print("[3/3] All models ready, launching Web UI...")
    print("=" * 60)
    print(f"Port: {ACTIVE_PORT}  ({PORT_SOURCE_MSG})")
    print(f"URL:  http://localhost:{ACTIVE_PORT}")
    print("=" * 60)
    app = build_ui()
    app.launch(
        server_name="0.0.0.0",
        server_port=ACTIVE_PORT,
        share=False,
        inbrowser=False,
        show_error=True,
    )
