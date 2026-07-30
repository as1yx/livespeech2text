"""
LiveSpeech2Text Web UI (v2)
- 浏览器打开 http://localhost:7860
- 麦克风声音小时可调增益 1-8 倍,或开启自动归一化
"""

import os
import datetime

os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

import gradio as gr
import numpy as np
import torch

MODEL_DIR = r"C:\Users\29335\.cache\modelscope\models\Qwen--Qwen3-ASR-1.7B\snapshots\master"
NOTES_PATH = "notes.md"
SAMPLE_RATE = 16000

print("=" * 60)
print("LiveSpeech2Text Web UI v2")
print("=" * 60)
print(f"[1/2] Loading model: {MODEL_DIR}")
from qwen_asr import Qwen3ASRModel

model = Qwen3ASRModel.from_pretrained(
    MODEL_DIR,
    dtype=torch.float16,
    device_map="cuda:0",
    max_inference_batch_size=1,
)
print("[2/2] Model ready")


def ensure_notes_file():
    if not os.path.exists(NOTES_PATH):
        with open(NOTES_PATH, "w", encoding="utf-8") as f:
            f.write(f"# 实时笔记 - {datetime.datetime.now():%Y-%m-%d %H:%M:%S}\n\n")


def load_notes():
    ensure_notes_file()
    with open(NOTES_PATH, "r", encoding="utf-8") as f:
        return f.read()


def append_note(text: str):
    if not text.strip():
        return load_notes()
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {text.strip()}"
    with open(NOTES_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    return load_notes()


def apply_gain(audio_data: np.ndarray, gain: float, auto_norm: bool, target_rms: float = 0.1) -> np.ndarray:
    """
    给音频加增益。
    - gain: 手动增益系数 (1.0 = 不变, 2.0 = 加倍)
    - auto_norm: 启用自动归一化,把 RMS 拉到 target_rms
    返回 (放大后音频, 实际gain, 原始RMS, 新RMS)
    """
    orig_rms = float(np.sqrt(np.mean(audio_data.astype(np.float64) ** 2)))
    out = audio_data.astype(np.float32).copy()

    actual_gain = float(gain)
    if auto_norm and orig_rms > 1e-6:
        needed = target_rms / orig_rms
        # 自动归一化用 target_rms / current_rms,但限制在 1-10 倍
        auto_gain = float(np.clip(needed, 1.0, 10.0))
        actual_gain = auto_gain

    out = out * actual_gain
    # 防 clip
    peak = float(np.max(np.abs(out)))
    if peak > 0.95:
        out = out * (0.95 / peak)
    return out, actual_gain, orig_rms


def transcribe_audio(audio, gain, auto_norm):
    """处理一段音频,带增益"""
    if audio is None:
        return "等待音频...", load_notes()
    sr, audio_data = audio
    if audio_data is None or len(audio_data) == 0:
        return "等待音频...", load_notes()

    if audio_data.ndim > 1:
        audio_data = audio_data.mean(axis=1)
    audio_data = audio_data.astype(np.float32)

    if sr != SAMPLE_RATE:
        import librosa
        audio_data = librosa.resample(audio_data, orig_sr=sr, target_sr=SAMPLE_RATE)

    duration = len(audio_data) / SAMPLE_RATE
    if duration < 0.3:
        return f"({duration:.1f}s 太短,跳过)", load_notes()

    # 应用增益
    boosted, actual_gain, orig_rms = apply_gain(audio_data, gain, auto_norm)
    new_rms = float(np.sqrt(np.mean(boosted.astype(np.float64) ** 2)))

    # ASR
    try:
        results = model.transcribe(
            audio=(boosted, SAMPLE_RATE),
            language="Chinese",
        )
    except Exception as e:
        return f"❌ ASR 错误: {e}", load_notes()

    if results and results[0].text.strip():
        text = results[0].text.strip()
        updated = append_note(text)
        status = f"OK: {text}  |  orig RMS={orig_rms:.4f} -> x{actual_gain:.1f} -> {new_rms:.4f}"
        return status, updated
    return f"(no speech in {duration:.1f}s, RMS={orig_rms:.4f})", load_notes()


def clear_notes():
    if os.path.exists(NOTES_PATH):
        with open(NOTES_PATH, "w", encoding="utf-8") as f:
            f.write(f"# 实时笔记 - {datetime.datetime.now():%Y-%m-%d %H:%M:%S}\n\n")
    return load_notes()


with gr.Blocks(title="LiveSpeech2Text") as app:
    gr.Markdown(
        """
        # LiveSpeech2Text (v2)
        **说话停顿 1-2 秒**,音频自动分段识别 → 实时显示 → 自动存 `notes.md`
        """
    )

    with gr.Row():
        with gr.Column(scale=1):
            audio_input = gr.Audio(
                sources=["microphone"],
                type="numpy",
                streaming=True,
                label="麦克风",
                show_label=True,
            )

            gr.Markdown("**增益设置**")
            gain_slider = gr.Slider(
                minimum=1.0,
                maximum=8.0,
                value=1.0,
                step=0.5,
                label="手动增益 (1x - 8x)",
                info="1=不变,8=放大 8 倍。麦克风声音小时调大",
            )
            auto_norm = gr.Checkbox(
                label="自动归一化 (AGC)",
                value=False,
                info="自动把音量拉到目标水平,会覆盖手动增益",
            )

            status = gr.Textbox(
                label="状态 (含 RMS 音量信息)",
                value="等待开始...",
                interactive=False,
                lines=3,
            )

            with gr.Row():
                reload_btn = gr.Button("重新加载笔记", size="sm")
                clear_btn = gr.Button("清空笔记", size="sm", variant="stop")

        with gr.Column(scale=2):
            notes_display = gr.Textbox(
                label="笔记 (实时更新,自动保存到 notes.md)",
                value=load_notes(),
                lines=25,
                max_lines=40,
                interactive=False,
            )

    gr.Markdown(
        """
        ---
        **使用说明:**
        1. 点麦克风图标开始录音,浏览器会请求麦克风权限(第一次点"允许")
        2. 说话停顿 1-2 秒,文字出现在右边的"笔记"框
        3. 笔记自动存到 `notes.md`,用 VSCode / Notepad++ 打开是正常中文

        **声音小怎么办:**
        - 调大"手动增益"(推荐 2-5 倍开始试)
        - 或者勾选"自动归一化",系统自动拉音量
        - 状态栏会显示原始 RMS 和放大后 RMS,看是否到位
        - 正常说话 RMS 应该在 0.05-0.3 之间
        """
    )

    app.load(load_notes, outputs=notes_display)

    audio_input.stream(
        fn=transcribe_audio,
        inputs=[audio_input, gain_slider, auto_norm],
        outputs=[status, notes_display],
        stream_every=2.0,
        time_limit=3600,
    )

    reload_btn.click(load_notes, outputs=notes_display)
    clear_btn.click(clear_notes, outputs=notes_display)


if __name__ == "__main__":
    print("=" * 60)
    print("[OK] Web UI v2 launching")
    print("    URL: http://localhost:7860")
    print("=" * 60)
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        inbrowser=False,
        show_error=True,
        theme=gr.themes.Soft(),
    )
