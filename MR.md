# feat: LiveSpeech2Text - 本地化实时语音转写笔记工具

## 📌 TL;DR

把 Qwen3-ASR-1.7B 语音识别模型(阿里通义千问开源,1.7B 参数)部署到 Windows 本地,
**麦克风说话 → 浏览器 Web UI 实时显示文字 → 自动写入 `notes.md`**。
全程离线、零 API 费用、零数据外传。

## 🎯 Why

日常会议、采访、灵感记录场景下:
- 商业 ASR(Whisper API、Azure、阿里云语音):贵、慢、要联网
- 桌面录音笔:要后处理手敲文字
- 开源 Whisper / faster-whisper:配置复杂、中文效果参差

Qwen3-ASR-1.7B 优势:
- 阿里最新开源,中文/英文/22 种方言一模型搞定
- 1.7B 规模,精度比 0.6B 大幅提升,FP16 半精度只需要 ~4GB 显存
- 支持 52 种语言,自动检测,中英混合不打架

## 🔧 What Changed

### 新增
- `note_taker.py` - 命令行常驻版(麦克风实时拾音 + 准流式识别 + 写 `notes.md`)
- `web_ui.py` - **Gradio Web UI 版**(v2,带增益控制),浏览器打开 `http://localhost:7860` 即可
- `smoke_test.py` - 单次冒烟测试脚本(3 秒录音 + 一次识别)
- `check_audio.py` - 列可用音频设备,排查麦克风
- `start.bat` - 启动命令行版
- `start_webui.bat` - 启动 Web UI 版(双击即用,无超时)
- `明天的指令.md` - 部署进度存档(交付后归档)
- `MR.md` - 本文件

### 关键设计
- **跳过 vLLM** — Windows 装 vLLM 太折腾,改用 Transformers 后端直接推理
- **模型走 ModelScope 镜像** — huggingface.co 国内不通,Qwen 自家 ModelScope 走国内直连,稳
- **CUDA 12.1** — 适配 RTX 4060 (驱动 591.74 / CUDA 13.1) 用 PyTorch cu121,向上兼容
- **VAD 简单能量阈值** — 不用 webrtcvad 这种重依赖,0.008 阈值 + 0.6s 停顿触发
- **Web UI 流式 Audio** — gradio 6.x 的 `stream_every=2.0` API,每 2 秒切一段送 ASR
- **增益控制(增益痛点)** — v2 加了手动增益滑块(1-8x) + 自动 AGC,解决笔记本麦克风声音小的问题
- **状态栏显示 RMS** — 让用户直观看到原始音量 + 放大后音量,方便调参

## 📊 性能 / 验证

测试环境:
- GPU: NVIDIA GeForce RTX 4060 Laptop GPU (8GB VRAM)
- 驱动: 591.74 / CUDA 13.1
- 模型: Qwen3-ASR-1.7B (FP16)
- 实际显存占用: ~3.5GB

实测:
- 首次加载到 GPU: ~33 秒
- 30 秒音频 → 2.3 秒识别(**RTF ≈ 0.08**,实时因子 8%)
- 中文普通话识别率: 主观测试 90%+
- 中英混合、语气词(呃/啊)都能识别

实际跑通案例(2026-07-30 14:46-14:55):
- 9 分钟连续口述 → 244 条笔记
- 平均 2 秒一段(gradio streaming 默认)

## 🚀 How to Run

### 前置
- NVIDIA GPU 8GB+(其它配置理论可跑但需要调小 batch)
- Python 3.12
- Windows 10/11

### 一键启动
```cmd
:: 双击 start_webui.bat
:: 浏览器打开 http://localhost:7860
:: 点 🎤 麦克风,说话,文字自动进右边的笔记框
```

### 命令行版(无 UI)
```cmd
:: 双击 start.bat
:: 或:venv\Scripts\python note_taker.py
:: Ctrl+C 退出,笔记写在 notes.md
```

### 调声音小的问题
- Web UI 里的"手动增益倍数"滑块拖到 2-5x
- 或勾选"自动归一化 (AGC)",让系统自动拉音量
- 状态栏的 RMS 数值参考:正常说话应在 0.05-0.3

## 📁 文件清单

```
livespeech2text/
├── web_ui.py            # Web UI 主入口(推荐用这个)
├── note_taker.py        # 命令行版
├── smoke_test.py        # 单次冒烟测试
├── check_audio.py       # 音频设备列表
├── start_webui.bat      # Web UI 启动器(双击)
├── start.bat            # 命令行启动器
├── notes.md             # 实时笔记输出(用户生成)
├── 明天的指令.md        # 部署进度存档
└── venv/                # Python 虚拟环境(已装好所有依赖)
```

### 依赖
- torch 2.5.1+cu121
- torchaudio 2.5.1+cu121
- transformers 4.57.6
- accelerate 1.12.0
- qwen-asr 0.0.6
- sounddevice, soundfile
- gradio 6.17
- numpy, librosa, modelscope

模型文件(~4.5GB):
- `C:\Users\29335\.cache\modelscope\models\Qwen--Qwen3-ASR-1.7B\`

## ⚠️ 已知限制

1. **首次启动慢** — 模型首次搬到 GPU 要 30-70 秒,之后秒开
2. **PowerShell 控制台乱码** — 终端默认 GBK,UTF-8 中文显示乱码但**文件内容正确**
   - 解决办法:用 VSCode/Notepad++/Typora 打开 `notes.md`,或 `Get-Content -Encoding UTF8`
3. **系统后台 1 小时自动停** — 如果用我的 task 跑,1 小时到点会死
   - 解决办法:用 `start_webui.bat` 自己跑
4. **Web UI streaming 不是真·流式** — gradio 每 2 秒切一段送,不是字级别延迟
   - 想要字级延迟:得用 vLLM + 真 streaming API(Windows 难装,WSL2 可行)
5. **没做说话人分离** — 多个人说话会混在一起识别
6. **浏览器录音限制** — Chrome/Edge 麦克风权限要"允许",HTTPS 或 localhost 才能用
7. **Web UI 不支持历史音频** — 一次只处理实时流,要处理录音文件用 `note_taker.py` 改一下

## 🔮 未来可以做

- [ ] WSL2 跑 vLLM,接真 streaming API,延迟做到 200ms 内
- [ ] 加说话人分离(pyannote.audio)
- [ ] 历史音频文件拖拽识别
- [ ] 时间戳 / SRT 字幕导出
- [ ] 桌面端(用 Tauri / Electron 包装,免开浏览器)
- [ ] 快捷键全局监听(系统级,任何窗口都能录音)
- [ ] 多语言自动切换 + UI 提示

## 🧪 验证步骤

```bash
# 1. 验证 CUDA
venv\Scripts\python -c "import torch; print(torch.cuda.is_available())"
# 应输出 True

# 2. 验证模型加载
venv\Scripts\python smoke_test.py
# 录 3 秒,应能输出中文文本

# 3. 启动 Web UI
venv\Scripts\python web_ui.py
# 浏览器开 http://localhost:7860
```

## 📷 截图(可放实机截图)
- Web UI 主界面(包含麦克风 + 增益滑块 + 笔记区)
- 实时识别输出样例

## 👤 测试人
- 部署: Mavis (MiniMax Code)
- 测试: 用户
- 日期: 2026-07-29 ~ 07-30
