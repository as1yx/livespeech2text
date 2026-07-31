@echo off
title LiveSpeech2Text Launcher
chcp 65001 > nul

:: v4: accept port as %1 (optional), forwarded to ps1 via env var
:: Usage:  start_webui.bat           (default port 7860)
::         start_webui.bat 7861      (use port 7861)
if not "%1"=="" set LST_PORT=%1

:: 跳过 PowerShell 执行策略,以新窗口跑 ps1
powershell.exe -NoExit -ExecutionPolicy Bypass -File "%~dp0start_webui.ps1"
