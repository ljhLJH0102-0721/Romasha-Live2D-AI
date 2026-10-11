@echo off
powershell -NoProfile -Command "Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.Path -like '*Romasha-Live2D-AI-main*' } | Stop-Process -Force -ErrorAction SilentlyContinue; Get-Process QtWebEngineProcess -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue"
