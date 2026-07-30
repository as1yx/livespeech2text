@echo off
chcp 65001 > nul
cd /d "%~dp0"
echo ============================================
echo  LiveSpeech2Text - 实时语音转写笔记
echo  双击本文件启动;Ctrl+C 退出
echo ============================================
echo.
call "%~dp0venv\Scripts\activate.bat"
if errorlevel 1 (
    echo [error] venv 激活失败,确认 venv 目录存在
    pause
    exit /b 1
)
python note_taker.py %*
echo.
echo [exit] 脚本已退出
pause
