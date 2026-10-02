@echo off
title Bongo Cat Auto Clicker
start "" pythonw "%~dp0bongocat_autoclicker.py"
if %errorlevel% neq 0 (
    python "%~dp0bongocat_autoclicker.py"
)
