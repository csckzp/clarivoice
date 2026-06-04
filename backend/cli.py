#!/usr/bin/env python3
"""ClarIvoice CLI — denoise and polish audio from the command line.

Usage:
    python cli.py <input_file> [-f wav|mp3] [-o output_path] [--superres]

Examples:
    python cli.py speech.mp3
    python cli.py podcast.wav -f mp3 -o podcast_clean.mp3

    # Neural bandwidth extension (requires: pip install resemble-enhance)
    python cli.py vintage.mp3 --superres
"""

import argparse
import os
import shutil
import sys
from pathlib import Path


def _progress(pct: int, msg: str) -> None:
    bar_len = 35
    filled = int(bar_len * pct / 100)
    bar = "\u2588" * filled + "\u2591" * (bar_len - filled)
    print(f"\r[{bar}] {pct:3d}%  {msg:<55}", end="", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="clarivoice",
        description="Denoise and polish audio using Demucs + FFmpeg.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "input",
        help="Path to input audio file (MP3, WAV, FLAC, OGG, etc.)",
    )
    parser.add_argument(
        "-f", "--format",
        choices=["wav", "mp3"],
        default="wav",
        metavar="FORMAT",
        help="Output format: wav or mp3 (default: wav)",
    )
    parser.add_argument(
        "-o", "--output",
        metavar="PATH",
        help=(
            "Output file path "
            "(default: <input_stem>_enhanced.<format> in the current directory)"
        ),
    )
    parser.add_argument(
        "-s", "--superres",
        action="store_true",
        help=(
            "Run neural bandwidth extension (Pass 3) using Resemble Enhance. "
            "Reconstructs high-frequency speech content lost in vintage or "
            "compressed recordings. Requires: pip install resemble-enhance"
        ),
    )
    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    if not input_path.is_file():
        print(f"ERROR: input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    if args.output:
        out_path = Path(args.output).resolve()
    else:
        out_path = Path.cwd() / f"{input_path.stem}_enhanced.{args.format}"

    # Ensure the backend package is importable when running the script directly
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    from denoise import denoise
    from polish import polish

    print(f"Input:  {input_path}")
    print(f"Output: {out_path}")
    if args.superres:
        print("Mode:   denoise → polish → neural bandwidth extension (Pass 3)")
    print()

    job_id = "cli"

    try:
        denoised = denoise(str(input_path), job_id, _progress)
        print()  # newline after progress bar
        polished = polish(denoised, job_id, "wav", _progress)
        print()

        final = polished
        if args.superres:
            from superres import superres
            final = superres(polished, job_id, _progress)
            print()

        # Re-encode to requested format if superres changed things to WAV
        if args.superres and args.format == "mp3" and not final.endswith(".mp3"):
            import subprocess, tempfile
            mp3_path = str(Path(tempfile.gettempdir()) / "clarivoice" / job_id / "superres_final.mp3")
            r = subprocess.run(
                ["ffmpeg", "-y", "-i", final, "-c:a", "libmp3lame", "-q:a", "2", mp3_path],
                capture_output=True, text=True,
            )
            if r.returncode != 0:
                raise RuntimeError(f"FFmpeg MP3 encode failed: {r.stderr[-400:]}")
            final = mp3_path
        elif not args.superres:
            final = polished  # already in requested format from polish()

    except ImportError as exc:
        print(f"\nMissing dependency: {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(final, out_path)

    size_mb = out_path.stat().st_size / (1024 * 1024)
    print(f"Done!  {out_path}  ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
