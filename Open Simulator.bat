@echo off
setlocal
cd /d "%~dp0"

if exist "venv\Scripts\python.exe" (
    "venv\Scripts\python.exe" "main.py"
) else if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" "main.py"
) else (
    echo Python virtual environment not found.
    echo Expected: .venv\Scripts\python.exe or venv\Scripts\python.exe
    echo.
    echo Create one with:
    echo   py -m venv .venv
    echo Then install dependencies and try again.
    pause
    exit /b 1
)

if errorlevel 1 (
    echo.
    echo Simulator exited with an error.
    pause
)

endlocal
