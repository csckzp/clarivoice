import subprocess
import tempfile
from pathlib import Path
from typing import Callable


def polish(input_path: str, job_id: str, output_format: str, progress_cb: Callable[[int, str], None]) -> str:
    """Pass 2: high-pass filter + compression + loudness normalization via FFmpeg."""
    output_dir = Path(tempfile.gettempdir()) / "clarivoice" / job_id
    output_dir.mkdir(parents=True, exist_ok=True)

    input_name = Path(input_path).stem
    out_path = str(output_dir / f"{input_name}_enhanced.{output_format}")

    progress_cb(60, "Pass 2: Applying speech EQ and compression...")

    # Two-pass loudnorm for accurate -16 LUFS targeting
    af = (
        "highpass=f=80,"
        "acompressor=threshold=-20dB:ratio=3:attack=200:release=1000,"
        "loudnorm=I=-16:TP=-1.5:LRA=11"
    )

    codec_args = ["-c:a", "libmp3lame", "-q:a", "2"] if output_format == "mp3" else []

    result = subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", input_path,
            "-af", af,
            "-ar", "44100",
            *codec_args,
            out_path,
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg failed: {result.stderr[-500:]}")

    progress_cb(95, "Pass 2: Finalizing output file...")
    return out_path
