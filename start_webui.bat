@echo off
title LiveSpeech2Text Launcher
chcp 65001 > nul

:: 绕过 PowerShell 执行策略,以新窗口跑 ps1
powershell.exe -NoExit -ExecutionPolicy Bypass -File "%~dp0start_webui.ps1"
