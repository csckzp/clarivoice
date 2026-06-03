import tempfile
from pathlib import Path
from typing import Callable


def denoise(input_path: str, job_id: str, progress_cb: Callable[[int, str], None]) -> str:
    """Pass 1: isolate vocals using Demucs htdemucs_ft (4.0.1 low-level API)."""
    import numpy as np
    import soundfile as sf
    import torch
    import torchaudio.functional as F_audio
    from demucs.pretrained import get_model
    from demucs.apply import apply_model

    output_dir = Path(tempfile.gettempdir()) / "clarivoice" / job_id
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = str(output_dir / "denoised.wav")

    progress_cb(10, "Loading Demucs model (first run downloads ~300 MB)...")

    if torch.cuda.is_available():
        device = "cuda"
    elif torch.backends.mps.is_available():
        device = "mps"
    else:
        device = "cpu"
    model = get_model("htdemucs_ft")
    model = model.to(device)
    model.eval()

    progress_cb(20, "Pass 1: Loading audio...")

    # Use soundfile directly — avoids torchaudio backend issues in v2.11+
    data, sr = sf.read(input_path, always_2d=True)  # [samples, channels]
    wav = torch.from_numpy(data.T).float()           # [channels, samples]

    # Resample to model's expected rate (44100 Hz)
    if sr != model.samplerate:
        wav = F_audio.resample(wav, sr, model.samplerate)

    # Demucs expects exactly 2 channels
    if wav.shape[0] == 1:
        wav = wav.expand(2, -1).clone()
    elif wav.shape[0] > 2:
        wav = wav[:2]

    wav = wav.to(device)

    # Standard demucs normalisation (mirrors separate.py)
    ref = wav.mean(0)
    mean, std = ref.mean(), ref.std()
    wav = (wav - mean) / (std + 1e-8)

    progress_cb(25, "Pass 1: Separating voice from background noise...")

    # apply_model blocks the thread with no sub-step callbacks.
    # Drive a smooth fake-progress on a side thread so the UI doesn't freeze.
    import threading, time

    _stop = threading.Event()

    def _tick():
        pct = 26
        while not _stop.is_set():
            time.sleep(1.5)
            # Decelerate as we approach the ceiling so the bar never freezes
            # but also never overshoots into Pass 2's range (55+).
            gap = 53 - pct
            if gap > 0:
                pct += max(1, gap // 4)
                pct = min(pct, 53)
            progress_cb(pct, "Pass 1: Separating voice from background noise...")

    ticker = threading.Thread(target=_tick, daemon=True)
    ticker.start()

    with torch.no_grad():
        sources = apply_model(model, wav.unsqueeze(0), device=device, progress=False)

    _stop.set()
    ticker.join()

    # Denormalise
    sources = sources * (std + 1e-8) + mean

    vocal_idx = model.sources.index("vocals")
    vocals = sources[0, vocal_idx].cpu().numpy().T  # [samples, channels]

    progress_cb(55, "Pass 1: Saving isolated vocal track...")
    sf.write(out_path, vocals, model.samplerate, subtype="PCM_24")

    return out_path
