"""
Qwen3-ASR-1.7B 实时语音转写笔记工具 (Windows)
- 常驻进程,麦克风拾音
- 简单能量 VAD:一句完整语音停顿>0.6s 后触发转写
- 文字实时打印到终端 + 追加到 notes.md
- 支持热键:
    Ctrl+C  退出
    按 Enter 回显最近一条识别结果
- 末尾追加录音时长和识别统计
"""

import argparse
import datetime
import os
import queue
import sys
import time

import numpy as np
import sounddevice as sd
import torch

# 让 Windows 终端能正常打印中文
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# --- 配置常量(命令行可覆盖) ---
SAMPLE_RATE = 16000
CHANNELS = 1
DTYPE = "float32"
BLOCK_MS = 100
ENERGY_THRESHOLD = 0.008
SILENCE_FLUSH_S = 0.6
MIN_SPEECH_S = 0.4
MAX_BUFFER_S = 30
OVERLAP_S = 0.3


class NoteTaker:
    def __init__(self, model_name: str, language: str, output_path: str, device: str):
        self.language = language
        self.output_path = output_path
        self.device = device
        self.audio_q: queue.Queue = queue.Queue()
        self.running = True
        self.buffer: list = []
        self.speech_started = False
        self.silence_ms = 0.0
        self.last_text = ""
        self.seg_count = 0
        self.seg_audio_s = 0.0
        self.seg_asr_s = 0.0

        print(f"[init] 加载模型 {model_name} -> {device}", flush=True)
        t0 = time.time()
        from qwen_asr import Qwen3ASRModel
        dtype = torch.float16 if device.startswith("cuda") else torch.float32
        self.model = Qwen3ASRModel.from_pretrained(
            model_name,
            dtype=dtype,
            device_map=device,
            max_inference_batch_size=1,
        )
        print(f"[init] 模型加载完成({time.time()-t0:.1f}s)", flush=True)

        # 初始化 notes.md
        if not os.path.exists(output_path):
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(f"# 实时笔记 - {datetime.datetime.now():%Y-%m-%d %H:%M:%S}\n\n")

    def audio_callback(self, indata, frames, time_info, status):
        if status:
            print(f"[audio warn] {status}", file=sys.stderr, flush=True)
        self.audio_q.put(indata.copy().reshape(-1))

    def feed_loop(self):
        blocksize = int(SAMPLE_RATE * BLOCK_MS / 1000)
        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=DTYPE,
            blocksize=blocksize,
            callback=self.audio_callback,
        ):
            print(f"[mic] 开始录音 @ {SAMPLE_RATE}Hz,能量阈值 {ENERGY_THRESHOLD}", flush=True)
            print(f"[mic] 停顿 {SILENCE_FLUSH_S}s 后自动转写,结果写入: {self.output_path}", flush=True)
            print("[mic] Ctrl+C 退出\n" + "-" * 60, flush=True)
            while self.running:
                try:
                    chunk = self.audio_q.get(timeout=0.5)
                except queue.Empty:
                    continue
                self._on_chunk(chunk)

    def _on_chunk(self, chunk: np.ndarray):
        energy = float(np.abs(chunk).mean())
        if energy > ENERGY_THRESHOLD:
            self.speech_started = True
            self.silence_ms = 0.0
            self.buffer.append(chunk)
        else:
            if self.speech_started:
                self.silence_ms += BLOCK_MS
                self.buffer.append(chunk)
                if self.silence_ms >= SILENCE_FLUSH_S * 1000:
                    self._flush()

        cur_len_s = sum(len(c) for c in self.buffer) / SAMPLE_RATE
        if cur_len_s >= MAX_BUFFER_S:
            self._flush()

    def _flush(self):
        if not self.buffer:
            return
        audio = np.concatenate(self.buffer)
        duration = len(audio) / SAMPLE_RATE

        if duration < MIN_SPEECH_S:
            self._reset_buffer()
            return

        t_asr0 = time.time()
        try:
            results = self.model.transcribe(
                audio=(audio, SAMPLE_RATE),
                language=self.language,
            )
        except Exception as e:
            print(f"[asr error] {e}", file=sys.stderr, flush=True)
            self._reset_buffer()
            return
        asr_t = time.time() - t_asr0

        if results and results[0].text.strip():
            text = results[0].text.strip()
            if text == self.last_text:
                self._reset_buffer()
                return
            self.last_text = text
            self.seg_count += 1
            self.seg_audio_s += duration
            self.seg_asr_s += asr_t
            rtf = asr_t / duration if duration > 0 else 0

            ts = datetime.datetime.now().strftime("%H:%M:%S")
            line = f"[{ts}] {text}"
            print(f">>> {line}   ({duration:.1f}s 音,识别用 {asr_t:.1f}s,RTF {rtf:.2f})", flush=True)
            with open(self.output_path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        else:
            print("[asr] (空结果)", flush=True)
        self._reset_buffer()

    def _reset_buffer(self):
        if OVERLAP_S > 0 and self.buffer:
            keep_samples = int(OVERLAP_S * SAMPLE_RATE)
            all_audio = np.concatenate(self.buffer)
            tail = all_audio[-keep_samples:]
            self.buffer = [tail] if len(tail) > 0 else []
            self.speech_started = len(tail) > 0
        else:
            self.buffer = []
            self.speech_started = False
        self.silence_ms = 0.0

    def stats(self):
        if self.seg_count == 0:
            return "本次没识别到任何语音"
        avg_rtf = self.seg_asr_s / self.seg_audio_s if self.seg_audio_s else 0
        return (
            f"本次共 {self.seg_count} 段,"
            f"音频 {self.seg_audio_s:.1f}s,识别 {self.seg_asr_s:.1f}s,"
            f"平均 RTF {avg_rtf:.2f},笔记: {self.output_path}"
        )


def main():
    parser = argparse.ArgumentParser(description="Qwen3-ASR 实时语音转写笔记")
    parser.add_argument("--model", default=r"C:\Users\29335\.cache\modelscope\models\Qwen--Qwen3-ASR-1.7B\snapshots\master")
    parser.add_argument("--language", default="Chinese", help="Chinese / English / None(自动)")
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--output", default="notes.md")
    parser.add_argument("--local-model", default=None, help="本地模型目录(已下好的)")
    args = parser.parse_args()

    model_ref = args.local_model or args.model
    nk = NoteTaker(model_ref, args.language, args.output, args.device)
    try:
        nk.feed_loop()
    except KeyboardInterrupt:
        print("\n[exit] Ctrl+C,正在退出...", flush=True)
    finally:
        nk.running = False
        if nk.speech_started:
            nk._flush()
        print(f"[exit] {nk.stats()}", flush=True)
        print("[exit] bye", flush=True)


if __name__ == "__main__":
    main()
