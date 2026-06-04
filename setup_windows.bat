@echo off
setlocal EnableExtensions EnableDelayedExpansion

cd /d "%~dp0"

echo ========================================
echo ClarIvoice Windows Setup
echo ========================================
echo.

set "HAS_WINGET=0"
where winget >nul 2>nul
if %errorlevel%==0 set "HAS_WINGET=1"

call :ensure_node
call :ensure_python
call :ensure_rust
call :ensure_ffmpeg

echo.
echo [1/3] Installing Node dependencies...
call npm.cmd install
if errorlevel 1 goto :fail

echo.
echo [2/3] Creating backend virtual environment if needed...
if not exist "backend\venv\Scripts\python.exe" (
  if defined PY_CMD (
    call %PY_CMD% %PY_ARGS% -m venv "backend\venv"
  ) else (
    echo ERROR: No usable Python command found.
    goto :fail
  )
  if errorlevel 1 goto :fail
) else (
  echo Backend virtual environment already exists.
)

echo.
echo [3/4] Installing backend Python dependencies...
call "backend\venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :fail
call "backend\venv\Scripts\python.exe" -m pip install -r "backend\requirements.txt"
if errorlevel 1 goto :fail

echo.
echo [4/4] Installing PyTorch with CUDA 11.8 support (GPU acceleration)...
echo This downloads ~2.7 GB on first run.
call "backend\venv\Scripts\python.exe" -m pip install "torch==2.2.2+cu118" "torchaudio==2.2.2+cu118" --index-url https://download.pytorch.org/whl/cu118 --force-reinstall
if errorlevel 1 (
  echo WARNING: CUDA PyTorch install failed. Falling back to CPU-only processing.
)

echo.
echo ========================================
echo Setup complete.
echo ========================================
echo.
echo To verify GPU support:
echo   backend\venv\Scripts\python.exe -c "import torch; print('CUDA:', torch.cuda.is_available())"
echo.
echo Run this command to start the app:
echo   npm.cmd run tauri dev
goto :end

:ensure_node
where node >nul 2>nul
if %errorlevel%==0 (
  echo Node.js detected.
  goto :eof
)
echo Node.js not found.
if "%HAS_WINGET%"=="1" (
  echo Attempting to install Node.js LTS via winget...
  winget install -e --id OpenJS.NodeJS.LTS --accept-source-agreements --accept-package-agreements
) else (
  echo Install Node.js manually: https://nodejs.org/
)
where node >nul 2>nul
if not %errorlevel%==0 (
  echo ERROR: Node.js is required.
  goto :fail
)
goto :eof

:ensure_python
set "PY_CMD="
set "PY_ARGS="
where py >nul 2>nul
if %errorlevel%==0 (
  call py -3 -c "import sys" >nul 2>nul
  if not errorlevel 1 (
    set "PY_CMD=py"
    set "PY_ARGS=-3"
    echo Python launcher py detected.
    goto :eof
  )
)
where python >nul 2>nul
if %errorlevel%==0 (
  call python -c "import sys" >nul 2>nul
  if not errorlevel 1 (
    set "PY_CMD=python"
    set "PY_ARGS="
    echo Python detected.
    goto :eof
  )
)
echo Python not found.
if "%HAS_WINGET%"=="1" (
  echo Attempting to install Python via winget...
  winget install -e --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements
) else (
  echo Install Python manually: https://www.python.org/downloads/
)

where py >nul 2>nul
if %errorlevel%==0 (
  call py -3 -c "import sys" >nul 2>nul
  if not errorlevel 1 (
    set "PY_CMD=py"
    set "PY_ARGS=-3"
    goto :eof
  )
)
where py >nul 2>nul
if %errorlevel%==0 (
  rem py exists but is not usable for running Python 3
)
where python >nul 2>nul
if %errorlevel%==0 (
  call python -c "import sys" >nul 2>nul
  if not errorlevel 1 (
    set "PY_CMD=python"
    set "PY_ARGS="
    goto :eof
  )
)
echo ERROR: Python is required and must be runnable from terminal.
echo If you just installed Python, close this terminal and open a new one.
echo You can also disable the Microsoft Store python alias in:
echo   Settings ^> Apps ^> Advanced app settings ^> App execution aliases
echo and then re-run setup.
goto :fail

:ensure_rust
where cargo >nul 2>nul
if %errorlevel%==0 (
  echo Rust toolchain detected.
  goto :eof
)
echo Rust toolchain not found.
if "%HAS_WINGET%"=="1" (
  echo Attempting to install rustup via winget...
  winget install -e --id Rustlang.Rustup --accept-source-agreements --accept-package-agreements
) else (
  echo Install Rust manually: https://rustup.rs/
)
where cargo >nul 2>nul
if not %errorlevel%==0 (
  echo WARNING: Rust not found. Tauri build/run may fail until installed.
)
goto :eof

:ensure_ffmpeg
where ffmpeg >nul 2>nul
if %errorlevel%==0 (
  echo FFmpeg detected.
  goto :eof
)
echo FFmpeg not found.
if "%HAS_WINGET%"=="1" (
  echo Attempting to install FFmpeg via winget...
  winget install -e --id Gyan.FFmpeg --accept-source-agreements --accept-package-agreements
) else (
  echo Install FFmpeg manually: https://ffmpeg.org/download.html
)
where ffmpeg >nul 2>nul
if not %errorlevel%==0 (
  echo WARNING: FFmpeg not found. Audio processing will fail until installed.
)
goto :eof

:fail
echo.
echo Setup failed. Fix the errors above, then run setup_windows.bat again.
exit /b 1

:end
exit /b 0
