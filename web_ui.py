"""
LiveSpeech2Text Web UI v3
- i18n: English (default) / Chinese, brand name LiveSpeech2Text not translated
- Recognition language: Chinese / Chinese-English / English-Chinese / English / Auto
- Translation: off / mostly zh->en / mostly en->zh / all to en / all to zh
- Real-time translation (async, doesn't block ASR)
"""

import os
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
SAMPLE_RATE = 16000
DEVICE = "cuda:0"

# --- i18n ---
LOCALES = {
    "English": {
        "subtitle": "**Speak naturally, pause 1-2 seconds.** Audio auto-segmented and recognized. Results save to `notes.md`.",
        "ui_lang": "UI Language",
        "asr_lang": "Recognition Language",
        "asr_lang_options": ["Chinese", "Chinese-English mix", "English-Chinese mix", "English", "Auto"],
        "asr_lang_values": ["Chinese", "Chinese-English", "English-Chinese", "English", "Auto"],
        "translation_mode": "Translation",
        "trans_off": "Off",
        "trans_mostly_zh_en": "Mostly Chinese -> English",
        "trans_mostly_en_zh": "Mostly English -> Chinese",
        "trans_all_en": "All -> English",
        "trans_all_zh": "All -> Chinese",
        "gain_label": "Manual gain (1x - 8x)",
        "gain_info": "1=no change, 8=amplify 8x",
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
    },
    "中文": {
        "subtitle": "**说话停顿 1-2 秒。** 音频自动分段识别,结果保存到 `notes.md`。",
        "ui_lang": "界面语言",
        "asr_lang": "识别语言",
        "asr_lang_options": ["中文", "中英文混合", "英中文混合", "英文", "自动检测"],
        "asr_lang_values": ["Chinese", "Chinese-English", "English-Chinese", "English", "Auto"],
        "translation_mode": "翻译",
        "trans_off": "不翻译",
        "trans_mostly_zh_en": "大量中文 → 英文",
        "trans_mostly_en_zh": "大量英文 → 中文",
        "trans_all_en": "全部 → 英文",
        "trans_all_zh": "全部 → 中文",
        "gain_label": "手动增益 (1x - 8x)",
        "gain_info": "1=不变,8=放大 8 倍",
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
print("LiveSpeech2Text v3 - Web UI")
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
    for path, title in [(NOTES_PATH, "# LiveSpeech2Text 笔记"), (TRANSLATIONS_PATH, "# LiveSpeech2Text 翻译")]:
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
    for path, title in [(NOTES_PATH, "# LiveSpeech2Text 笔记"), (TRANSLATIONS_PATH, "# LiveSpeech2Text 翻译")]:
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
        actual_gain = float(np.clip(needed, 1.0, 10.0))
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

        with gr.Row():
            with gr.Column(scale=1):
                audio_input = gr.Audio(
                    sources=["microphone"],
                    type="numpy",
                    streaming=True,
                    label=LOCALES["English"]["mic"],
                )
                asr_lang_radio = gr.Radio(
                    choices=LOCALES["English"]["asr_lang_options"],
                    value="Chinese",
                    label=LOCALES["English"]["asr_lang"],
                )
                gain_slider = gr.Slider(1.0, 8.0, value=1.0, step=0.5,
                                          label=LOCALES["English"]["gain_label"],
                                          info=LOCALES["English"]["gain_info"])
                auto_norm = gr.Checkbox(False,
                                          label=LOCALES["English"]["agc_label"],
                                          info=LOCALES["English"]["agc_info"])
                trans_mode_radio = gr.Radio(
                    choices=[
                        LOCALES["English"]["trans_off"],
                        LOCALES["English"]["trans_mostly_zh_en"],
                        LOCALES["English"]["trans_mostly_en_zh"],
                        LOCALES["English"]["trans_all_en"],
                        LOCALES["English"]["trans_all_zh"],
                    ],
                    value=LOCALES["English"]["trans_off"],
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
                                            lines=30, max_lines=40, interactive=False)
                translation_display = gr.Textbox(value=load_translations(),
                                                   label=LOCALES["English"]["translation"],
                                                   lines=15, max_lines=20, interactive=False)

        instructions_md = gr.Markdown(LOCALES["English"]["instructions"])

        # ASR stream
        audio_input.stream(
            fn=transcribe_audio,
            inputs=[audio_input, gain_slider, auto_norm, asr_lang_radio, trans_mode_radio],
            outputs=[status, notes_display, translation_display],
            stream_every=2.0,
            time_limit=3600,
        )

        reload_btn.click(load_notes, outputs=notes_display)
        clear_btn.click(lambda: clear_files(), outputs=[notes_display, translation_display])

        # UI language switch
        def switch_ui(lang):
            t = LOCALES[lang]
            return {
                subtitle_md: gr.update(value=t["subtitle"]),
                audio_input: gr.update(label=t["mic"]),
                asr_lang_radio: gr.update(choices=t["asr_lang_options"], value="Chinese", label=t["asr_lang"]),
                gain_slider: gr.update(label=t["gain_label"], info=t["gain_info"]),
                auto_norm: gr.update(label=t["agc_label"], info=t["agc_info"]),
                trans_mode_radio: gr.update(
                    choices=[t["trans_off"], t["trans_mostly_zh_en"], t["trans_mostly_en_zh"], t["trans_all_en"], t["trans_all_zh"]],
                    value=t["trans_off"],
                    label=t["translation_mode"],
                ),
                status: gr.update(value=t["waiting"], label=t["status"]),
                notes_display: gr.update(label=t["notes"]),
                translation_display: gr.update(label=t["translation"]),
                reload_btn: gr.update(value=t["reload"]),
                clear_btn: gr.update(value=t["clear"]),
                instructions_md: gr.update(value=t["instructions"]),
            }

        ui_lang_radio.change(switch_ui, inputs=ui_lang_radio,
                              outputs=[subtitle_md, audio_input, asr_lang_radio, gain_slider,
                                       auto_norm, trans_mode_radio, status, notes_display,
                                       translation_display, reload_btn, clear_btn, instructions_md])

    return app


if __name__ == "__main__":
    print("[3/3] All models ready, launching Web UI...")
    print("=" * 60)
    print("URL: http://localhost:7860")
    print("=" * 60)
    app = build_ui()
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        inbrowser=False,
        show_error=True,
    )
