@echo off
setlocal
cd /d "%~dp0"
py translation_reference\app\text_scanner_app.py
if errorlevel 1 (
  python translation_reference\app\text_scanner_app.py
)
