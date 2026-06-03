Non-profits, community radio, and student stations sit on mountains of incredible archival history—interviews, local news, historic broadcasts—but they rarely have the budget for Adobe subscriptions or the technical expertise to fiddle with Python environments and GitHub repositories.

Building a dead-simple, unified GUI (Graphical User Interface) desktop app or web utility for this is entirely doable because **the underlying engines are already open-source.** You don't have to invent the AI; you just need to package it brilliantly.


## The Tech Stack Blueprint

To make it accessible, you want a packaged desktop application (Windows/Mac) that bundles everything together so the user never sees a terminal window.

```
[ User UI: Electron / Tauri / Python CustomTkinter ]
                       │
                       ▼
[ Pass 1 Engine: Python Backend (ONNX Runtime / OpenVINO) ]
       ├── Demucs or MDX-Net (Strips the static)
                       │
                       ▼
[ Pass 2 Engine: Pydub / FFmpeg / Matchering ]
       └── Automatic Gain, Speech EQ Curve, Dynamic Compression
                       │
                       ▼
            [ Clean WAV/MP3 Output ]

```

### 1. The Frontend (The User Interface)

* **Tauri (Rust + Web Tech) or Electron:** These let you build beautiful, modern interfaces using HTML/CSS/JavaScript (or React/Vue) and package them as standard desktop applications (`.exe` or `.app`). Tauri is highly recommended because it results in a much smaller file size than Electron.
* **Python CustomTkinter or PySide6:** If you want to keep the entire project strictly in Python, these libraries let you build surprisingly modern, clean GUIs without touching web code.

### 2. The Core Processing Backend (Pass 1 & 2)

Your interface will quietly pass the audio file to a localized Python backend that executes the steps sequentially:

* **For Pass 1 (The De-Noising):** Instead of forcing users to download the massive UVR application, you can use the raw, open-source **Demucs** or **MDX-Net** Python libraries. You can bundle a pre-trained, lightweight voice-isolation model directly inside your app folder.
* **For Pass 2 (The Polishing):** Once the backend finishes stripping the noise, the script immediately passes that temporary file to an audio processing library like **Pydub** or **FFmpeg**. You can program a hardcoded "Speech Enhancement Macro":
* A high-pass filter to cut out low-end rumble below 80Hz.
* A gentle compressor to make quiet words louder and loud words quieter (essential for old field recordings).
* An automatic leveler to bring the overall file up to broadcast loudness standards (typically -16 LUFS for stereo podcasts).



---

## Key Open-Source Projects to Steal... Uh, "Borrow" From

You don't have to write this from scratch. You can look at how these open-source projects handle the heavy lifting:

1. **`Matchering` (GitHub):** A brilliant open-source, audio-mastering engine written in Python. It takes a target track and a reference track, and automatically matches the EQ, compression, and loudness. You could feed it an old VOA clip, set a modern NPR clip as the "mastering reference," and it balances the frequencies automatically.
2. **Intel’s `openvino-plugins-ai-audacity` (GitHub):** Intel explicitly created open-source C++/Python pipelines for Audacity that handle local AI noise suppression and "Audio Super Resolution" (which physically upsamples low-quality 8kHz phone/radio recordings into crisp 44.1kHz audio). The code is entirely open to inspect.
3. **`SoundSieve` or `Auditok`:** Open-source Python libraries for audio cleanup and silence/noise detection.

---

## License

MIT