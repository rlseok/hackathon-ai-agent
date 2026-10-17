@echo off
rem Chat screen in demo mode (guide shows every time). Same as the desktop shortcut.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0launch_demo.ps1" -App chat
