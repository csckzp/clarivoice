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

    # Speech enhancement chain for vintage / bandwidth-limited audio:
    #   highpass       — remove low-frequency rumble below 80 Hz
    #   equalizer      — presence boost at 2.5 kHz for speech intelligibility
    #   aexciter       — harmonic exciter: synthesises upper harmonics above
    #                    4 kHz where vintage/AM-radio recordings roll off.
    #                    drive=10 / amount=0.8 gives audible but not harsh lift.
    #   equalizer      — +6 dB air shelf above 10 kHz to make the synthesised
    #                    harmonics project without harshness
    #   afftdn         — spectral noise reduction on residual artefacts
    #   acompressor    — gentle dynamic range control
    #   loudnorm       — broadcast loudness target (-16 LUFS, -1.5 dBTP)
    af = (
        "highpass=f=80,"
        "equalizer=f=2500:t=o:w=2:g=4,"
        "aexciter=level_in=1:level_out=1:amount=0.8:drive=10:freq=4000,"
        "equalizer=f=10000:t=h:width_type=o:w=0.8:g=6,"
        "afftdn=nf=-25,"
        "acompressor=threshold=-20dB:ratio=3:attack=5:release=50:makeup=2dB,"
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
