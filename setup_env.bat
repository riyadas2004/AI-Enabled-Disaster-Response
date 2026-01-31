@echo off
cd /d "%~dp0"
title Activating Virtual Environment (venv)
color 0A

echo ============================================================
echo 🚀 Activating Python Virtual Environment
echo ============================================================

if exist "venv\Scripts\activate" (
    call venv\Scripts\activate
    echo ✅ Virtual environment activated.
) else (
    echo ❌ Virtual environment not found.
    echo Creating new one...
    python -m venv venv
    call venv\Scripts\activate
    echo ✅ Virtual environment created and activated.
)

echo.
echo ============================================================
echo 🟢 You are now inside the venv.
echo ============================================================

cmd /k
