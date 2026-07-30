# LiveSpeech2Text

> 本地化实时语音转写笔记工具 — 说话即出字,自动保存

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
```cmd
:: 双击 start_webui.bat
:: 浏览器自动打开 http://localhost:7860(没自动开就手动复制地址)
:: 点 🎤 麦克风,说话
:: 文字实时进右边的笔记框
```

### 命令行版
```cmd
:: 双击 start.bat
:: 看到 [mic] 开始录音 就说话
:: Ctrl+C 退出
```

## 🔧 调音

如果麦克风声音小:
1. Web UI 里调"手动增益倍数"(1-8x,推荐 2-5)
2. 或勾选"自动归一化 (AGC)"
3. 状态栏的 RMS 值参考:正常说话应在 0.05-0.3

## 📦 安装(新机器)

```powershell
# 1. 创建 venv
python -m venv venv
venv\Scripts\activate

# 2. 装 PyTorch (CUDA 12.1)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# 3. 装其余依赖(清华源)
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple transformers accelerate soundfile librosa sounddevice qwen-asr gradio modelscope
```

模型首次跑时自动从 ModelScope 镜像下(~4.5GB)。

## 📁 文件

| 文件 | 作用 |
|------|------|
| `web_ui.py` | Gradio Web UI 主入口 |
| `note_taker.py` | 命令行常驻版 |
| `smoke_test.py` | 单次冒烟测试 |
| `start_webui.bat` | Web UI 启动器 |
| `start.bat` | 命令行启动器 |
| `notes.md` | 实时笔记输出 |

## 🛠️ 技术栈

- Qwen3-ASR-1.7B (HuggingFace/ModelScope)
- PyTorch 2.5.1 + CUDA 12.1
- Transformers 4.57.6
- Gradio 6.17
- sounddevice (PortAudio)
- librosa (音频重采样)

## 📊 性能

| 指标 | 数值 |
|------|------|
| 首次 GPU 加载 | 30-70s |
| 推理 RTF | 0.08 |
| 显存占用 | ~3.5GB (FP16) |
| 中文识别率 | 90%+ (主观) |

## ⚠️ 限制

- 首次启动需要联网下模型(以后离线)
- PowerShell 控制台中文显示乱码(文件内容正确)
- Web UI 是 2 秒分段流式,不是字级别延迟
- 不做说话人分离,多人混说会糊

## 📜 License

代码部分 MIT。Qwen3-ASR 模型遵循 Apache 2.0。
