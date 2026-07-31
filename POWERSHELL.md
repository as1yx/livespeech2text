# PowerShell 兼容性说明

LiveSpeech2Text 启动脚本 `start_webui.ps1` 在 **Windows PowerShell 5.1**（Win10/11 默认版本）下运行良好，但有一些 UTF-8 相关的小问题。本文档说明需要的版本和原因。

---

## 推荐版本

**PowerShell 7.0 或更高**（也叫 `pwsh`，Core 版本）

- ✅ 完整 UTF-8 支持
- ✅ 没有 BOM 问题
- ✅ 与 Python 3.12 / 现代工具链一致
- ✅ 跨平台（万一以后想换 Mac/Linux）

---

## 检查你现在的版本

在 PowerShell 里跑：

```powershell
$PSVersionTable.PSVersion
```

输出长这样：

| 看到的 | 含义 |
|---|---|
| `Major=5, Minor=1` | **Windows PowerShell 5.1**（Win10/11 默认） |
| `Major=7` 或更高 | **PowerShell 7+**（推荐） |

或者一行：

```powershell
powershell --version   # 5.x
pwsh --version        # 7.x
```

---

## 怎么升级

### 方法 A：winget 一行装（推荐）

```powershell
winget install Microsoft.PowerShell
```

装完会有两个 PowerShell：
- `powershell.exe` — 老的 5.1（系统自带的，没动）
- `pwsh.exe` — 新的 7+（在 `C:\Program Files\PowerShell\7\pwsh.exe`）

启动新版本：

```powershell
pwsh
```

### 方法 B：手动下 MSI

去 https://github.com/PowerShell/PowerShell/releases 找最新 `PowerShell-7.x.x-win-x64.msi`，双击装。

---

## 升级后怎么跑 LiveSpeech2Text

`start_webui.bat` 默认调的是 `powershell.exe`（5.1）。要让它走新版本，改一行：

**改前**（`start_webui.bat`）：

```bat
powershell.exe -NoExit -ExecutionPolicy Bypass -File "%~dp0start_webui.ps1"
```

**改后**：

```bat
where pwsh >nul 2>nul && (
    pwsh.exe -NoExit -ExecutionPolicy Bypass -File "%~dp0start_webui.ps1"
) || (
    powershell.exe -NoExit -ExecutionPolicy Bypass -File "%~dp0start_webui.ps1"
)
```

这样优先用 `pwsh.exe`，找不到再回落到 `powershell.exe`。

或者直接绕过 .bat，在 PowerShell 7 里手动跑：

```powershell
pwsh -ExecutionPolicy Bypass -File .\start_webui.ps1
```

---

## 不升级也能跑（当前默认状态）

如果你不想升级，**LiveSpeech2Text 已经做了兼容**：

- `start_webui.ps1` 里的 `Write-Host` 全部用英文，绕开 PS 5.1 的 UTF-8 中文乱码
- 日志文件 `webui.log` 用 `Add-Content -Encoding UTF8` 写，PS 5.1 会带 BOM，但 VSCode / Notepad++ / 浏览器都能正确识别
- 模型加载、ASR 推理、笔记写入这些 Python 侧操作不受 PS 版本影响

所以 PS 5.1 + 这个项目 = 能跑，但偶尔小别扭（log 文件带 BOM、路径里有中文偶尔出问题）。

---

## PS 5.1 已知小问题

1. **BOM**：`-Encoding UTF8` 写出来的文件带 UTF-8 BOM（`EF BB BF`）。PS 7+ 的 `-Encoding utf8`（小写）不带 BOM。如果有工具不认 BOM，可以这样：

   ```powershell
   # PS 5.1: 写完后去掉 BOM
   $content = Get-Content log.txt
   $content | Set-Content log.txt -Encoding UTF8
   ```

2. **中文路径**：PS 5.1 调外部程序（`python.exe`）时，如果当前路径含中文，可能要切到 PS 7 或用 `cmd /c` 绕开。

3. **chcp 65001**：脚本开头有 `chcp 65001 > nul` 切到 UTF-8 代码页。PS 5.1 切了之后偶尔和 Windows 资源管理器路径解析有冲突，PS 7 没这问题。

---

## 经验值

我自己（开发时）用的是 PS 5.1 + Python 3.12 + venv，能跑通所有功能。遇到 UTF-8 写文件的场合，就靠 `-Encoding UTF8` 接受 BOM，或者用 `out-file` + `encoding utf8NoBOM`（PS 6+ 才有）。

升级到 PS 7+ 之后这些问题都没了，但不算必须升级。

---

## 总结一句话

> **PS 5.1 能用，PS 7+ 更省心。** 升级不升级都行，看你机器配置。
