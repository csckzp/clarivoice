"""
Compare the power spectrum of two audio files.

Usage:
    python compare_bandwidth.py <file_a> <file_b>

Prints:
  - Spectral centroid
  - Spectral rolloff at 85%, 95%, 99%
  - Energy (dB) in six frequency bands
  - Overall SNR proxy (signal vs. residual high-frequency noise floor)
"""

import sys
import numpy as np
import torchaudio

def load_mono(path: str):
    wav, sr = torchaudio.load(path)
    mono = wav.mean(dim=0).numpy()   # mix to mono
    return mono, sr

def power_spectrum(samples, sr):
    """Returns (frequencies, power_dB) using Welch-style averaged FFT."""
    n = len(samples)
    # Use overlapping windows for smoother estimate
    win = 4096
    hop = win // 2
    frames = []
    for start in range(0, n - win, hop):
        frame = samples[start:start + win] * np.hanning(win)
        frames.append(np.abs(np.fft.rfft(frame)) ** 2)
    power = np.mean(frames, axis=0)
    freqs = np.fft.rfftfreq(win, d=1.0 / sr)
    power_db = 10 * np.log10(power + 1e-12)
    return freqs, power, power_db

def spectral_centroid(freqs, power):
    return np.sum(freqs * power) / (np.sum(power) + 1e-12)

def spectral_rolloff(freqs, power, threshold=0.95):
    cumsum = np.cumsum(power)
    total = cumsum[-1]
    idx = np.searchsorted(cumsum, threshold * total)
    return freqs[min(idx, len(freqs) - 1)]

def band_energy_db(freqs, power, low, high):
    mask = (freqs >= low) & (freqs < high)
    e = np.sum(power[mask])
    return 10 * np.log10(e + 1e-12)

BANDS = [
    ("  80–300 Hz  (warmth)", 80, 300),
    (" 300–1k  Hz  (body)  ", 300, 1000),
    ("  1k–4k  Hz  (presence)", 1000, 4000),
    ("  4k–8k  Hz  (brilliance)", 4000, 8000),
    ("  8k–16k Hz  (air)   ", 8000, 16000),
    (" 16k–24k Hz  (ultra) ", 16000, 24000),
]

def analyze(label, path):
    samples, sr = load_mono(path)
    freqs, power, power_db = power_spectrum(samples, sr)
    print(f"\n{'─'*55}")
    print(f"  {label}")
    print(f"  File : {path}")
    print(f"  SR   : {sr} Hz   |   Duration: {len(samples)/sr:.1f}s")
    print(f"{'─'*55}")
    print(f"  Spectral centroid : {spectral_centroid(freqs, power):.0f} Hz")
    for pct in (0.85, 0.95, 0.99):
        print(f"  Rolloff @{int(pct*100):2d}%       : {spectral_rolloff(freqs, power, pct):.0f} Hz")
    print()
    print("  Band energy (dB)")
    for name, lo, hi in BANDS:
        db = band_energy_db(freqs, power, lo, hi)
        bar = "█" * max(0, int((db + 60) / 3))
        print(f"  {name}  {db:+6.1f} dB  {bar}")
    return freqs, power, power_db, sr

def diff_report(label_a, fa, pa, label_b, fb, pb):
    print(f"\n{'═'*55}")
    print(f"  DELTA: {label_b} − {label_a}")
    print(f"{'═'*55}")
    # Interpolate b onto a's freq axis if SRs differ
    if len(fa) != len(fb):
        pb_interp = np.interp(fa, fb, pb)
    else:
        pb_interp = pb
    for name, lo, hi in BANDS:
        da = band_energy_db(fa, pa, lo, hi)
        db_ = band_energy_db(fb, pb, lo, hi)
        diff = db_ - da
        sign = "+" if diff >= 0 else ""
        print(f"  {name}  {sign}{diff:+.1f} dB")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python compare_bandwidth.py <file_a> <file_b>")
        sys.exit(1)

    path_a, path_b = sys.argv[1], sys.argv[2]
    label_a = "A (baseline)"
    label_b = "B (enhanced)"

    fa, pa, pda, _ = analyze(label_a, path_a)
    fb, pb, pdb, _ = analyze(label_b, path_b)
    diff_report(label_a, fa, pa, label_b, fb, pb)
    print()
