@echo off
rem Scene viewer launcher (uses python.exe so its audio session matches the desktop pet)
cd /d "%~dp0"
start "" "%~dp0venv\Scripts\python.exe" "%~dp0scene_viewer.py"
