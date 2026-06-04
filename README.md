# ClarIvoice

ClarIvoice is a Tauri + React desktop app with a Python audio-processing backend.
It isolates vocals using Demucs, then enhances them with harmonic excitement, spectral noise reduction, and loudness normalisation. An optional neural bandwidth-extension pass (AudioSR) can synthesise high-frequency content lost in vintage or compressed recordings.

## Quick Start

After initial setup, run the app with one command:

```powershell
npm.cmd run tauri dev
```

This starts:
- Vite frontend
- Python backend (auto-started by Tauri)

## Windows Setup (Recommended)

From project root, run:

```bat
setup_windows.bat
```

The script will:
- Check for required tools (`node`, Python, `cargo`/`rustc`, `ffmpeg`)
- Attempt to install missing prerequisites via `winget` when available
- Install Node dependencies (`npm.cmd install`)
- Create backend virtual environment (`backend\\venv`)
- Install backend Python dependencies (`backend\\requirements.txt`)

Then start the app:

```powershell
npm.cmd run tauri dev
```

## Manual Setup

### 1) Install prerequisites
- Node.js 18+ (20+ recommended)
- Python 3.10+
- Rust toolchain (rustup + MSVC build tools)
- FFmpeg available on PATH

### 2) Install frontend dependencies

```powershell
npm.cmd install
```

### 3) Set up backend environment

```powershell
cd backend
py -m venv venv
venv\\Scripts\\python.exe -m pip install -r requirements.txt
```

### 4) Install PyTorch with CUDA (GPU acceleration)

The default pip wheel for PyTorch is CPU-only. Install the pinned CUDA 11.8 build which bundles all required Windows DLLs:

```powershell
venv\\Scripts\\python.exe -m pip install "torch==2.2.2+cu118" "torchaudio==2.2.2+cu118" --index-url https://download.pytorch.org/whl/cu118 --force-reinstall
cd ..
```

> **Why 2.2.2?** PyTorch 2.5+ CUDA wheels on Windows omit the NVRTC DLLs and require a separate CUDA Toolkit installation. 2.2.2+cu118 is the last build that bundles everything needed — no CUDA Toolkit required.

> If you don't have an NVIDIA GPU, skip this step.

### 4) Run app

```powershell
npm.cmd run tauri dev
```

## Web-Only Dev Mode (Optional)

If you want to run frontend and backend separately:

Terminal 1:

```powershell
cd backend
venv\\Scripts\\uvicorn.exe server:app --host 127.0.0.1 --port 8765
```

Terminal 2:

```powershell
npm.cmd run dev
```

Open `http://localhost:1420`.

## CLI Tool

Process audio directly from the command line — no GUI needed.

```
backend\venv\Scripts\python.exe backend\cli.py <input> [-f wav|mp3] [-o path] [--superres]
```

| Flag | Description |
|---|---|
| `-f`, `--format` | Output format: `wav` (default) or `mp3` |
| `-o`, `--output` | Output path (default: `<stem>_enhanced.<format>` in current dir) |
| `-s`, `--superres` | Enable neural bandwidth extension (Pass 3) — see below |

Examples:

```powershell
# Denoise + polish, save as WAV
backend\venv\Scripts\python.exe backend\cli.py "speech.mp3"

# Save as MP3
backend\venv\Scripts\python.exe backend\cli.py speech.mp3 -f mp3 -o speech_clean.mp3

# Full pipeline including neural bandwidth extension
backend\venv\Scripts\python.exe backend\cli.py vintage.mp3 --superres
```

Accepts any format FFmpeg can decode (MP3, WAV, FLAC, OGG, AAC, …).  
Output defaults to `<input_stem>_enhanced.<format>` in the current directory.

### Optional: Neural Speech Bandwidth Extension (`--superres`)

For vintage, AM-radio, or otherwise bandwidth-limited audio, Pass 3 uses
[AudioSR](https://github.com/haoheliu/versatile_audio_super_resolution) (MIT) to
synthesize the missing high-frequency content up to 48 kHz. AudioSR was trained
on low-pass filtered speech, which closely matches the natural roll-off of vintage
recordings after the denoise + polish passes.

**Install** (audiosr 0.0.7 has strict pins that don't resolve cleanly on Python 3.12 — install in this order):

```powershell
# 1. Install audiosr without pulling in its broken dependency pins
backend\venv\Scripts\python.exe -m pip install audiosr --no-deps

# 2. Install torchvision matched to torch 2.2.2
backend\venv\Scripts\python.exe -m pip install "torchvision==0.17.2+cu118" --index-url https://download.pytorch.org/whl/cu118

# 3. Install remaining runtime deps (tokenizers 0.19 has Python 3.12 wheels;
#    transformers 4.44 is the last version that supports torch 2.2.2)
backend\venv\Scripts\python.exe -m pip install `
    chardet ftfy unidecode progressbar pandas scipy timm torchlibrosa `
    "librosa>=0.9.2" phonemizer `
    "tokenizers>=0.19,<0.20" "transformers==4.44.2"
```

Then add `--superres` to any CLI command. Model weights (~1 GB) download automatically on first run. GPU strongly recommended.

> **Why so many steps?** `audiosr==0.0.7` pins `numpy<=1.23.5` (can't build from source on Python 3.12), `tokenizers==0.13.3` (Rust compile fails on Python 3.12), and `transformers==4.30.2` (incompatible with torch 2.2.2). Installing `--no-deps` and then providing compatible modern versions sidesteps all three problems.

## Build

```powershell
npm.cmd run tauri build
```

## Audio Processing Pipeline

| Pass | Tool | What it does |
|---|---|---|
| 1 | Demucs `htdemucs_ft` | Separates vocals from background noise/music |
| 2 | FFmpeg | High-pass filter, harmonic exciter, presence EQ, spectral denoising, loudness normalisation |
| 3 *(optional)* | AudioSR | Neural speech bandwidth extension to 48 kHz — synthesises missing high-frequency content in vintage or compressed audio |

## Notes
- First processing run can take longer while Demucs model weights (~300 MB) are downloaded.
- `--superres` triggers an ~1 GB download for AudioSR model weights on first run. GPU strongly recommended. See the audiosr install instructions above — a simple `pip install audiosr` will fail on Python 3.12.
- **GPU acceleration:** `setup_windows.bat` installs `torch==2.2.2+cu118` which bundles all CUDA DLLs and works without a CUDA Toolkit installation. PyTorch 2.5+ on Windows requires the CUDA Toolkit separately — avoid those versions. Verify GPU is being used with:
  ```powershell
  backend\venv\Scripts\python.exe -c "import torch; print('CUDA:', torch.cuda.is_available())"
  ```
- **PowerShell execution policy:** all commands above call executables directly (`npm.cmd`, `venv\Scripts\python.exe`) to avoid the `.ps1` script block. If you prefer to activate the venv the normal way, run once per terminal session: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`
