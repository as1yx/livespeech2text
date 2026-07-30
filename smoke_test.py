"""
冒烟测试:加载 Qwen3-ASR-1.7B,录 3 秒,转写
优先用本地 ModelScope 缓存(已下好),不重新下载
"""
import os
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

import time
import numpy as np
import sounddevice as sd
import torch

# 优先用本地 ModelScope 缓存
MODEL_DIR = os.path.expanduser(
    r"~\.cache\modelscope\models\Qwen--Qwen3-ASR-1.7B\snapshots\master"
)
if not os.path.exists(os.path.join(MODEL_DIR, "config.json")):
    print("[!] 本地模型没找到,临时从 HuggingFace 下载,会比较慢...")
    MODEL_DIR = "Qwen/Qwen3-ASR-1.7B"
else:
    print(f"[ok] 用本地模型: {MODEL_DIR}")

print("[1/3] 加载模型(可能从本地 cache 读,几秒到十几秒)...")
t0 = time.time()
from qwen_asr import Qwen3ASRModel

model = Qwen3ASRModel.from_pretrained(
    MODEL_DIR,
    dtype=torch.float16,
    device_map="cuda:0",
    max_inference_batch_size=1,
)
print(f"[1/3] 模型就绪 ({time.time()-t0:.1f}s)")

print("[2/3] 录 3 秒钟音频(请说一句话)...")
sr = 16000
audio = sd.rec(int(3 * sr), samplerate=sr, channels=1, dtype="float32")
sd.wait()
audio = audio.reshape(-1)
energy = float(np.abs(audio).mean())
print(f"[2/3] 录完,能量={energy:.4f}(<0.005 可能是静音或麦克风没接好)")

print("[3/3] 转写中...")
t0 = time.time()
results = model.transcribe(
    audio=(audio, sr),
    language="Chinese",
)
print(f"[3/3] 推理耗时 {time.time()-t0:.1f}s")
for r in results:
    print(f"  语言: {r.language}")
    print(f"  文本: {r.text}")
print("done")
