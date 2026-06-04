"""Pass 3 (optional): Neural speech super-resolution via AudioSR.

AudioSR extends the bandwidth of band-limited speech up to 48 kHz by
synthesising missing high-frequency content.  It was trained on low-pass
filtered audio, which matches the natural roll-off of vintage recordings
after the denoise + polish passes.

Uses the "speech" model checkpoint (PyPI audiosr 0.0.7).

Install with:
    pip install audiosr
(plus deps — see README for the full manual install procedure)
"""

from pathlib import Path
from typing import Callable
import os
import tempfile


def superres(
    input_path: str,
    job_id: str,
    progress_cb: Callable[[int, str], None],
) -> str:
    """Run AudioSR speech super-resolution on *input_path*.

    Returns the path to the enhanced WAV file (48 kHz).
    """
    try:
        import torch
        from audiosr import build_model, super_resolution, save_wave
    except ImportError as exc:
        raise ImportError(
            "audiosr is not installed. "
            "Run: backend\\venv\\Scripts\\python.exe -m pip install audiosr"
        ) from exc

    import numpy as np
    import soundfile as sf

    # Suppress tokenizer parallelism warning from AudioSR internals
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

    output_dir = Path(tempfile.gettempdir()) / "clarivoice" / job_id
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = str(output_dir / "superres.wav")

    # AudioSR fp32 weights are ~7 GB — too large to fit in 8 GB VRAM alongside
    # inference activations.  Strategy: load on CPU, then apply accelerate
    # sequential CPU offloading so each sub-module is moved to CUDA just before
    # its forward pass and immediately returned to CPU RAM.  Peak VRAM stays at
    # the size of the largest single layer (a few hundred MB), while all actual
    # arithmetic runs on the GPU.  Falls back gracefully to pure CPU if CUDA is
    # unavailable.
    use_cuda = torch.cuda.is_available()

    progress_cb(97, "Pass 3: Loading AudioSR weights...")
    audiosr_model = build_model(model_name="speech", device="cpu")

    if use_cuda:
        try:
            from accelerate import cpu_offload
            for name, module in audiosr_model.named_children():
                cpu_offload(module, execution_device=torch.device("cuda"))
            progress_cb(97, "Pass 3: GPU offload ready (sequential CPU offload)...")
        except Exception:
            # accelerate unavailable or offload failed — stay on CPU
            use_cuda = False

    # AudioSR is optimised for ≤5.12 s clips and warns on longer input.
    # Split into non-overlapping 5 s chunks, super-resolve each, concatenate.
    CHUNK_DUR = 5.0  # seconds
    audio, orig_sr = sf.read(input_path)
    n_chunks = -(-len(audio) // int(CHUNK_DUR * orig_sr))  # ceiling division

    chunk_in_dir = output_dir / "sr_chunks_in"
    chunk_out_dir = output_dir / "sr_chunks_out"
    chunk_in_dir.mkdir(exist_ok=True)
    chunk_out_dir.mkdir(exist_ok=True)

    chunk_samples = int(CHUNK_DUR * orig_sr)
    results = []
    for idx, start in enumerate(range(0, len(audio), chunk_samples)):
        progress_cb(97, f"Pass 3: AudioSR chunk {idx + 1}/{n_chunks}...")
        chunk = audio[start: start + chunk_samples]
        chunk_in_path = str(chunk_in_dir / f"{idx:04d}.wav")
        sf.write(chunk_in_path, chunk, orig_sr)

        waveform = super_resolution(
            audiosr_model, chunk_in_path,
            seed=42, guidance_scale=3.5, ddim_steps=50,
        )
        save_wave(waveform, inputpath=chunk_in_path,
                  savepath=str(chunk_out_dir), name=f"{idx:04d}", samplerate=48000)
        part, _ = sf.read(str(chunk_out_dir / f"{idx:04d}.wav"))
        results.append(part)

    sf.write(out_path, np.concatenate(results, axis=0), 48000)
    return out_path
